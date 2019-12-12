import json
import time

from kbc.client_base import HttpClientBase

BASE_URL = ' https://api.adform.com/'

MAX_RETRIES = 10

LOGIN_URL = 'https://id.adform.com/sts/connect/token'

# endpoints
END_BUYER_STATS = 'v1/buyer/stats/data'
END_BUYER_STATS_OPERATION = 'v1/buyer/stats/operations/'

DEFAULT_PAGING_LIMIT = 100000
# wait between polls (s)
DEFAULT_WAIT_INTERVAL = 2


class AdformClientError(Exception):
    """

    """


class AdformClient(HttpClientBase):
    """
    Basic HTTP client taking care of core HTTP communication with the API service.

    It exttends the kbc.client_base.HttpClientBase class, setting up the specifics for Adform service and adding
    methods for handling pagination.

    """

    def __init__(self, token):
        HttpClientBase.__init__(self, base_url=BASE_URL, max_retries=MAX_RETRIES, backoff_factor=0.3,
                                status_forcelist=(429, 500, 502, 504),
                                default_http_header={"Authorization": 'Bearer ' + str(token)})

    def _get_paged_result_pages(self, endpoint, parameters, res_obj_name, limit_attr, offset_req_attr, offset_resp_attr,
                                has_more_attr, offset, limit):
        """
        Generic pagination getter method returning Iterable instance that can be used in for loops.

        :param endpoint:
        :param parameters:
        :param res_obj_name:
        :param limit_attr:
        :param offset_req_attr:
        :param offset_resp_attr:
        :param has_more_attr:
        :param offset:
        :param limit:
        :return:
        """
        has_more = True
        while has_more:

            parameters['offset'] = offset
            parameters['limit'] = limit

            req = self.get_raw(self.base_url + endpoint, params=parameters)
            resp_text = str.encode(req.text, 'utf-8')
            req_response = json.loads(resp_text)

            if req_response[has_more_attr]:
                has_more = True
            else:
                has_more = False
            offset = req_response['paging']['']

            yield req_response[res_obj_name]

    def login_using_client_credentials(self, client_id, client_secret,
                                       scope='https://api.adform.com/scope/buyer.stats'):
        params = dict(grant_type='client_credentials', client_id=client_id, client_secret=client_secret, scope=scope)
        secrets = self.post(url=LOGIN_URL, data=params)
        self._auth_header = {"Authorization": 'Bearer ' + str(secrets['access_token'])}

    def submit_stats_report(self, filter, dimensions, metrics, paging=None):
        """
        :param paging dict
        {"limit":0, "offset":10}

        :param filter: dict
            {
                "date": {
                  "from": "2019-12-11T08:38:24.6963524Z",
                  "to": "2019-12-11T08:38:24.6963524Z"
                },
             "client": {
             "id": [12, 13, 14]
             }}
         [12, 13] // OR condition is applied within the same filter condition values, either data for client name_12 or name_13 will be reported.

        :param dimensions: an array
         [
            "date",
            "client",
            "campaign"
          ]
        :param metrics: array
         [
            {
              "metric": "impressions",
              "specs": {
                "adUniqueness": "campaignUnique"
              }
            }
          ]

        :return: operation_id, report_location_id
        operation_id for polling
        location_id for report retrieval
        """
        body = dict(dimensions=dimensions, filter=filter, metrics=metrics)
        if paging:
            body['paging'] = paging
        response = self.post_raw(self.base_url + END_BUYER_STATS, json=body)
        if response.status_code > 299:
            raise AdformClientError(
                f"Failed to submit report. Operation failed with code {response.status_code}. Reason: {response.text}")
        operation_id = response.headers['Operation-Location'].rsplit('/', 1)[1]
        report_location_id = response.headers['Location'].rsplit('/', 1)[1]
        return operation_id, report_location_id

    def wait_until_operation_finished(self, operation_id):
        continue_polling = True
        res = {}
        while continue_polling:
            time.sleep(DEFAULT_WAIT_INTERVAL)
            res = self.get(self.base_url + END_BUYER_STATS_OPERATION + str(operation_id))
            if res['status'] in ['succeeded', 'failed']:
                continue_polling = False

        if res['status'] == 'failed':
            raise AdformClientError(f'Report job ID "{operation_id} failed to process, please try again later."')

        return res

    def get_report_result(self, location_id):
        return self.get(self.base_url + END_BUYER_STATS + '/' + str(location_id))

    def get_report_data_paginated(self, filter, dimensions, metrics):
        has_more = True
        offset = 0
        while has_more:
            paging = {"offset": offset, "limit": DEFAULT_PAGING_LIMIT}
            operation_id, report_location_id = self.submit_stats_report(filter, dimensions, metrics, paging)
            self.wait_until_operation_finished(operation_id)
            res = self.get_report_result(report_location_id)
            if len(res['reportData']['rows']) > 0:
                offset = len(res['reportData']['rows']) + offset
            else:
                has_more = False
            yield res
