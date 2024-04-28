# unit test for ad-service
import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from app.services.ad_service import get_all_ads, create_ad, get_ad_by_id, get_ad_by_state, update_ad_state, update_ad


class TestAdService(unittest.TestCase):

    @patch('app.services.ad_service.create_session')
    def test_get_all_ads(self, mock_create_session):
        mock_session = Mock()
        mock_get_all_ads = [Mock(adid='A123')]
        mock_session.query().all.return_value = mock_get_all_ads
        mock_create_session.return_value = mock_session

        result = get_all_ads()
        assert result[0]['adid'] == 'A123'
        assert len(result) == 1

    @patch('app.services.ad_service.create_session')
    def test_get_ad_by_id(self, mock_create_session):
        mock_session = Mock()
        mock_get_ad = Mock(adid='A123')
        mock_session.query().filter_by().first.return_value = mock_get_ad
        mock_create_session.return_value = mock_session

        result = get_ad_by_id('A123')
        assert result['adid'] == 'A123'

    @patch('app.services.ad_service.create_session')
    def test_create_ad(self, mock_create_session):
        mock_session = Mock()
        mock_create_session.return_value = mock_session

        mock_session.commit.return_value = None
        ad_data = {
            'adname': 'test', 'campaignid': 'test', 'advertiserid': 'test', 'creativeid': 'test',
             'startdate': datetime.now(), 'enddate': datetime.now(), 'landingurl': 'test', 'budget': 'test',
             'frequencycaps': 'test', 'bidinfo': 'test', 'adtype': 'test', 'adpriority': 'test',
             'targetinginfo': 'test', 'createdby': 'test', 'updatedby': 'test', 'adstate': 'test',
             'ad_unit_targeted': 'test'
        }

        result = create_ad(ad_data)

        id = result['adid']
        ca = result['createdat']
        st = result['adstate']
        ua = result['updatedat']
        sd = result['startdate']
        ed = result['enddate']
        assert result['adname'] == 'test'
        assert result == {'adid': id, 'adname': 'test', 'campaignid': 'test', 'advertiserid': 'test',
                          'creativeid': 'test', 'startdate': sd, 'enddate': ed, 'landingurl': 'test',
                          'budget': 'test', 'frequencycaps': 'test', 'bidinfo': 'test', 'adtype': 'test',
                          'adpriority': 'test', 'targetinginfo': 'test', 'createdby': 'test', 'updatedby': 'test',
                          'adstate': st, 'ad_unit_targeted': 'test', 'createdat': ca, 'updatedat': ua}

    @patch('app.services.ad_service.create_session')
    def test_update_ad(self, mock_create_session):
        mock_session = Mock()
        mock_create_session.return_value = mock_session

        result = create_ad(
            {'adname': 'test', 'campaignid': 'test', 'advertiserid': 'test', 'creativeid': 'test',
             'startdate': datetime.now(), 'enddate': datetime.now(), 'landingurl': 'test', 'budget': 'test',
             'frequencycaps': 'test', 'bidinfo': 'test', 'adtype': 'test', 'adpriority': 'test',
             'targetinginfo': 'test', 'createdby': 'test', 'updatedby': 'test', 'adstate': 'test',
             'ad_unit_targeted': 'test'})
        id = result['adid']
        ca = result['createdat']
        st = result['adstate']
        ua = result['updatedat']
        sd = datetime.now()
        ed = datetime.now()
        call_update = update_ad(
            {'adid': id, 'adname': 'testUpdate', 'campaignid': 'test', 'advertiserid': 'test', 'creativeid': 'test',
             'startdate': sd, 'enddate': ed, 'landingurl': 'test', 'budget': 'test', 'frequencycaps': 'test',
             'bidinfo': 'test', 'adtype': 'test', 'adpriority': 'test', 'targetinginfo': 'test', 'createdby': 'test',
             'updatedby': 'test', 'adstate': st, 'ad_unit_targeted': 'test', 'createdat': ca, 'updatedat': ua})
        updated_ad = get_ad_by_id(id)
        assert updated_ad['adname'] == 'testUpdate'
        assert call_update == True

    @patch('app.services.ad_service.create_session')
    def test_get_ad_by_state(self, mock_create_session):
        mock_session = Mock()
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.all.return_value = [
            Mock(adid='A123', adstate='CREATED')
        ]
        mock_create_session.return_value = mock_session

        result = get_ad_by_state('CREATED')
        assert result[0]['adid'] == 'A123'
        assert len(result) == 1

    @patch('app.services.ad_service.create_session')
    def test_update_ad_state(self, mock_create_session):
        mock_session = Mock()
        mock_create_session.return_value = mock_session

        created_ad = create_ad(
            {'adname': 'test', 'campaignid': 'test', 'advertiserid': 'test', 'creativeid': 'test',
             'startdate': datetime.now(), 'enddate': datetime.now(), 'landingurl': 'test', 'budget': 'test',
             'frequencycaps': 'test', 'bidinfo': 'test', 'adtype': 'test', 'adpriority': 'test',
             'targetinginfo': 'test', 'createdby': 'test', 'updatedby': 'test', 'adstate': 'CREATED',
             'ad_unit_targeted': 'test'})
        id = created_ad['adid']
        ua = update_ad_state(id, 'ACTIVE')
        result = get_ad_by_id(id)
        assert result['adstate'] == 'ACTIVE'
        assert ua == True
