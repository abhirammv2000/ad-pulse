from unittest.mock import patch, Mock
import unittest

from app.services.publisher_service import get_all_publishers, create_publisher, get_publisher_by_id, update_publisher, \
    update_publisher_state, get_publisher_by_state


class TestPublisherService(unittest.TestCase):

    @patch('app.services.publisher_service.create_session')
    def test_get_all_publishers(self, mock_create_session):
        mock_session = Mock()
        mock_get_all_pbs = [
            Mock(publisherid='P123')
        ]
        mock_session.query().all.return_value = mock_get_all_pbs
        mock_create_session.return_value = mock_session

        result = get_all_publishers()
        assert result[0]['publisherid'] == 'P123'
        assert len(result) == 1

    @patch('app.services.publisher_service.create_session')
    def test_get_publisher_by_id(self, mock_create_session):
        mock_session = Mock()
        mock_get_pb = Mock(publisherid='P123')
        mock_session.query().filter_by().first.return_value = mock_get_pb
        mock_create_session.return_value = mock_session

        result = get_publisher_by_id('P123')
        # print("!!!@@@###", result)
        assert result['publisherid'] == 'P123'

    @patch('app.services.publisher_service.create_session')
    def test_create_publisher(self, mock_create_session):
        mock_create_session.return_value = Mock()

        result = create_publisher(
            {'publishername': 'test', 'contactinfo': 'test', 'publisherstate': 'test', 'publisherdomain': 'test',
             'createdby': 'test', 'updatedby': 'test', 'preference': 'test'})
        id = result['publisherid']
        ca = result['createdat']
        st = result['publisherstate']
        ua = result['updatedat']
        assert result['publishername'] == 'test'
        # print(result)
        assert result == {'publisherid': id, 'publishername': 'test', 'contactinfo': 'test', 'publisherstate': st,
                          'publisherdomain': 'test', 'createdby': 'test', 'updatedby': 'test', 'preference': 'test',
                          'createdat': ca, 'updatedat': ua}

    @patch('app.services.publisher_service.create_session')
    def test_update_publisher(self, mock_create_session):
        mock_create_session.return_value = Mock()

        cp = create_publisher(
            {'publishername': 'test', 'contactinfo': 'test', 'publisherstate': 'test', 'publisherdomain': 'test',
             'createdby': 'test', 'updatedby': 'test', 'preference': 'test'})
        id = cp['publisherid']
        result = update_publisher(
            {'publisherid': id, 'publishername': 'testUpdate', 'contactinfo': 'test', 'publisherstate': 'test',
             'publisherdomain': 'test', 'createdby': 'test', 'updatedby': 'test', 'preference': 'test'})
        assert result['publishername'] == 'testUpdate'

    @patch('app.services.publisher_service.create_session')
    def test_update_publisher_state(self, mock_create_session):
        mock_create_session.return_value = Mock()

        cp = create_publisher(
            {'publishername': 'test', 'contactinfo': 'test', 'publisherstate': 'CREATED', 'publisherdomain': 'test',
             'createdby': 'test', 'updatedby': 'test', 'preference': 'test'})
        id = cp['publisherid']

        result = update_publisher_state(id, 'ACTIVE')
        pb = get_publisher_by_id(id)
        assert result == True
        assert pb['publisherstate'] == 'ACTIVE'

    @patch('app.services.publisher_service.create_session')
    def test_get_publisher_by_state(self, mock_create_session):
        mock_session = Mock()
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.all.return_value = [
            Mock(publisherid=1, publishername="Publisher1", contactinfo="Contact1", publisherstate="State1",
                 publisherdomain="Domain1", createdby="Creator1", updatedby="Updater1",
                 preference="Preference1")
        ]

        mock_create_session.return_value = mock_session
        result = get_publisher_by_state("State1")
        assert len(result) == 1
