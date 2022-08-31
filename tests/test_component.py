'''
Created on 12. 11. 2018

@author: esner
'''
import unittest
import mock
import os
import datetime
from freezegun import freeze_time

from component import Component, build_metrics, build_specs, build_filter_def, get_date_period_converted


class TestComponent(unittest.TestCase):

    # set global time to 2010-10-10 - affects functions like datetime.now()
    @freeze_time("2010-10-10")
    # set KBC_DATADIR env to non-existing dir
    @mock.patch.dict(os.environ, {'KBC_DATADIR': './non-existing-dir'})
    def test_run_no_cfg_fails(self):
        with self.assertRaises(ValueError):
            comp = Component()
            comp.run()

    def test_metric_building(self):
        metrics = [{
            "metric": "conversionsAll",
            "specs_metadata": [
                {
                    "key": "adInteraction",
                    "value": "postImpression"
                },
                {
                    "key": "conversionType",
                    "value": "conversionType1"
                }
            ]
        }]
        expected_metrics = [{"metric": "conversionsAll",
                             "specs": {"adInteraction": "postImpression", "conversionType": "conversionType1"}}]
        built_metrics = build_metrics(metrics)
        self.assertEquals(expected_metrics, built_metrics)

    def test_metric_spec_building(self):
        metric_specs = [
            {
                "key": "adInteraction",
                "value": "postImpression"
            },
            {
                "key": "conversionType",
                "value": "conversionType1"
            }
        ]
        expected_specs = {"adInteraction": "postImpression", "conversionType": "conversionType1"}
        built_specs = build_specs(metric_specs)
        self.assertEquals(expected_specs, built_specs)

    def test_filter_building_without_client_ids(self):
        start_date = datetime.date(2022, 8, 20)
        end_date = datetime.date(2022, 8, 21)
        expected_filter = {'date': {'from': '2022-08-20', 'to': '2022-08-21'}}
        built_filter = build_filter_def(start_date, end_date, None)
        self.assertEquals(expected_filter, built_filter)

    def test_filter_building(self):
        start_date = datetime.datetime(2022, 8, 20)
        end_date = datetime.datetime(2022, 8, 21)
        client_ids = [11, 12]
        expected_filter = {'date': {'from': '2022-08-20', 'to': '2022-08-21'}, "client": {"id": client_ids}}
        built_filter = build_filter_def(start_date, end_date, client_ids)
        self.assertEquals(expected_filter, built_filter)

    def test_get_date_period_converted(self):
        expected_start, expected_end = datetime.datetime(2022, 8, 20), datetime.datetime(2022, 8, 21)
        built_start, built_end = get_date_period_converted("2022-08-20", "2022-08-21")
        self.assertEquals(expected_start, built_start)
        self.assertEquals(expected_end, built_end)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
