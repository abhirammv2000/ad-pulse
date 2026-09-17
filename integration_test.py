"""End-to-end workflow test: create a publisher/advertiser/campaign/creative/ad
unit, activate an ad against them, confirm it lands in the serving cache,
serve it, click and render it, and confirm the report counts land.

Every entity is created fresh by this test rather than assuming fixture data
already exists in the target environment - the previous version hardcoded IDs
from one specific run against the original team's stage database, so it only
ever passed there and failed against any other environment (including a
freshly created one, since those IDs were never guaranteed to exist).
"""

import os
import requests
import unittest
import time
from datetime import datetime, timedelta

ad_serve_payload = {
            "dpl": "eyJ1c2VySWQiOiJVMjIwOTA4MTU0MjE2MTUwNzUwMTUzOCIsImFkVW5pdElkIjoiQURVMTIzNDUiLCJhZFVuaXROYW1lIjoiV2ViUGFnZTFUb3AiLCJsb2NhbGUiOiJlbiIsImFzcGVjdFJhdGlvIjoiMTZ4OSJ9",
            "id": "c2cd389c-b6e8-4198-8850-9cc14305d407",
            "imp": [
                {
                    "bidfloorcur": "INR",
                    "id": "877d9821-fc34-4f2c-b63a-28397bea8308-1",
                    "native": {
                        "request": {"ver": "1.2", "assets": [{"id": 1, "required": 1, "img": {"type": 3, "w": 1280, "h": 720}}]},
                        "ver": "1.2"
                    }
                }
            ],
            "user": {
                "id": "b300a5a01e981519bccfdb9093407f9fe0c22d31dc16823a450974c7e4668d49"
            }
        }

# The window every flight date (campaign and ad) is created in - wide enough
# that "now", whenever the test actually runs, always falls inside it.
FLIGHT_START = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
FLIGHT_END = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.ad_manager_host = os.environ.get('AD_MANAGER_HOST')
        self.ad_server_host = os.environ.get('AD_SERVER_HOST')

    def _create_publisher(self):
        resp = requests.post(self.ad_manager_host + '/publisher', json={
            "publishername": "Integration Test Publisher",
            "publisherdomain": "integration-test.example.com",
            "createdby": "integration-test",
            "updatedby": "integration-test",
        })
        self.assertEqual(resp.status_code, 201, f"publisher create failed: {resp.status_code} {resp.text}")
        return resp.json()['publisher']['publisherid']

    def _create_advertiser(self):
        resp = requests.post(self.ad_manager_host + '/advertiser', json={
            "advertisername": "Integration Test Advertiser",
            "industry": "Testing",
            "createdby": "integration-test",
            "updatedby": "integration-test",
        })
        self.assertEqual(resp.status_code, 201, f"advertiser create failed: {resp.status_code} {resp.text}")
        return resp.json()['advertiser']['advertiserid']

    def _create_ad_unit(self, publisher_id):
        resp = requests.post(self.ad_manager_host + '/adunit', json={
            "adunittype": "NATIVE",
            "adunitname": "Integration Test Ad Unit",
            "publisherid": publisher_id,
            "createdby": "integration-test",
            "updatedby": "integration-test",
        })
        self.assertEqual(resp.status_code, 201, f"ad unit create failed: {resp.status_code} {resp.text}")
        return resp.json()['ad_unit']['adunitid']

    def _create_active_campaign(self, advertiser_id):
        resp = requests.post(self.ad_manager_host + '/campaign', json={
            "campaignname": "Integration Test Campaign",
            "advertiserid": advertiser_id,
            "startdate": FLIGHT_START,
            "enddate": FLIGHT_END,
            "budget": {"currencyCode": "USD", "dailyBudget": 10, "totalBudget": 10},
            "createdby": "integration-test",
            "updatedby": "integration-test",
        })
        self.assertEqual(resp.status_code, 201, f"campaign create failed: {resp.status_code} {resp.text}")
        campaign_id = resp.json()['campaign']['campaignid']

        # Only ACTIVE campaigns are projected into the serving cache
        # (ad-manager-svc/app/cache/cache_job.py).
        activate = requests.patch(self.ad_manager_host + '/campaign',
                                   params={'campaign_id': campaign_id, 'state': 'ACTIVE'})
        self.assertEqual(activate.status_code, 200, f"campaign activate failed: {activate.status_code} {activate.text}")
        return campaign_id

    def _create_creative(self, advertiser_id):
        # Width/height must match the "img" asset requested in
        # ad_serve_payload below - ad-server-svc's matchImpression
        # (ad-server-svc/api/bids.go) only bids a creative whose IMAGE asset
        # dimensions match what the caller asked for.
        resp = requests.post(self.ad_manager_host + '/creative', json={
            "creativetype": "IMAGE",
            "creativename": "Integration Test Creative",
            "advertiserid": advertiser_id,
            "assets": [
                {
                    "type": "IMAGE",
                    "required": True,
                    "width": 1280,
                    "height": 720,
                    "imageURL": "https://integration-test.example.com/creative.png",
                    "imageType": "png",
                }
            ],
            "createdby": "integration-test",
            "updatedby": "integration-test",
        })
        self.assertEqual(resp.status_code, 201, f"creative create failed: {resp.status_code} {resp.text}")
        creative_id = resp.json()['creative']['creativeid']

        # Only ACTIVE creatives are projected into the serving cache
        # (ad-manager-svc/app/cache/cache_job.py) - ad-server-svc's bidder
        # loads the creative from cache and skips the ad if it's missing.
        activate = requests.patch(self.ad_manager_host + '/creative',
                                   params={'creative_id': creative_id, 'state': 'ACTIVE'})
        self.assertEqual(activate.status_code, 200, f"creative activate failed: {activate.status_code} {activate.text}")
        return creative_id

    def test_workflow(self):
        ad_creation_endpoint = '/ad'
        cache_refresh_endpoint = '/cache'

        publisher_id = self._create_publisher()
        advertiser_id = self._create_advertiser()
        ad_unit_id = self._create_ad_unit(publisher_id)
        campaign_id = self._create_active_campaign(advertiser_id)
        creative_id = self._create_creative(advertiser_id)

        ad_payload = {
            "ad_unit_targeted": [ad_unit_id],
            "adname": "Integration Test Ad",
            "adpriority": 8,
            "adstate": "ACTIVE",
            "adtype": "GUARANTEED",
            "advertiserid": advertiser_id,
            "bidinfo": {"bid": 1, "bidType": "CPM"},
            "budget": {"currencyCode": "USD", "dailyBudget": 10, "totalBudget": 10},
            "campaignid": campaign_id,
            "createdby": "integration-test",
            "creativeid": creative_id,
            "enddate": FLIGHT_END,
            "frequencycaps": {
                "frequencyCapList": [
                    {
                        "entityType": "CAMPAIGN",
                        "eventType": "CSC",
                        "timeFrame": {"maxCount": 0, "timeWindowType": "HOUR", "value": 0},
                        "userCap": True,
                    }
                ]
            },
            "landingurl": "nike.com",
            "startdate": FLIGHT_START,
            "updatedby": "integration-test",
        }

        # Make a POST request to create the ad
        ad_response = requests.post(self.ad_manager_host + ad_creation_endpoint, json=ad_payload)
        self.assertEqual(ad_response.status_code, 201, f"Expected status code 201, but got {ad_response.status_code}: {ad_response.text}")
        response_data = ad_response.json()
        ad_id = response_data['ad']['adid']

        query_params_activate_ad = {
            'ad_id': ad_id,
            'state': 'ACTIVE'
        }

        ad_update_response = requests.patch(self.ad_manager_host + ad_creation_endpoint, params=query_params_activate_ad)
        self.assertEqual(ad_update_response.status_code, 200, f"Expected status code 200, but got {ad_update_response.status_code}")

        time.sleep(5)

        requests.get(self.ad_manager_host + cache_refresh_endpoint + '/campaigns')
        requests.get(self.ad_manager_host + cache_refresh_endpoint + '/creatives')
        cache_response = requests.get(self.ad_manager_host + cache_refresh_endpoint + '/ads')
        self.assertEqual(cache_response.status_code, 200, f"Expected status code 200, but got {cache_response.status_code}")
        cache_response_data = cache_response.json()
        self.assertTrue(ad_id in cache_response_data[campaign_id], f"Expected adid {ad_id} in cache, but not in cache")

        time.sleep(5)

        query_params_ad_serve = {
            'adunit_id': ad_unit_id,
            'publisher_id': publisher_id
        }
        ad_serve_response = requests.post(self.ad_server_host + '/adserve', params=query_params_ad_serve, json=ad_serve_payload)


        query_params_deactivate_ad = {
            'ad_id': ad_id,
            'state': 'INACTIVE'
        }

        ad_update_response = requests.patch(self.ad_manager_host + ad_creation_endpoint, params=query_params_deactivate_ad)
        self.assertEqual(ad_update_response.status_code, 200, f"Expected status code 200, but got {ad_update_response.status_code}")

        time.sleep(5)
        cache_response = requests.get(self.ad_manager_host + cache_refresh_endpoint + '/ads')
        self.assertEqual(cache_response.status_code, 200, f"Expected status code 200, but got {cache_response.status_code}")
        cache_response_data = cache_response.json()
        self.assertTrue(campaign_id not in cache_response_data, f"Expected adid {ad_id} to be inactive, but found in cache")

        self.assertEqual(ad_serve_response.status_code, 200, f"Expected status code 200, but got {ad_serve_response.status_code}: {ad_serve_response.text}")
        self.assertEqual(ad_serve_response.json()['bid'][0]['adid'], ad_id, f"Expected adid {ad_id} not present in response")

        clickURL = ad_serve_response.json()['bid'][0]['ext']['clickUrl']
        renderURL = ad_serve_response.json()['bid'][0]['ext']['renderUrl']

        click_response = requests.get(clickURL)
        self.assertEqual(click_response.status_code, 200, f"Expected status code 200, but got {click_response.status_code}")

        render_response = requests.get(renderURL)
        self.assertEqual(render_response.status_code, 200, f"Expected status code 200, but got {render_response.status_code}")

        time.sleep(5)
        report_response = requests.get(self.ad_manager_host + '/reports/' + ad_id)
        self.assertEqual(report_response.status_code, 200, f"Expected status code 200, but got {report_response.status_code}")

        report_response = report_response.json()
        print(report_response)
        self.assertEqual(report_response[0]['_id'], ad_id, f"Expected adid {ad_id} not present in response")
        self.assertEqual(report_response[0]['click'], 1, f"Expected clicks 1, but got {report_response[0]['click']}")
        self.assertEqual(report_response[0]['render'], 1, f"Expected impressions 1, but got {report_response[0]['render']}")
