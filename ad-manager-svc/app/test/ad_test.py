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

    def test_create_ad(self):
        # Test case for create_ad function
        json_data = {
        "adid": "A20240410162238070",
        "adname": "test1Aditi",
        "adpriority": 4,
        "adstate": "INACTIVE",
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

        # Mocking the create_ad function
        created_ad = create_ad(json_data)
        self.assertIsNotNone(created_ad)

    def test_get_all_ads(self):
        # Test case for get_all_ads function
        json_data = [{
            "adid": "A20240410162238070",
            "adname": "test1Aditi",
            "adpriority": 4,
            "adstate": "INACTIVE",
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
        }]
        # Call the function
        self.session_mock.query.return_value.all.return_value = json_data
        ads_data = get_all_ads()
        # Assert that the returned data is not empty
        self.assertNotEqual(len(ads_data), 0)
        self.assertIn("test1Aditi", [ad['adname'] for ad in ads_data])

    def test_get_ad_by_id(self):
        # Test case for get_ad_by_id function
        ad_id = "A20240410162238070"
        json_data = {
            "adid": "A20240410162238070",
            "adname": "test1Aditi",
            "adpriority": 4,
            "adstate": "INACTIVE",
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
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = json_data

        # Call the function
        ad_data = get_ad_by_id(ad_id)

        # Assertions
        self.assertIsNotNone(ad_data)
        self.assertEqual(ad_data['adid'], ad_id)

    def test_ad_not_found(self):
        # Test case for get_ad_by_id function when ad is not found
        ad_id = "A20240410162238"
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None

        # Call the function
        ad_data = get_ad_by_id(ad_id)
        # print("ad_data", ad_data)

        # Assertions
        self.assertIsNone(ad_data)

    def test_get_ad_by_state(self):
        # Test case for get_ad_by_state function
        state = "INACTIVE"
        json_data = {
            "adid": "A20240410162238070",
            "adname": "test1Aditi",
            "adpriority": 4,
            "adstate": "INACTIVE",
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
        self.session_mock.query.return_value.filter_by.return_value.all.return_value = json_data
        ad_state = get_ad_by_state("INACTIVE")
        self.assertIsNotNone(ad_state)
        # print(self.session_mock.query.return_value.filter_by.return_value.all.return_value)
        self.assertEqual(json_data['adstate'], state)

    def test_get_ad_by_state_no_ads_found(self):
        # Mock data
        state = 'NON_EXISTING_STATE'
        # Simulate the case where no ads with the specified state are found
        self.session_mock.query.return_value.filter_by.return_value.all.return_value = None

        # Call the function
        ads_data = get_ad_by_state(state)

        # Assertions
        self.assertEqual(len(ads_data), 0)

    def test_update_ad_state(self):
        # Test case for update_ad_state function
        ad_id = "A20240410162238070"
        new_state = "ACTIVE"
        json_data = {
            "adid": "A20240410162238070",
            "adname": "test1Aditi",
            "adpriority": 4,
            "adstate": "ACTIVE",
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
            "updatedby": "aditihk@gmail.com"}
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = json_data
        # Call the function
        updated = update_ad_state(ad_id, new_state)
        self.assertTrue(updated)

    def test_update_ad_state_invalid_state(self):
        # Test case for update_ad_state function with invalid state
        ad_id = "A20240410162238"
        new_state = "INVALID_STATE"
        # Call the function
        updated = update_ad_state(ad_id, new_state)

        self.assertFalse(updated)

    # def test_create_ad_api(self):
    #     # Test case for create_ad_api function
    #     json_data = {
    #         "adid": "A202404101",
    #         "adname": "test1Aditi",
    #         "adpriority": 4,
    #         "adstate": "INACTIVE",
    #         "adtype": "GUARANTEED",
    #         "advertiserid": "A12345",
    #         "bidinfo": None,
    #         "budget": None,
    #         "campaignid": "C54321",
    #         "createdat": "Wed, 10 Apr 2024 16:22:38 GMT",
    #         "createdby": "kushal.1nagaraj.1@gmail.com",
    #         "creativeid": "CR12345",
    #         "enddate": "2024-03-17T21:05:56",
    #         "frequencycaps": None,
    #         "landingurl": "https://www.hotstar.com",
    #         "startdate": "2024-03-17T21:05:56",
    #         "targetinginfo": None,
    #         "updatedat": "",
    #         "updatedby": "aditihk@gmail.com"}
    #     # Mocking the request.json
    #     request = MagicMock()
    #     request.json = json_data
    #     # Call the function
    #     created_ad = create_ad(json_data)
    #     # Assertions
    #     self.assertIsNotNone(created_ad)

    def test_update_ad_api(self):
        # Test case for update_ad_api function
        json_data = {
            "adid": "A202404101",
            "adname": "test1Aditi",
            "adpriority": 4,
            "adstate": "INACTIVE",
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
            "updatedby": "aditihk@gmail.com"}
        # Mocking the request.json
        request = MagicMock()
        request.json = json_data
        # Call the function
        updated_ad = update_ad(json_data)
        # Assertions
        self.assertIsNotNone(updated_ad)



if __name__ == '__main__':
    unittest.main()
