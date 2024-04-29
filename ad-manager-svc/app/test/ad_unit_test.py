import unittest
from unittest.mock import patch, Mock
from app.services.ad_unit_service import get_ad_unit_by_id, create_ad_unit, update_ad_unit, update_ad_unit_state, \
    get_ad_unit_by_state, get_all_ad_units


class TestAdUnitService(unittest.TestCase):

    @patch('app.services.ad_unit_service.create_session')
    def test_get_ad_unit_by_id(self, mock_create_session):
        mock_session = Mock()
        mock_get_ad = Mock(adunitid='A123')
        mock_session.query().filter_by().first.return_value = mock_get_ad
        mock_create_session.return_value = mock_session

        result = get_ad_unit_by_id('A123')
        assert result['adunitid'] == 'A123'

    @patch('app.services.ad_unit_service.create_session')
    def test_get_all_ad_units(self, mock_create_session):
        mock_session = Mock()
        mock_get_all_ads = [
            Mock(adunitid='A123')
        ]
        mock_session.query().all.return_value = mock_get_all_ads
        mock_create_session.return_value = mock_session

        result = get_all_ad_units()
        assert result[0]['adunitid'] == 'A123'
        assert len(result) == 1

    @patch('app.services.ad_unit_service.create_session')
    def test_create_ad_unit(self, mock_create_session):
        mock_create_session.return_value = Mock()

        result = create_ad_unit(
            {'adunitname': 'test', 'publisherid': 'test', 'adunitstate': 'test', 'adunitdomain': 'test',
             'createdby': 'test', 'updatedby': 'test', 'preference': 'test','adunittype': 'test'})
        id = result['adunitid']
        ca = result['createdat']
        st = result['adunitstate']
        ua = result['updatedat']
        print(result)
        assert result['adunitname'] == 'test'
        assert result == {'adunitid': id, 'adunittype': 'test', 'adunitname': 'test', 'publisherid': 'test', 'adunitstate': st, 'createdby': 'test', 'updatedby': 'test', 'createdat': ca, 'updatedat': ua, 'preference': 'test'}

    @patch('app.services.ad_unit_service.create_session')
    def test_update_ad_unit(self, mock_create_session):
        mock_create_session.return_value = Mock()

        cp = create_ad_unit(
            {'adunitname': 'test', 'publisherid': 'test', 'adunitstate': 'test', 'adunitdomain': 'test',
             'createdby': 'test', 'updatedby': 'test', 'preference': 'test','adunittype': 'test'})
        id = cp['adunitid']
        result = update_ad_unit(
            {'adunitid': id, 'adunitname': 'testUpdate', 'publisherid': 'test', 'adunitstate': 'test',
             'adunitdomain': 'test', 'createdby': 'test', 'updatedby': 'test', 'preference': 'test','adunittype': 'test'})
        assert result['adunitname'] == 'testUpdate'

    @patch('app.services.ad_unit_service.create_session')
    def test_update_ad_unit_state(self, mock_create_session):
        mock_create_session.return_value = Mock()

        cp = create_ad_unit(
            {'adunitname': 'test', 'publisherid': 'test', 'adunitstate': 'test', 'adunitdomain': 'test',
             'createdby': 'test', 'updatedby': 'test', 'preference': 'test','adunittype': 'test'})
        id = cp['adunitid']
        result = update_ad_unit_state(id, 'ACTIVE')
        updated_ad = get_ad_unit_by_id(id)
        assert updated_ad['adunitstate'] == 'ACTIVE'


    @patch('app.services.ad_unit_service.create_session')
    def test_get_ad_unit_by_state(self, mock_create_session):
        mock_session = Mock()
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.all.return_value = [
            Mock(adunitname='test', adunitstate='test')
        ]
        mock_create_session.return_value = mock_session
        result = get_ad_unit_by_state('test')
        assert result[0]['adunitname'] == 'test'
        assert result[0]['adunitstate'] == 'test'
        assert len(result) == 1
