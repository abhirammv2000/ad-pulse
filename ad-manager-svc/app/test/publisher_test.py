import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch

from app.services.publisher_service import (
    create_publisher,
    get_all_publishers,
    get_publisher_by_id,
    get_publisher_by_state,
    update_publisher,
    update_publisher_state,
)


@contextmanager
def _scope(session):
    """Stand-in for config.db.session_scope that hands back a given mock."""
    yield session


class TestPublisherService(unittest.TestCase):

    @patch('app.services.crud.session_scope')
    def test_get_all_publishers(self, mock_session_scope):
        mock_session = Mock()
        mock_session.query().all.return_value = [
            Mock(spec=['to_dict'], to_dict=lambda: {'publisherid': 'P123'})
        ]
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        result = get_all_publishers()
        assert result[0]['publisherid'] == 'P123'
        assert len(result) == 1

    @patch('app.services.crud.session_scope')
    def test_get_publisher_by_id(self, mock_session_scope):
        mock_session = Mock()
        mock_session.query().filter().first.return_value = Mock(
            spec=['to_dict'], to_dict=lambda: {'publisherid': 'P123'}
        )
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        result = get_publisher_by_id('P123')
        assert result['publisherid'] == 'P123'

    @patch('app.services.publisher_service.session_scope')
    def test_create_publisher(self, mock_session_scope):
        mock_session = Mock()
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        result = create_publisher(
            {'publishername': 'test', 'contactinfo': 'test', 'publisherdomain': 'test',
             'createdby': 'test', 'updatedby': 'test', 'preference': 'test'})

        assert result['publishername'] == 'test'
        assert result['publisherstate'] == 'CREATED'
        mock_session.add.assert_called_once()

    @patch('app.services.publisher_service.session_scope')
    def test_update_publisher(self, mock_session_scope):
        mock_session = Mock()
        publisher = Mock(publisherid='P123', publishername='old', publisherdomain='test')
        mock_session.query().filter_by().first.return_value = publisher
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        update_publisher({'publisherid': 'P123', 'publishername': 'testUpdate'})
        assert publisher.publishername == 'testUpdate'
        # Fields absent from the request are left untouched.
        assert publisher.publisherdomain == 'test'

    @patch('app.services.publisher_service.session_scope')
    def test_update_publisher_not_found(self, mock_session_scope):
        mock_session = Mock()
        mock_session.query().filter_by().first.return_value = None
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        assert update_publisher({'publisherid': 'missing'}) is None

    @patch('app.services.crud.session_scope')
    def test_update_publisher_state(self, mock_session_scope):
        mock_session = Mock()
        publisher = Mock(publisherid='P123', publisherstate='CREATED')
        mock_session.query().filter().first.return_value = publisher
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        assert update_publisher_state('P123', 'ACTIVE') is True
        assert publisher.publisherstate == 'ACTIVE'

    @patch('app.services.crud.session_scope')
    def test_update_publisher_state_not_found(self, mock_session_scope):
        mock_session = Mock()
        mock_session.query().filter().first.return_value = None
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        assert update_publisher_state('missing', 'ACTIVE') is False

    @patch('app.services.crud.session_scope')
    def test_get_publisher_by_state(self, mock_session_scope):
        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = [
            Mock(spec=['to_dict'], to_dict=lambda: {'publisherid': '1', 'publisherstate': 'State1'})
        ]
        mock_session_scope.side_effect = lambda: _scope(mock_session)

        result = get_publisher_by_state("State1")
        assert len(result) == 1


if __name__ == '__main__':
    unittest.main()
