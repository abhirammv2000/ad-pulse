import unittest
from unittest.mock import patch, Mock

from app.services.advertiser_service import get_all_advertisers, create_advertiser, get_advertiser_by_id, \
    get_advertiser_by_state, update_advertiser_state, update_advertiser


class TestAdvertiserService(unittest.TestCase):

    @patch('app.services.advertiser_service.create_session')
    def test_get_all_advertisers(self, mock_create_session):
        mock_session = Mock()
        mock_get_all_ads = [
            Mock(advertiserid='A123')
        ]
        mock_session.query().all.return_value = mock_get_all_ads
        mock_create_session.return_value = mock_session

        result = get_all_advertisers()
        assert result[0]['advertiserid'] == 'A123'
        assert len(result) == 1

    @patch('app.services.advertiser_service.create_session')
    def test_get_advertiser_by_id(self, mock_create_session):
        mock_session = Mock()
        mock_get_ad = Mock(advertiserid='A123')
        mock_session.query().filter_by().first.return_value = mock_get_ad
        mock_create_session.return_value = mock_session

        result = get_advertiser_by_id('A123')
        assert result['advertiserid'] == 'A123'

    @patch('app.services.advertiser_service.create_session')
    def test_create_advertiser(self, mock_create_session):
        mock_create_session.return_value = Mock()

        result = create_advertiser(
            {'advertisername': 'test', 'industry': 'test', 'brands': 'test', 'contactinfo': 'test',
             'advertisertype': 'test', 'createdby': 'test', 'updatedby': 'test', 'advertiserstate': 'test'})
        id = result['advertiserid']
        ca = result['createdat']
        st = result['advertiserstate']
        ua = result['updatedat']
        assert result['advertisername'] == 'test'
        assert result == {'advertiserid': id, 'advertisername': 'test', 'industry': 'test', 'brands': 'test',
                          'contactinfo': 'test', 'advertisertype': 'test', 'createdby': 'test', 'updatedby': 'test',
                          'advertiserstate': st, 'createdat': ca, 'updatedat': ua}

    @patch('app.services.advertiser_service.create_session')
    def test_update_advertiser(self, mock_create_session):
        mock_create_session.return_value = Mock()

        ca = create_advertiser(
            {'advertisername': 'test', 'industry': 'test', 'brands': 'test', 'contactinfo': 'test',
             'advertisertype': 'test', 'createdby': 'test', 'updatedby': 'test', 'advertiserstate': 'test'})
        id = ca['advertiserid']
        result = update_advertiser(
            {'advertiserid': id, 'advertisername': 'testUpdate', 'industry': 'test', 'brands': 'test',
             'contactinfo': 'test', 'advertisertype': 'test', 'createdby': 'test', 'updatedby': 'test',
             'advertiserstate': 'test'})
        assert result['advertisername'] == 'testUpdate'

    @patch('app.services.advertiser_service.create_session')
    def test_update_advertiser_state(self, mock_create_session):
        mock_create_session.return_value = Mock()

        ca = create_advertiser(
            {'advertisername': 'test', 'industry': 'test', 'brands': 'test', 'contactinfo': 'test',
             'advertisertype': 'test', 'createdby': 'test', 'updatedby': 'test', 'advertiserstate': 'test'})
        id = ca['advertiserid']
        result = update_advertiser_state(id, 'testUpdate')
        assert result == True

    @patch('app.services.advertiser_service.create_session')
    def test_get_advertiser_by_state(self, mock_create_session):
        mock_session = Mock()
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.all.return_value = [ Mock(advertisername= 'test', advertiserstate= 'test')]
        mock_create_session.return_value = mock_session
        result = get_advertiser_by_state("test")
        assert len(result) == 1



