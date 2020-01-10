'''
Template Component main class.

'''

import csv
import json
import logging
import os
import sys

from kbc.env_handler import KBCEnvHandler
from kbc.result import KBCTableDef, KBCResult

from adform.api_service import AdformClient

# configuration variables
KEY_API_TOKEN = '#api_secret'
KEY_API_CLIENT_ID = 'api_client_id'

KEY_RESULT_FILE = 'result_file_name'
KEY_FILTER = 'filter'
KEY_DATE_RANGE = 'date_range'
KEY_DATE_FROM = 'from_date'
KEY_DATE_TO = 'to_date'
KEY_CLIENT_IDS = 'client_ids'

KEY_DIMENSIONS = 'dimensions'

KEY_METRICS = 'metrics'
KEY_METRIC = 'metric'
KEY_SPEC_DATA = 'specs_metadata'
KEY_KEY = 'key'
KEY_VALUE = 'value'

# #### Keep for debug
KEY_DEBUG = 'debug'
MANDATORY_PARS = [KEY_FILTER, KEY_DIMENSIONS, KEY_METRICS, KEY_RESULT_FILE]
MANDATORY_IMAGE_PARS = []

APP_VERSION = '0.0.1'


class Component(KBCEnvHandler):

    def __init__(self, debug=False):
        KBCEnvHandler.__init__(self, MANDATORY_PARS, )
        # override debug from config
        if self.cfg_params.get(KEY_DEBUG):
            debug = True

        log_level = logging.DEBUG if debug else logging.INFO
        # setup GELF if available
        if os.getenv('KBC_LOGGER_ADDR', None):
            self.set_gelf_logger(log_level)
        else:
            self.set_default_logger(log_level)
        logging.info('Running version %s', APP_VERSION)
        logging.info('Loading configuration...')

        try:
            self.validate_config()
            self.validate_parameters(self.cfg_params[KEY_FILTER],
                                     [KEY_DATE_RANGE], KEY_FILTER)
            self.validate_parameters(self.cfg_params[KEY_FILTER].get(KEY_DATE_RANGE, []),
                                     [KEY_DATE_FROM, KEY_DATE_TO],
                                     KEY_DATE_RANGE)
            for m in self.cfg_params[KEY_METRICS]:
                self.validate_parameters(m, [KEY_METRIC], KEY_METRICS)
        except ValueError as e:
            logging.exception(e)
            exit(1)

        # intialize instance parameteres
        try:
            if self.cfg_params[KEY_API_TOKEN]:
                # legacy client credential flow support
                self.client = AdformClient('')
                self.client.login_using_client_credentials(self.cfg_params[KEY_API_CLIENT_ID],
                                                           self.cfg_params[KEY_API_TOKEN])
            else:
                # oauth
                auth = json.loads(self.get_authorization()['#data'])
                self.client = AdformClient(auth.get('access_token'))
        except Exception as ex:
            raise RuntimeError(f'Login failed, please check your credentials! {str(ex)}')

    def run(self):
        '''
        Main execution code
        '''
        params = self.cfg_params  # noqa

        logging.info('Building report request..')
        dimensions = params.get(KEY_DIMENSIONS)

        metric_defs = self.build_metrics(params.get(KEY_METRICS))
        filters = params[KEY_FILTER]
        date_range = filters[KEY_DATE_RANGE]
        start_date, end_date = self.get_date_period_converted(date_range[KEY_DATE_FROM], date_range[KEY_DATE_TO])

        filter_def = self.build_fiter_def(start_date, end_date, filters.get(KEY_CLIENT_IDS))
        logging.info(f'Submitting report with parameters: filter: {params[KEY_FILTER]}, '
                     f'dimensions={dimensions}, metrics:{params.get(KEY_METRICS)}')
        logging.info('Collecting report result..')

        result_file_name = params[KEY_RESULT_FILE]
        for r in self.client.get_report_data_paginated(filter_def, dimensions, metric_defs):
            logging.info('Storing results')
            self.store_results(r, report_name=result_file_name, incremental=params.get('incremental_output', True),
                               pkey=dimensions)

        logging.info('Extraction finished successfully!')

    def build_metrics(self, metrics_cfg):
        metric_defs = []
        for m in metrics_cfg:
            metric_def = {"metric": m[KEY_METRIC],
                          "specs": self.build_specs(m[KEY_SPEC_DATA])}
            metric_defs.append(metric_def)
        return metric_defs

    def build_specs(self, spec_metadata):
        spec_def = dict()
        for s in spec_metadata:
            spec_def[s[KEY_KEY]] = s[KEY_VALUE]
            return spec_def

    def build_fiter_def(self, start_date, end_date, client_ids):
        """ {
                "date": {
                  "from": "2019-12-11T08:38:24.6963524Z",
                  "to": "2019-12-11T08:38:24.6963524Z"
                },
             "client": {
             "id": [12, 13, 14]
             }}"""
        filter_def = dict()
        filter_def['date'] = {"from": start_date.strftime('%Y-%m-%d'),
                              "to": end_date.strftime('%Y-%m-%d')}
        if client_ids:
            filter_def['client'] = {"id": client_ids}
        return filter_def

    def store_results(self, report_result, incremental=True, report_name='result_data', pkey=[]):

        file_name = report_name + '.csv'
        res_file_path = os.path.join(self.tables_out_path, file_name)
        if os.path.exists(res_file_path):
            mode = 'a'
        else:
            mode = 'w+'
        columns = report_result['reportData']['columnHeaders']
        with open(res_file_path, mode, newline='', encoding='utf-8') as out:
            writer = csv.writer(out)
            # write header
            if mode == 'w+':
                writer.writerow(columns)
            # write data
            writer.writerows(report_result['reportData']['rows'])

        table_def = KBCTableDef(file_name, [], pkey)
        result = KBCResult(file_name, res_file_path, table_def)
        self.create_manifests([result], incremental=incremental)


"""
    Main entrypoint
"""

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug = sys.argv[1]
    else:
        debug = False
    try:
        comp = Component(debug)
        comp.run()
    except Exception as e:
        logging.exception(e)
        exit(1)
