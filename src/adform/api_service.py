import time
import logging
from typing import Dict, List, Optional, Tuple, Generator
from keboola.http_client import HttpClient
from requests.exceptions import RetryError

BASE_URL = 'https://api.adform.com'
LOGIN_URL = 'https://id.adform.com/sts/connect/token'

# endpoints
END_BUYER_STATS = 'v1/buyer/stats/data'
END_BUYER_STATS_OPERATION = "v1/buyer/stats/operations/"

DEFAULT_PAGING_LIMIT = 100000
MAX_RETRIES = 10

# wait between polls (s)
DEFAULT_WAIT_INTERVAL = 2


class AdformClientError(Exception):
    pass


class AdformServerError(Exception):
    pass


class AdformClient(HttpClient):
    """
    Basic HTTP client taking care of core HTTP communication with the API service.

    It extends the kbc.client_base.HttpClientBase class, setting up the specifics for Adform service and adding
    methods for handling pagination.

    """

    def __init__(self, token):
        super().__init__(BASE_URL,
                         max_retries=MAX_RETRIES,
                         backoff_factor=0.3,
                         status_forcelist=(429, 500, 502, 504),
                         auth_header={"Authorization": f'Bearer {str(token)}'})

    def login_using_client_credentials(self,
                                       client_id: str,
                                       client_secret: str,
                                       scope: str = 'https://api.adform.com/scope/buyer.stats'):
        params = dict(grant_type='client_credentials', client_id=client_id, client_secret=client_secret, scope=scope)

        logging.info(f"🔐 LOGIN API CALL - Endpoint: {LOGIN_URL}")
        logging.info(f"🔐 LOGIN REQUEST - Method: POST, Client ID: {client_id}, Scope: {scope}")
        logging.debug(
            f"🔐 LOGIN REQUEST - Full params: grant_type=client_credentials, client_id={client_id}, scope={scope}"
        )

        secrets: Dict = self.post(endpoint_path=LOGIN_URL, is_absolute_path=True, data=params)  # noqa

        response_size = len(str(secrets)) if secrets else 0
        logging.info(f"🔐 LOGIN RESPONSE - Status: SUCCESS, Response size: {response_size} chars")
        logging.debug(f"🔐 LOGIN RESPONSE - Full response: {secrets}")

        access_token = str(secrets.get('access_token'))
        self._auth_header = {"Authorization": f'Bearer {access_token}'}
        logging.info(f"🔐 LOGIN SUCCESS - Access token obtained, length: {len(access_token)} chars")

    def _submit_stats_report(self,
                             request_filter: Dict,
                             dimensions: List,
                             metrics: List[Dict],
                             paging: Optional[Dict] = None) -> Tuple[str, str]:
        body = dict(dimensions=dimensions, filter=request_filter, metrics=metrics)
        if paging:
            body['paging'] = paging

        endpoint_url = f"{self.base_url}/{END_BUYER_STATS}"
        logging.info(f"📊 STATS SUBMISSION API CALL - Endpoint: {endpoint_url}")
        logging.info(
            f"📊 STATS SUBMISSION REQUEST - Method: POST, Dimensions: {dimensions}, Metrics count: {len(metrics)}"
        )
        logging.info(f"📊 STATS SUBMISSION REQUEST - Filter: {request_filter}")
        if paging:
            logging.info(
                f"📊 STATS SUBMISSION REQUEST - Paging: offset={paging.get('offset', 0)},"
                f" limit={paging.get('limit', 'N/A')}"
            )
        logging.debug(f"📊 STATS SUBMISSION REQUEST - Full body: {body}")

        try:
            response = self.post_raw(endpoint_path=END_BUYER_STATS, json=body)
        except RetryError as e:
            logging.error(f"📊 STATS SUBMISSION ERROR - RetryError occurred: {e}")
            raise AdformServerError(f"Client is unable to fetch data from server, "
                                    f"please check your AdForm API quota limits in case of error #429"
                                    f" the maximum allowed number of requests has been reached, error: {e}") from e

        response_size = len(response.text) if response.text else 0
        logging.info(
            f"📊 STATS SUBMISSION RESPONSE - Status: {response.status_code}, Response size: {response_size} chars"
        )
        logging.debug(f"📊 STATS SUBMISSION RESPONSE - Headers: {dict(response.headers)}")
        logging.debug(f"📊 STATS SUBMISSION RESPONSE - Full response: {response.text}")

        if response.status_code > 299:
            logging.error(f"📊 STATS SUBMISSION ERROR - HTTP {response.status_code}: {response.text}")
            raise AdformClientError(
                f"Failed to submit report. Operation failed with code {response.status_code}. Reason: {response.text}")

        operation_id = str(response.headers['Operation-Location'].rsplit('/', 1)[1])
        report_location_id = str(response.headers['Location'].rsplit('/', 1)[1])
        logging.info(
            f"📊 STATS SUBMISSION SUCCESS - Operation ID: {operation_id}, Report Location ID: {report_location_id}"
        )

        return operation_id, report_location_id

    def _wait_until_operation_finished(self, operation_id: str) -> Dict:
        continue_polling = True
        res = {}
        invalid_status = False
        start = time.time()
        poll_count = 0

        logging.info(f"⏳ OPERATION POLLING START - Operation ID: {operation_id}")

        while continue_polling:
            time.sleep(DEFAULT_WAIT_INTERVAL)
            poll_count += 1
            req_url = "".join([self.base_url, END_BUYER_STATS_OPERATION, operation_id])

            logging.info(f"⏳ OPERATION POLL #{poll_count} - Endpoint: {req_url}")
            logging.debug(f"⏳ OPERATION POLL #{poll_count} - Method: GET")

            res: Dict = self.get(req_url)  # noqa

            response_size = len(str(res)) if res else 0
            logging.info(f"⏳ OPERATION POLL #{poll_count} - Response size: {response_size} chars")
            logging.debug(f"⏳ OPERATION POLL #{poll_count} - Full response: {res}")

            if "status" not in res:
                invalid_status = True
                logging.warning(f"⏳ OPERATION POLL #{poll_count} - No status in response: {res}")
            elif res['status'] in ['succeeded', 'failed']:
                continue_polling = False
                logging.info(f"⏳ OPERATION POLL #{poll_count} - Status: {res['status']} (final)")
            else:
                logging.info(f"⏳ OPERATION POLL #{poll_count} - Status: {res.get('status', 'unknown')} (continuing)")

            if "status" not in res and time.time() - start > 60:
                continue_polling = False
                logging.warning(
                    f"⏳ OPERATION POLLING TIMEOUT - No status received after 60 seconds, poll count: {poll_count}"
                )

        if invalid_status:
            logging.error(f"⏳ OPERATION POLLING ERROR - Invalid status response: {res}")
            raise AdformClientError("Result could not be parsed. The result should return a status, but only"
                                    f"returned {res}")
        if res['status'] == 'failed':
            logging.error(f"⏳ OPERATION POLLING FAILED - Operation {operation_id} failed")
            raise AdformClientError(f'Report job ID "{operation_id} failed to process, please try again later."')

        logging.info(f"⏳ OPERATION POLLING SUCCESS - Operation {operation_id} completed after {poll_count} polls")
        return res

    def _get_report_result(self, location_id: str) -> Dict:
        endpoint = '/'.join([END_BUYER_STATS, location_id])
        endpoint_url = f"{self.base_url}/{endpoint}"

        logging.info(f"📄 REPORT RETRIEVAL API CALL - Endpoint: {endpoint_url}")
        logging.info(f"📄 REPORT RETRIEVAL REQUEST - Method: GET, Location ID: {location_id}")

        res = self.get(endpoint)  # noqa

        response_size = len(str(res)) if res else 0
        logging.info(f"📄 REPORT RETRIEVAL RESPONSE - Status: SUCCESS, Response size: {response_size} chars")

        # Log report data summary if available
        if res and 'reportData' in res:
            report_data = res['reportData']
            row_count = len(report_data.get('rows', [])) if 'rows' in report_data else 0
            column_count = len(report_data.get('columns', [])) if 'columns' in report_data else 0
            logging.info(f"📄 REPORT RETRIEVAL SUCCESS - Rows: {row_count}, Columns: {column_count}")
            logging.debug(f"📄 REPORT RETRIEVAL RESPONSE - Full response: {res}")
        else:
            logging.warning(f"📄 REPORT RETRIEVAL WARNING - No reportData in response: {res}")

        return res

    def get_report_data_paginated(self,
                                  request_filter: Dict,
                                  dimensions: List,
                                  metrics: List[Dict]) -> Generator:
        """
        Args:
            request_filter: Dict containing date range and client ids
                            e.g { "date": {"from": "2019-12-11T08:38:24.6963524Z","to": "2019-12-11T08:38:24.6963524Z"},
                                 "client": {"id": [12, 13, 14]}}
            dimensions: List containing valid dimensions
                        e.g. ["date","client","campaign"]
            metrics: List of Dicts containing valid metrics and their specs.
                     e.g.  [{"metric": "impressions","specs": {"adUniqueness": "campaignUnique"}}]

        Returns:
            res : generator - paginated results

        """
        has_more = True
        offset = 0
        page_count = 0

        logging.info(
            f"📋 PAGINATED REPORT START - Dimensions: {dimensions}, Metrics: {len(metrics)}, Filter: {request_filter}"
        )

        while has_more:
            page_count += 1
            paging = {"offset": offset, "limit": DEFAULT_PAGING_LIMIT}

            logging.info(f"📋 PAGINATED REPORT PAGE #{page_count} - Offset: {offset}, Limit: {DEFAULT_PAGING_LIMIT}")

            operation_id, report_location_id = self._submit_stats_report(request_filter, dimensions, metrics, paging)
            logging.debug(f"operation_id  : {operation_id}")
            self._wait_until_operation_finished(operation_id)
            res = self._get_report_result(report_location_id)

            if len(res.get('reportData')['rows']) > 0:
                rows_returned = len(res.get('reportData')['rows'])
                offset = rows_returned + offset
                logging.info(
                    f"📋 PAGINATED REPORT PAGE #{page_count} - Returned {rows_returned} rows, new offset: {offset}"
                )
            else:
                has_more = False
                logging.info(f"📋 PAGINATED REPORT PAGE #{page_count} - No more rows, pagination complete")

            yield res

        logging.info(f"📋 PAGINATED REPORT COMPLETE - Total pages: {page_count}, Total offset: {offset}")
