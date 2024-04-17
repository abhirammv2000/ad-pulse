#unit test for ad-service
import unittest
from unittest.mock import MagicMock

from app.services.ad_service import get_all_ads, create_ad, get_ad_by_id, get_ad_by_state, update_ad_state, update_ad


class TestAdService(unittest.TestCase):
    def setUp(self):
        # Mocking the create_session function
        self.mock_create_session = MagicMock()
        self.session_mock = MagicMock()
        self.mock_create_session.return_value = self.session_mock

    def get_ad_id_by_name(self, json_data, ad_name):
        for ad in json_data:
            if ad.get('adname') == ad_name:
                return ad.get('adid')

    def test_create_ad(self):
        # Test case for create_ad function
        json_data = {
        "adid": "A20240410162238070",
        "adname": "test1Aditi",
        "adpriority": 4,
        "adstate": "CREATED",
        "adtype": "GUARANTEED",
        "advertiserid": "A12345",
        "bidinfo": None,
        "budget": None,
        "campaignid": "C54321",
        "createdat": "Wed, 10 Apr 2024 16:22:38 GMT",
        "createdby": "kushal.1nagaraj.1@gmail.com",
        "creativeid": "CR12345",
        "enddate": "2024-03-17T21:05:56",
        "frequencycaps": None,
        "landingurl": "https://www.hotstar.com",
        "startdate": "2024-03-17T21:05:56",
        "targetinginfo": None,
        "updatedat": "",
        "updatedby": "aditihk@gmail.com"
        }

        # testing the create_ad function
        created_ad = create_ad(json_data)
        self.assertIsNotNone(created_ad)
        self.assertEqual(created_ad['adname'], json_data['adname'])

        #testing the get all ads function
        all_ads = get_all_ads()
        self.assertIsNotNone(all_ads)
        self.assertIn("test1Aditi", [ad['adname'] for ad in all_ads])

        #testing the get ad by id function
        ad_id = self.get_ad_id_by_name(all_ads, "test1Aditi")
        ad = get_ad_by_id(ad_id)
        self.assertIsNotNone(ad)
        self.assertEqual(ad['adid'], ad_id)

        #testing the update ad state function
        state = "ACTIVE"
        update_ad_state(ad_id, state)
        updated_ad = get_ad_by_id(ad_id)
        self.assertIsNotNone(updated_ad)
        self.assertEqual(updated_ad['adstate'], state)

        #testing the update ad function
        updated_json_data = {
            "adid": ad_id,
            "adname": "test1Aditi",
            "adpriority": 7,
            "adstate": "CREATED",
            "adtype": "GUARANTEED",
            "advertiserid": "A12345",
            "bidinfo": None,
            "budget": None,
            "campaignid": "C54321",
            "createdat": "Wed, 10 Apr 2024 16:22:38 GMT",
            "createdby": "kushal.1nagaraj.1@gmail.com",
            "creativeid": "CR12345",
            "enddate": "2024-03-17T21:05:56",
            "frequencycaps": None,
            "landingurl": "https://www.hotstar.com",
            "startdate": "2024-03-17T21:05:56",
            "targetinginfo": None,
            "updatedat": "",
            "updatedby": "aditihk@gmail.com"
        }
        update_ad(updated_json_data)
        updated_ad = get_ad_by_id(ad_id)
        self.assertIsNotNone(updated_ad)
        self.assertEqual(updated_ad['adpriority'], updated_json_data['adpriority'])

    #testing the get ad by state function
        state = "ACTIVE"
        ad_state = get_ad_by_state(state)
        self.assertIsNotNone(ad_state)
        self.assertEqual(ad_state['adstate'], state)

if __name__ == '__main__':
    unittest.main()
