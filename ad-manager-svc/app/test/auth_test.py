"""API key authentication. The service layer is never reached, so these need no database.

POST /ad with no body is used as the probe route: it answers 400 ("JSON object") without touching the database,
so a 400 means the request got past authentication and a 401 means it did not.
"""

import logging
import os
import unittest
from unittest.mock import patch

from app import create_app
from app.auth import API_KEY_HEADER, configured_keys, key_matches


def make_client(api_key):
    env = {} if api_key is None else {'API_KEY': api_key}
    with patch.dict(os.environ, env, clear=False):
        if api_key is None:
            os.environ.pop('API_KEY', None)
        with patch('app.init_db'):
            app = create_app()
    app.testing = False
    return app.test_client()


class ConfiguredKeysTest(unittest.TestCase):
    def test_splits_on_commas_and_trims(self):
        self.assertEqual(configured_keys({'API_KEY': ' one , two ,, '}), ['one', 'two'])

    def test_unset_or_blank_means_no_keys(self):
        self.assertEqual(configured_keys({}), [])
        self.assertEqual(configured_keys({'API_KEY': '   '}), [])
        self.assertEqual(configured_keys({'API_KEY': ' , '}), [])


class KeyMatchesTest(unittest.TestCase):
    def test_matches_any_configured_key(self):
        self.assertTrue(key_matches('b', ['a', 'b', 'c']))

    def test_rejects_other_values(self):
        self.assertFalse(key_matches('d', ['a', 'b']))
        self.assertFalse(key_matches('', ['a']))
        self.assertFalse(key_matches('aa', ['a']))
        self.assertFalse(key_matches('a', ['aa']))

    def test_no_keys_never_matches(self):
        self.assertFalse(key_matches('anything', []))
        self.assertFalse(key_matches('', []))

    def test_non_ascii_keys_work(self):
        # hmac.compare_digest on two str values raises for non-ASCII text, which is why digests are compared
        self.assertTrue(key_matches('clé-ü', ['clé-ü']))
        self.assertFalse(key_matches('clé-ü', ['cle-u']))


class WithoutAKeyTest(unittest.TestCase):
    def test_the_api_stays_open_and_says_so(self):
        with self.assertLogs('app.auth', level=logging.WARNING) as logs:
            client = make_client(None)
        self.assertIn('API_KEY is not set', logs.output[0])
        self.assertEqual(client.post('/ad').status_code, 400)

    def test_a_blank_key_counts_as_not_set(self):
        with self.assertLogs('app.auth', level=logging.WARNING):
            client = make_client('   ')
        self.assertEqual(client.post('/ad').status_code, 400)


class WithAKeyTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client('secret-one')

    def test_no_key_is_a_401(self):
        response = self.client.post('/ad')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'error': 'missing or invalid API key'})

    def test_a_wrong_key_is_a_401(self):
        self.assertEqual(self.client.post('/ad', headers={API_KEY_HEADER: 'nope'}).status_code, 401)

    def test_an_empty_key_is_a_401(self):
        self.assertEqual(self.client.post('/ad', headers={API_KEY_HEADER: ''}).status_code, 401)

    def test_the_right_key_gets_through_to_the_route(self):
        self.assertEqual(self.client.post('/ad', headers={API_KEY_HEADER: 'secret-one'}).status_code, 400)

    def test_every_method_is_protected(self):
        for method in ('get', 'post', 'put', 'patch', 'delete'):
            response = getattr(self.client, method)('/publisher')
            self.assertEqual(response.status_code, 401, method)

    def test_an_unknown_path_is_a_401_not_a_404(self):
        # so the API does not tell an unauthenticated caller which paths exist
        self.assertEqual(self.client.get('/no/such/path').status_code, 401)
        self.assertEqual(self.client.get('/no/such/path', headers={API_KEY_HEADER: 'secret-one'}).status_code, 404)

    def test_health_needs_no_key(self):
        self.assertEqual(self.client.get('/health').status_code, 200)

    def test_only_the_exact_health_path_is_open(self):
        self.assertEqual(self.client.get('/health/extra').status_code, 401)

    def test_a_cors_preflight_needs_no_key(self):
        """A browser never puts the key on a preflight, so this must pass or the dashboard cannot work."""
        response = self.client.options('/ad', headers={
            'Origin': 'http://dashboard.example',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'x-api-key,content-type',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://dashboard.example')
        self.assertIn('X-API-Key'.lower(), response.headers['Access-Control-Allow-Headers'].lower())

    def test_the_401_still_carries_cors_headers_so_the_browser_can_read_it(self):
        response = self.client.post('/ad', headers={'Origin': 'http://dashboard.example'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://dashboard.example')


class KeyRotationTest(unittest.TestCase):
    def test_old_and_new_keys_both_work_during_a_rotation(self):
        client = make_client('old-key, new-key')
        for key in ('old-key', 'new-key'):
            self.assertEqual(client.post('/ad', headers={API_KEY_HEADER: key}).status_code, 400, key)
        self.assertEqual(client.post('/ad', headers={API_KEY_HEADER: 'older-key'}).status_code, 401)


if __name__ == '__main__':
    unittest.main()
