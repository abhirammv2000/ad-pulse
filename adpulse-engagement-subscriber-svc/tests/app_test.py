import json
import logging
import os
import sys
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import app  # noqa: E402

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


def event_body(ad_id='AD7', bid_id='B1', served_at=NOW):
    return {'adid': ad_id, 'bidid': bid_id, 'requesttimestamp': int(served_at.timestamp())}


def message_with(payload):
    message = Mock()
    message.data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return message


class ParseEventTest(unittest.TestCase):
    def test_reads_the_ad_the_bid_and_the_serve_time(self):
        self.assertEqual(app.parse_event(json.dumps(event_body()).encode()), ('AD7', 'B1', NOW))

    def test_anything_that_can_never_be_counted_is_a_bad_event(self):
        bad = [
            b'{not json',
            b'\xff\xfe',
            b'[1, 2]',
            json.dumps({'bidid': 'B1', 'requesttimestamp': 1}).encode(),
            json.dumps({'adid': 'AD1', 'requesttimestamp': 1}).encode(),
            json.dumps({'adid': 'AD1', 'bidid': 'B1'}).encode(),
            json.dumps({'adid': 'AD1', 'bidid': '', 'requesttimestamp': 1}).encode(),
            json.dumps({'adid': 'AD1', 'bidid': 'B1', 'requesttimestamp': 'yesterday'}).encode(),
            json.dumps({'adid': 'AD1', 'bidid': 'B1', 'requesttimestamp': True}).encode(),
            json.dumps({'adid': 'AD1', 'bidid': 'B1', 'requesttimestamp': 10**20}).encode(),
        ]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(app.BadEvent):
                app.parse_event(data)


class TooOldTest(unittest.TestCase):
    def test_an_event_served_more_than_48_hours_ago_is_not_counted_and_mongodb_is_not_touched(self):
        client, database = Mock(), Mock()
        served = NOW - timedelta(hours=48, seconds=1)
        result = app.record_event(client, database, 'click', 'AD1', 'B1', served, NOW)
        self.assertEqual(result, 'too_old')
        client.start_session.assert_not_called()

    def test_the_count_window_ends_before_the_inbox_forgets(self):
        # This is what makes a late copy impossible to count twice. See the comment on COUNT_WINDOW.
        self.assertLess(app.COUNT_WINDOW, app.INBOX_TTL)


class CallbackTest(unittest.TestCase):
    def setUp(self):
        self.callback = app.make_callback(Mock(), Mock(), 'click')

    @patch('app.record_event', return_value='counted')
    def test_a_counted_event_is_acked(self, record):
        message = message_with(event_body())
        self.callback(message)
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        self.assertEqual(record.call_args.args[2:6], ('click', 'AD7', 'B1', NOW))

    @patch('app.record_event', return_value='duplicate')
    def test_a_duplicate_is_acked(self, _):
        message = message_with(event_body())
        self.callback(message)
        message.ack.assert_called_once()

    @patch('app.record_event', return_value='too_old')
    def test_an_event_that_is_too_old_is_acked(self, _):
        message = message_with(event_body())
        self.callback(message)
        message.ack.assert_called_once()

    @patch('app.record_event')
    def test_a_bad_event_is_acked_without_trying_to_count_it(self, record):
        message = message_with(b'{not json')
        self.callback(message)
        record.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch('app.record_event', side_effect=RuntimeError('mongo is down'))
    def test_a_database_error_is_nacked_so_pubsub_retries_it(self, _):
        message = message_with(event_body())
        self.callback(message)
        message.nack.assert_called_once()
        message.ack.assert_not_called()


@unittest.skipUnless(os.getenv('MONGODB_TEST_URI'), 'set MONGODB_TEST_URI to a MongoDB replica set to run these')
class ExactlyOnceTest(unittest.TestCase):
    """Runs against a real MongoDB replica set, because the guarantee lives in its transactions."""

    @classmethod
    def setUpClass(cls):
        from pymongo import MongoClient

        cls.client = MongoClient(os.environ['MONGODB_TEST_URI'])

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        self.database = self.client[f'adpulse_test_{uuid.uuid4().hex[:8]}']
        app.prepare_database(self.database)

    def tearDown(self):
        self.client.drop_database(self.database.name)

    def record(self, event_type='click', bid_id='B1', ad_id='AD1'):
        return app.record_event(self.client, self.database, event_type, ad_id, bid_id, NOW, NOW)

    def report(self, ad_id='AD1'):
        return self.database.reports.find_one({'_id': ad_id})

    def test_an_event_is_counted(self):
        self.assertEqual(self.record(), 'counted')
        self.assertEqual(self.report(), {'_id': 'AD1', 'click': 1, 'render': 0})

    def test_a_replayed_url_is_counted_once(self):
        results = [self.record() for _ in range(5)]
        self.assertEqual(results, ['counted'] + ['duplicate'] * 4)
        self.assertEqual(self.report()['click'], 1)

    def test_a_message_delivered_again_after_its_commit_is_counted_once(self):
        # The worker commits, then dies before it can ack, so Pub/Sub sends the same message again.
        self.assertEqual(self.record(), 'counted')
        self.assertEqual(self.record(), 'duplicate')
        self.assertEqual(self.report()['click'], 1)

    def test_a_failure_between_the_two_writes_leaves_nothing_behind(self):
        # The inbox record is written, then the worker fails before the count is added. Without the transaction
        # the record would stay, the retry would see a "duplicate", and the click would never be counted.
        from pymongo.collection import Collection

        real_update_one = Collection.update_one

        def fail_on_reports(collection, *args, **kwargs):
            if collection.name == 'reports':
                raise ConnectionError('the worker died here')
            return real_update_one(collection, *args, **kwargs)

        with patch.object(Collection, 'update_one', autospec=True, side_effect=fail_on_reports):
            with self.assertRaises(ConnectionError):
                self.record()

        self.assertIsNone(self.database.inbox.find_one({'_id': 'click:B1'}))
        self.assertEqual(self.record(), 'counted')
        self.assertEqual(self.report()['click'], 1)

    def test_the_click_and_the_render_of_one_bid_both_count(self):
        self.record('click')
        self.record('render')
        self.assertEqual(self.report(), {'_id': 'AD1', 'click': 1, 'render': 1})

    def test_different_bids_of_the_same_ad_each_count(self):
        for bid_id in ('B1', 'B2', 'B3'):
            self.record(bid_id=bid_id)
        self.assertEqual(self.report()['click'], 3)

    def test_the_same_event_arriving_on_several_threads_at_once_is_counted_once(self):
        # Pub/Sub can hand two workers the same message. Their transactions collide on the inbox record, one
        # commits, and the other retries and finds it.
        threads, results = 12, []
        start = threading.Barrier(threads)
        lock = threading.Lock()

        def worker():
            start.wait()
            result = self.record(bid_id='SHARED')
            with lock:
                results.append(result)

        workers = [threading.Thread(target=worker) for _ in range(threads)]
        for thread in workers:
            thread.start()
        for thread in workers:
            thread.join()

        self.assertEqual(sorted(results), ['counted'] + ['duplicate'] * (threads - 1))
        self.assertEqual(self.report()['click'], 1)

    def test_the_inbox_forgets_after_72_hours(self):
        index = next(i for i in self.database.inbox.list_indexes() if i['key'] == {'seen_at': 1})
        self.assertEqual(index['expireAfterSeconds'], 72 * 3600)

    def test_preparing_the_database_twice_is_fine(self):
        app.prepare_database(self.database)


if __name__ == '__main__':
    unittest.main()
