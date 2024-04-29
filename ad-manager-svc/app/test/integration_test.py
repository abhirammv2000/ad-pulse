import os
import requests
import unittest
from app.test.utils import ad_payload, ad_serve_payload
import time

os.environ['AD_MANAGER_HOST'] = 'http://localhost:5000'
os.environ['AD_SERVER_HOST'] = 'http://localhost:8080'

class TestAPI(unittest.TestCase):
    # Fixture to retrieve the API hostname from environment variables
    def setUp(self):
        self.ad_manager_host = os.environ.get('AD_MANAGER_HOST')
        self.ad_server_host = os.environ.get('AD_SERVER_HOST')

    def test_workflow(self):
        
        ad_creation_endpoint = '/ad'
        cache_refresh_endpoint = '/cache'

        # Make a POST request to create the ad
        ad_response = requests.post(self.ad_manager_host + ad_creation_endpoint, json=ad_payload)
        
        # Assert the response status code is 200 (or any other expected status code)
        self.assertEqual(ad_response.status_code, 201, f"Expected status code 200, but got {ad_response.status_code}")
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
        cache_response = requests.get(self.ad_manager_host + cache_refresh_endpoint + '/ads')
        self.assertEqual(cache_response.status_code, 200, f"Expected status code 200, but got {cache_response.status_code}")
        cache_response_data = cache_response.json()
        self.assertTrue(ad_id in cache_response_data["C20240428150217896"], f"Expected adid {ad_id} in cache, but not in cache")

        time.sleep(5)

        query_params_ad_serve = {
            'adunit_id': 'ADU20240429114506248',
            'publisher_id': 'P20240429114437478'
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
        self.assertTrue("C20240428150217896" not in cache_response_data, f"Expected adid {ad_id} to be inactive, but found in cache")

        self.assertEqual(ad_serve_response.status_code, 200, f"Expected status code 200, but got {ad_serve_response.status_code}")
        self.assertEqual(ad_serve_response.json()['bid'][0]['adid'], ad_id, f"Expected adid {ad_id} not present in response")

        clickURL = ad_serve_response.json()['bid'][0]['ext']['clickUrl']
        renderURL = ad_serve_response.json()['bid'][0]['ext']['renderUrl']

        click_response = requests.get(clickURL)
        self.assertEqual(click_response.status_code, 200, f"Expected status code 200, but got {click_response.status_code}")

        render_response = requests.get(renderURL)
        self.assertEqual(render_response.status_code, 200, f"Expected status code 200, but got {render_response.status_code}")

        report_response = requests.get(self.ad_manager_host + '/report/' + ad_id)
        self.assertEqual(report_response.status_code, 200, f"Expected status code 200, but got {report_response.status_code}")
        self.assertEqual(response_data['_id'], ad_id, f"Expected adid {ad_id} not present in response")
        self.assertEqual(response_data['clicks'], 1, f"Expected clicks 1, but got {response_data['clicks']}")
        self.assertEqual(response_data['renders'], 1, f"Expected impressions 1, but got {response_data['impressions']}") 
        

