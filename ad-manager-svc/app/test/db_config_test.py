import os
import unittest
from unittest.mock import patch

from config import db


class DatabaseUrlTest(unittest.TestCase):
    def url_for(self, value):
        with patch.dict(os.environ, {'DATABASE_URL': value}):
            return db._get_database_url()

    def test_a_plain_postgres_url_names_the_psycopg2_driver(self):
        self.assertEqual(
            self.url_for('postgresql://user:pw@db:5432/adpulse'),
            'postgresql+psycopg2://user:pw@db:5432/adpulse',
        )

    def test_a_url_that_already_names_a_driver_is_left_alone(self):
        url = 'postgresql+psycopg2://user:pw@db:5432/adpulse'
        self.assertEqual(self.url_for(url), url)

    def test_a_missing_url_explains_what_to_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                db._get_database_url()
        self.assertIn('DATABASE_URL', str(context.exception))


if __name__ == '__main__':
    unittest.main()
