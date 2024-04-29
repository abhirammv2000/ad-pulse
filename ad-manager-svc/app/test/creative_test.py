import unittest
from unittest.mock import patch, Mock
from app.services.creative_service import get_creative_by_id, create_creative, update_creative, update_creative_state, get_creative_by_state, get_all_creatives

class TestCreativeService(unittest.TestCase):
    @patch('app.services.creative_service.create_session')
    def test_get_creative_by_id(self, mock_create_session):
        mock_session = Mock()
        mock_get_cr = Mock(creativeid='C123')
        mock_session.query().filter_by().first.return_value = mock_get_cr
        mock_create_session.return_value = mock_session

        result = get_creative_by_id('C123')
        assert result['creativeid'] == 'C123'

    @patch('app.services.creative_service.create_session')
    def test_get_all_creatives(self, mock_create_session):
        mock_session = Mock()
        mock_get_all_crs = [
            Mock(creativeid='C123')
        ]
        mock_session.query().all.return_value = mock_get_all_crs
        mock_create_session.return_value = mock_session

        result = get_all_creatives()
        assert result[0]['creativeid'] == 'C123'
        assert len(result) == 1

    @patch('app.services.creative_service.create_session')
    def test_create_creative(self, mock_create_session):
        mock_create_session.return_value = Mock()

        result = create_creative(
            {'creativename': 'test', 'advertiserid': 'test', 'creativestate': 'test', 'creativetype': 'test',
             'createdby': 'test', 'updatedby': 'test', 'assets': 'test'})
        id = result['creativeid']
        ca = result['createdat']
        st = result['creativestate']
        ua = result['updatedat']
        assert result['creativename'] == 'test'
        assert result == {'creativeid': id, 'creativename': 'test', 'advertiserid': 'test', 'creativestate': st, 'creativetype': 'test', 'createdby': 'test', 'updatedby': 'test', 'createdat': ca, 'updatedat': ua, 'assets': 'test'}

    @patch('app.services.creative_service.create_session')
    def test_update_creative(self, mock_create_session):
        mock_create_session.return_value = Mock()

        cp = create_creative(
            {'creativename': 'test', 'advertiserid': 'test', 'creativestate': 'test', 'creativetype': 'test',
             'createdby': 'test', 'updatedby': 'test', 'assets': 'test'})
        id = cp['creativeid']
        result = update_creative(
            {'creativeid': id, 'creativename': 'testUpdate', 'advertiserid': 'test', 'creativestate': 'test',
             'creativetype': 'test', 'createdby': 'test', 'updatedby': 'test', 'assets': 'test'})
        assert result['creativename'] == 'testUpdate'

    @patch('app.services.creative_service.create_session')
    def test_update_creative_state(self, mock_create_session):
        mock_create_session.return_value = Mock()

        cp = create_creative(
            {'creativename': 'test', 'advertiserid': 'test', 'creativestate': 'test', 'creativetype': 'test',
             'createdby': 'test', 'updatedby': 'test', 'assets': 'test'})
        id = cp['creativeid']
        result = update_creative_state(id, 'ACTIVE')
        updated_cr = get_creative_by_id(id)
        assert updated_cr['creativestate'] == 'ACTIVE'

    @patch('app.services.creative_service.create_session')
    def test_get_creative_by_state(self, mock_create_session):
        mock_session = Mock()
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.all.return_value = [Mock(creativename='test', creativestate='ACTIVE')]
        mock_create_session.return_value = mock_session

        result = get_creative_by_state('ACTIVE')
        assert result[0]['creativename'] == 'test'
        assert result[0]['creativestate'] == 'ACTIVE'
        assert len(result) == 1



