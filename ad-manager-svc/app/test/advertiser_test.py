import unittest
from unittest.mock import MagicMock

from app.services.advertiser_service import get_all_advertisers, create_advertiser, get_advertiser_by_id, \
    get_advertiser_by_state, update_advertiser_state, update_advertiser


class TestAdvertiserService(unittest.TestCase):
    def setUp(self):
        # Mocking the create_session function
        self.mock_create_session = MagicMock()
        self.session_mock = MagicMock()
        self.mock_create_session.return_value = self.session_mock

    def get_adv_id_by_name(self, json_data, ad_name):
        for adv in json_data:
            if adv.get('advertisername') == ad_name:
                return adv.get('advertiserid')

    def test_create_advertiser(self):
        # Test case for create_advertiser function
        json_data = {
            "advertiserid": "",
            "advertisername": "test1Aditi",
            "industry": "IT",
            "brands": ["test"],
            "contactinfo": {
                "email": "asdf@gmail.com"
            },
            "advertisertype": "GUARANTEED",
            "createdby": "aditi@gmail.com ",
            "updatedby": "admin",
            "createdat": "2024-03-17T21:05:56",
            "updatedat": "2024-03-17T21:05:56",
            "advertiserstate": "CREATED"
        }

        created_advertiser = create_advertiser(json_data)
        self.assertIsNotNone(created_advertiser)
        self.assertEqual(created_advertiser['advertisername'], json_data['advertisername'])

    def test_get_all_advertisers(self):
        all_advertisers = get_all_advertisers()
        self.assertIsNotNone(all_advertisers)
        self.assertIn("test1Aditi", [advertiser['advertisername'] for advertiser in all_advertisers])

    def test_get_advertiser_by_id(self):
        json_data = {
            "advertiserid": "",
            "advertisername": "test1Aditi",
            "industry": "IT",
            "brands": ["test"],
            "contactinfo": {
                "email": "asdf@gmail.com"
            },
            "advertisertype": "GUARANTEED",
            "createdby": "aditi@gmail.com ",
            "updatedby": "admin",
            "createdat": "2024-03-17T21:05:56",
            "updatedat": "2024-03-17T21:05:56",
            "advertiserstate": "CREATED"
        }
        created_advertiser = create_advertiser(json_data)
        adv_id = created_advertiser['advertiserid']
        advertiser = get_advertiser_by_id(adv_id)
        self.assertIsNotNone(advertiser)
        self.assertEqual(advertiser['advertiserid'], adv_id)

    def test_update_advertiser_state(self):
        json_data = {
            "advertiserid": "",
            "advertisername": "test1Aditi",
            "industry": "IT",
            "brands": ["test"],
            "contactinfo": {
                "email": "asdf@gmail.com"
            },
            "advertisertype": "GUARANTEED",
            "createdby": "aditi@gmail.com ",
            "updatedby": "admin",
            "createdat": "2024-03-17T21:05:56",
            "updatedat": "2024-03-17T21:05:56",
            "advertiserstate": "CREATED"
        }

        created_advertiser = create_advertiser(json_data)
        adv_id = created_advertiser['advertiserid']
        state = "INACTIVE"
        update_advertiser_state(adv_id, state)
        updated_advertiser = get_advertiser_by_id(adv_id)
        self.assertIsNotNone(updated_advertiser)
        self.assertEqual(updated_advertiser['advertiserstate'], state)

    def test_update_advertiser(self):
        json_data = {
            "advertiserid": "",
            "advertisername": "test1Aditi",
            "industry": "IT",
            "brands": ["test"],
            "contactinfo": {
                "email": "asdf@gmail.com"
            },
            "advertisertype": "GUARANTEED",
            "createdby": "aditi@gmail.com ",
            "updatedby": "admin",
            "createdat": "2024-03-17T21:05:56",
            "updatedat": "2024-03-17T21:05:56",
            "advertiserstate": "CREATED"
        }

        created_advertiser = create_advertiser(json_data)
        adv_id = created_advertiser['advertiserid']

        updated_json_data = {
            "advertiserid": adv_id,
            "advertisername": "test1Aditi",
            "industry": "IT",
            "brands": ["test45"],
            "contactinfo": {
                "email": "asdf1234@gmail.com"
            },
            "advertisertype": "GUARANTEED",
            "createdby": "aditi@gmail.com ",
            "updatedby": "admin",
            "createdat": "2024-03-17T21:05:56",
            "updatedat": "2024-03-17T21:05:56",
            "advertiserstate": "CREATED"
        }

        update_advertiser(updated_json_data)
        updated_advertiser = get_advertiser_by_id(adv_id)
        self.assertIsNotNone(updated_advertiser)
        self.assertEqual(updated_advertiser['brands'], updated_json_data['brands'])
        self.assertEqual(updated_advertiser['contactinfo'], updated_json_data['contactinfo'])

    def test_get_advertiser_by_state(self):
        adv_state = "INACTIVE"
        advs = get_advertiser_by_state(adv_state)
        self.assertIsNotNone(advs)
        self.assertIn("test1Aditi", [advertiser['advertisername'] for advertiser in advs])


if __name__ == '__main__':
    unittest.main()
