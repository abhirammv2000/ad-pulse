import os
import sys
import unittest
from unittest.mock import Mock

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import refresh_cache  # noqa: E402


def session_returning(*outcomes):
    """A fake requests session. Each outcome is a status code or an exception."""
    session = Mock()
    replies = []
    for outcome in outcomes:
        if isinstance(outcome, Exception):
            replies.append(outcome)
        else:
            replies.append(Mock(status_code=outcome))
    session.get.side_effect = replies
    return session


class RefreshAllTest(unittest.TestCase):
    def test_calls_campaigns_then_ads_then_creatives(self):
        session = session_returning(200, 200, 200)
        failures = refresh_cache.refresh_all(session, 'http://manager')
        self.assertEqual(failures, 0)
        urls = [call.args[0] for call in session.get.call_args_list]
        self.assertEqual(urls, [
            'http://manager/cache/campaigns',
            'http://manager/cache/ads',
            'http://manager/cache/creatives',
        ])

    def test_every_request_has_a_timeout(self):
        session = session_returning(200, 200, 200)
        refresh_cache.refresh_all(session, 'http://manager')
        for call in session.get.call_args_list:
            self.assertEqual(call.kwargs['timeout'], refresh_cache.REQUEST_TIMEOUT_SECONDS)

    def test_a_connection_error_does_not_stop_the_other_calls(self):
        session = session_returning(requests.ConnectionError('down'), 200, 200)
        with self.assertLogs('refresh_cache', level='ERROR'):
            failures = refresh_cache.refresh_all(session, 'http://manager')
        self.assertEqual(failures, 1)
        self.assertEqual(session.get.call_count, 3)

    def test_a_non_200_counts_as_a_failure(self):
        session = session_returning(200, 500, 503)
        with self.assertLogs('refresh_cache', level='ERROR'):
            failures = refresh_cache.refresh_all(session, 'http://manager')
        self.assertEqual(failures, 2)


if __name__ == '__main__':
    unittest.main()
