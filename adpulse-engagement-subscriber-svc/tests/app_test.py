import json
import logging
import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import app  # noqa: E402


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


def message_with(payload):
    message = Mock()
    message.data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return message


class RecordEventTest(unittest.TestCase):
    def test_a_click_increments_click_and_starts_render_at_zero(self):
        collection = Mock()
        app.record_event(collection, 'AD1', 'click')
        collection.update_one.assert_called_once_with(
            {'_id': 'AD1'},
            {'$inc': {'click': 1}, '$setOnInsert': {'render': 0}},
            upsert=True,
        )

    def test_a_render_increments_render_and_starts_click_at_zero(self):
        collection = Mock()
        app.record_event(collection, 'AD1', 'render')
        collection.update_one.assert_called_once_with(
            {'_id': 'AD1'},
            {'$inc': {'render': 1}, '$setOnInsert': {'click': 0}},
            upsert=True,
        )


class CallbackTest(unittest.TestCase):
    def setUp(self):
        self.collection = Mock()
        self.callback = app.make_callback(self.collection, 'click')

    def test_a_good_message_is_recorded_and_acked(self):
        message = message_with({'adid': 'AD7'})
        self.callback(message)
        self.collection.update_one.assert_called_once()
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    def test_malformed_json_is_acked_so_it_stops_redelivering(self):
        message = message_with(b'{not json')
        self.callback(message)
        self.collection.update_one.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    def test_a_message_without_an_adid_is_acked_and_dropped(self):
        message = message_with({'something': 'else'})
        self.callback(message)
        self.collection.update_one.assert_not_called()
        message.ack.assert_called_once()

    def test_bytes_that_are_not_utf8_are_acked_and_dropped(self):
        message = message_with(b'\xff\xfe')
        self.callback(message)
        message.ack.assert_called_once()

    def test_a_database_error_is_nacked_so_pubsub_retries_it(self):
        self.collection.update_one.side_effect = RuntimeError('mongo is down')
        message = message_with({'adid': 'AD7'})
        self.callback(message)
        message.nack.assert_called_once()
        message.ack.assert_not_called()


if __name__ == '__main__':
    unittest.main()
