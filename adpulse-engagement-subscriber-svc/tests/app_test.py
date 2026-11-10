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


def event_body(ad_id='AD7', bid_id='B1', served_at=NOW, **extra):
    body = {'adid': ad_id, 'campaignid': 'C1', 'bidid': bid_id, 'requesttimestamp': int(served_at.timestamp())}
    body.update(extra)
    return body


def engagement(ad_id='AD1', bid_id='B1', bid_type='', price=0, served_at=NOW, campaign_id='C1', user_id='', counters=()):
    return app.Engagement(ad_id, campaign_id, bid_id, served_at, bid_type, price, user_id, tuple(counters))


def message_with(payload):
    message = Mock()
    message.data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return message


class ParseEventTest(unittest.TestCase):
    def test_reads_the_ad_the_bid_the_serve_time_and_the_price(self):
        event = app.parse_event(json.dumps(event_body(bidtype='CPM', pricenanos=1000)).encode())
        self.assertEqual(event, app.Engagement('AD7', 'C1', 'B1', NOW, 'CPM', 1000))

    def test_an_ad_with_no_bid_has_no_price(self):
        event = app.parse_event(json.dumps(event_body()).encode())
        self.assertEqual((event.bid_type, event.price_nanos), ('', 0))

    def test_a_capped_ad_names_its_user_and_counters(self):
        event = app.parse_event(json.dumps(event_body(userid='alice', counters=['AD:CSC', 'CAMPAIGN:CLK'])).encode())
        self.assertEqual((event.user_id, event.counters), ('alice', ('AD:CSC', 'CAMPAIGN:CLK')))

    def test_an_uncapped_ad_has_no_user_or_counters(self):
        event = app.parse_event(json.dumps(event_body()).encode())
        self.assertEqual((event.user_id, event.counters), ('', ()))

    def test_anything_that_can_never_be_counted_is_a_bad_event(self):
        bad = [
            b'{not json',
            b'\xff\xfe',
            b'[1, 2]',
            json.dumps({'campaignid': 'C1', 'bidid': 'B1', 'requesttimestamp': 1}).encode(),
            json.dumps({'adid': 'AD1', 'bidid': 'B1', 'requesttimestamp': 1}).encode(),
            json.dumps({'adid': 'AD1', 'campaignid': 'C1', 'requesttimestamp': 1}).encode(),
            json.dumps({'adid': 'AD1', 'campaignid': 'C1', 'bidid': 'B1'}).encode(),
            json.dumps({'adid': 'AD1', 'campaignid': 'C1', 'bidid': '', 'requesttimestamp': 1}).encode(),
            json.dumps({'adid': 'AD1', 'campaignid': 'C1', 'bidid': 'B1', 'requesttimestamp': 'yesterday'}).encode(),
            json.dumps({'adid': 'AD1', 'campaignid': 'C1', 'bidid': 'B1', 'requesttimestamp': True}).encode(),
            json.dumps({'adid': 'AD1', 'campaignid': 'C1', 'bidid': 'B1', 'requesttimestamp': 10**20}).encode(),
            json.dumps(event_body(pricenanos=-1)).encode(),
            json.dumps(event_body(pricenanos=1.5)).encode(),
            json.dumps(event_body(pricenanos='1000')).encode(),
            json.dumps(event_body(bidtype=7)).encode(),
            json.dumps(event_body(userid=7)).encode(),
            json.dumps(event_body(counters='AD:CSC')).encode(),
            json.dumps(event_body(counters=['AD:VIEW'])).encode(),
            json.dumps(event_body(counters=['ADVERTISER:CSC'])).encode(),
        ]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(app.BadEvent):
                app.parse_event(data)


class ChargeTest(unittest.TestCase):
    def test_a_cpm_ad_pays_for_renders_and_a_cpc_ad_for_clicks(self):
        cases = [
            ('render', 'CPM', 1000),
            ('click', 'CPM', 0),
            ('click', 'CPC', 1000),
            ('render', 'CPC', 0),
            ('render', '', 0),
            ('click', 'CPD', 0),
        ]
        for event_type, bid_type, want in cases:
            with self.subTest(event_type=event_type, bid_type=bid_type):
                self.assertEqual(app.charge(event_type, engagement(bid_type=bid_type, price=1000)), want)

    def test_the_ad_and_the_campaign_are_charged_in_total_and_for_the_day_the_ad_was_served(self):
        served = datetime(2026, 11, 7, 23, 59, 30, tzinfo=timezone.utc)
        ids = [spend_id for spend_id, _ in app.spend_totals(engagement(served_at=served))]
        self.assertEqual(ids, ['ad:AD1', 'ad:AD1:2026-11-07', 'campaign:C1', 'campaign:C1:2026-11-07'])


class CounterKeysTest(unittest.TestCase):
    def test_an_event_goes_into_the_counters_of_its_own_type(self):
        event = engagement(user_id='alice', counters=['AD:CSC', 'CAMPAIGN:CSC', 'CAMPAIGN:CLK'])
        self.assertEqual(app.counter_keys('render', event), ['fc:AD:AD1:CSC:alice', 'fc:CAMPAIGN:C1:CSC:alice'])
        self.assertEqual(app.counter_keys('click', event), ['fc:CAMPAIGN:C1:CLK:alice'])

    def test_no_user_means_no_counters(self):
        self.assertEqual(app.counter_keys('render', engagement(counters=['AD:CSC'])), [])


class TooOldTest(unittest.TestCase):
    def test_an_event_served_more_than_48_hours_ago_is_not_counted_and_nothing_is_touched(self):
        client, database, redis_client = Mock(), Mock(), Mock()
        event = engagement(served_at=NOW - timedelta(hours=48, seconds=1))
        result = app.record_event(client, database, redis_client, 'click', event, NOW)
        self.assertEqual(result, 'too_old')
        client.start_session.assert_not_called()
        redis_client.pipeline.assert_not_called()

    def test_the_count_window_ends_before_the_inbox_forgets(self):
        # This is what makes a late copy impossible to count twice. See the comment on COUNT_WINDOW.
        self.assertLess(app.COUNT_WINDOW, app.INBOX_TTL)


class CallbackTest(unittest.TestCase):
    def setUp(self):
        self.callback = app.make_callback(Mock(), Mock(), Mock(), 'click')

    @patch('app.record_event', return_value='counted')
    def test_a_counted_event_is_acked(self, record):
        message = message_with(event_body())
        self.callback(message)
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        self.assertEqual(record.call_args.args[3:5], ('click', app.Engagement('AD7', 'C1', 'B1', NOW, '', 0)))

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


class MongoTestCase(unittest.TestCase):
    """A fresh database on a real MongoDB replica set, because the guarantee lives in its transactions."""

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
        self.redis = Mock()  # replaced in the spend tests, unused for events with no price

    def tearDown(self):
        self.client.drop_database(self.database.name)

    def record(self, event_type='click', event=None):
        return app.record_event(self.client, self.database, self.redis, event_type, event or engagement(), NOW)

    def report(self, ad_id='AD1'):
        return self.database.reports.find_one({'_id': ad_id})


@unittest.skipUnless(os.getenv('MONGODB_TEST_URI'), 'set MONGODB_TEST_URI to a MongoDB replica set to run these')
class ExactlyOnceTest(MongoTestCase):
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
            self.record(event=engagement(bid_id=bid_id))
        self.assertEqual(self.report()['click'], 3)

    def test_the_same_event_arriving_on_several_threads_at_once_is_counted_once(self):
        # Pub/Sub can hand two workers the same message. Their transactions collide on the inbox record, one
        # commits, and the other retries and finds it.
        threads, results = 12, []
        start = threading.Barrier(threads)
        lock = threading.Lock()

        def worker():
            start.wait()
            result = self.record(event=engagement(bid_id='SHARED'))
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


class RedisTestCase(MongoTestCase):
    """MongoDB and a real Redis. Each test uses its own ad and campaign ids, so nothing needs flushing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import redis

        cls.real_redis = redis.Redis.from_url(os.environ['REDIS_TEST_URL'], decode_responses=True)

    @classmethod
    def tearDownClass(cls):
        cls.real_redis.close()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.redis = self.real_redis
        self.ad, self.campaign = f'AD{uuid.uuid4().hex[:8]}', f'C{uuid.uuid4().hex[:8]}'


@unittest.skipUnless(
    os.getenv('MONGODB_TEST_URI') and os.getenv('REDIS_TEST_URL'),
    'set MONGODB_TEST_URI and REDIS_TEST_URL to run these',
)
class SpendTest(RedisTestCase):
    """Spend is added in the transaction and copied to Redis."""

    def cpm_render(self, bid_id='B1', price=1_000_000):
        return self.record('render', engagement(self.ad, bid_id, 'CPM', price, campaign_id=self.campaign))

    def spent(self):
        """The four totals, from MongoDB and from Redis."""
        ids = [f'ad:{self.ad}', f'ad:{self.ad}:2026-11-08', f'campaign:{self.campaign}', f'campaign:{self.campaign}:2026-11-08']
        rows = {row['_id']: row['nanos'] for row in self.database.spend.find({'_id': {'$in': ids}})}
        mongo = [rows.get(i) for i in ids]
        cached = [None if v is None else int(v) for v in self.redis.mget([f'spend:{i}' for i in ids])]
        return mongo, cached

    def test_a_billable_event_adds_its_price_to_all_four_totals_in_both_places(self):
        self.cpm_render(price=1_000_000)
        self.cpm_render(bid_id='B2', price=500)
        mongo, cached = self.spent()
        self.assertEqual(mongo, [1_000_500] * 4)
        self.assertEqual(cached, [1_000_500] * 4)

    def test_an_event_its_bid_type_does_not_pay_for_costs_nothing(self):
        self.record('click', engagement(self.ad, 'B1', 'CPM', 1_000_000, campaign_id=self.campaign))
        self.assertEqual(self.spent(), ([None] * 4, [None] * 4))

    def test_a_replay_is_not_charged_twice(self):
        for _ in range(4):
            self.cpm_render()
        mongo, cached = self.spent()
        self.assertEqual(mongo, [1_000_000] * 4)
        self.assertEqual(cached, [1_000_000] * 4)

    def test_if_redis_fails_after_the_commit_the_redelivery_repairs_it(self):
        broken = Mock()
        broken.register_script.side_effect = ConnectionError('redis is down')
        self.redis = broken
        with self.assertRaises(ConnectionError):
            self.cpm_render()

        # Pub/Sub delivers it again. It is a duplicate now, so nothing is charged twice, but Redis gets the totals.
        self.redis = self.real_redis
        self.assertEqual(self.cpm_render(), 'duplicate')
        self.assertEqual(self.spent(), ([1_000_000] * 4, [1_000_000] * 4))

    def test_a_late_smaller_total_never_overwrites_a_larger_one(self):
        key = f'ad:{self.ad}'
        ttl = {key: app.TOTAL_SPEND_TTL}
        app.copy_spend_to_redis(self.redis, {key: 300}, ttl)
        app.copy_spend_to_redis(self.redis, {key: 200}, ttl)
        self.assertEqual(self.redis.get(f'spend:{key}'), '300')
        app.copy_spend_to_redis(self.redis, {key: 301}, ttl)
        self.assertEqual(self.redis.get(f'spend:{key}'), '301')

    def test_totals_past_two_to_the_53_compare_exactly(self):
        # A double can't tell each of these pairs apart. Compared as numbers in Lua, the second, larger value would
        # look equal to the first and be dropped, and the ad would look like it had spent less than it has.
        key = f'ad:{self.ad}'
        ttl = {key: app.TOTAL_SPEND_TTL}
        for smaller, larger in ((2**53, 2**53 + 1), (10**18 - 1, 10**18)):
            app.copy_spend_to_redis(self.redis, {key: smaller}, ttl)
            app.copy_spend_to_redis(self.redis, {key: larger}, ttl)
            self.assertEqual(self.redis.get(f'spend:{key}'), str(larger))
            app.copy_spend_to_redis(self.redis, {key: smaller}, ttl)
            self.assertEqual(self.redis.get(f'spend:{key}'), str(larger))

    def test_daily_totals_expire_sooner_than_the_overall_totals(self):
        self.cpm_render()
        daily = self.redis.ttl(f'spend:ad:{self.ad}:2026-11-08')
        total = self.redis.ttl(f'spend:ad:{self.ad}')
        self.assertTrue(47 * 3600 < daily <= 48 * 3600, daily)
        self.assertTrue(29 * 86400 < total <= 30 * 86400, total)

    def test_many_events_of_one_ad_at_once_add_up_exactly(self):
        # Every transaction writes the same four totals, so they conflict and retry. None may be lost.
        threads = 12
        start = threading.Barrier(threads)

        def worker(n):
            start.wait()
            self.cpm_render(bid_id=f'B{n}', price=1_000 + n)

        workers = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
        for thread in workers:
            thread.start()
        for thread in workers:
            thread.join()

        want = sum(1_000 + n for n in range(threads))
        self.assertEqual(self.spent(), ([want] * 4, [want] * 4))


@unittest.skipUnless(
    os.getenv('MONGODB_TEST_URI') and os.getenv('REDIS_TEST_URL'),
    'set MONGODB_TEST_URI and REDIS_TEST_URL to run these',
)
class CounterTest(RedisTestCase):
    """A capped ad's events go into its user's sorted sets, which the ad server's caps count."""

    def setUp(self):
        super().setUp()
        self.user = f'u{uuid.uuid4().hex[:8]}'
        self.key = f'fc:AD:{self.ad}:CSC:{self.user}'

    def capped_render(self, bid_id='B1', served_at=NOW):
        event = engagement(self.ad, bid_id, campaign_id=self.campaign, served_at=served_at,
                           user_id=self.user, counters=['AD:CSC'])
        return self.record('render', event)

    def test_a_render_is_recorded_at_its_serve_time(self):
        self.capped_render()
        self.assertEqual(self.redis.zrange(self.key, 0, -1, withscores=True), [('B1', NOW.timestamp())])

    def test_a_replay_is_recorded_once(self):
        for _ in range(3):
            self.capped_render()
        self.assertEqual(self.redis.zcard(self.key), 1)

    def test_each_served_bid_is_its_own_event(self):
        for bid_id in ('B1', 'B2', 'B3'):
            self.capped_render(bid_id)
        self.assertEqual(self.redis.zcard(self.key), 3)

    def test_events_older_than_a_week_are_dropped(self):
        self.redis.zadd(self.key, {'ancient': NOW.timestamp() - 7 * 86400 - 1, 'week_old': NOW.timestamp() - 7 * 86400})
        self.capped_render()
        self.assertEqual(sorted(self.redis.zrange(self.key, 0, -1)), ['B1', 'week_old'])

    def test_at_most_1000_events_are_kept_and_the_oldest_go_first(self):
        self.redis.zadd(self.key, {f'old{n}': NOW.timestamp() - 1000 + n for n in range(1005)})
        self.capped_render()
        self.assertEqual(self.redis.zcard(self.key), 1000)
        self.assertIsNone(self.redis.zscore(self.key, 'old0'))
        self.assertIsNotNone(self.redis.zscore(self.key, 'B1'))

    def test_a_counter_expires_a_day_after_the_longest_window(self):
        self.capped_render()
        self.assertTrue(7 * 86400 < self.redis.ttl(self.key) <= 8 * 86400)

    def test_if_redis_fails_the_redelivery_records_the_event(self):
        broken = Mock()
        broken.pipeline.side_effect = ConnectionError('redis is down')
        self.redis = broken
        with self.assertRaises(ConnectionError):
            self.capped_render()

        self.redis = self.real_redis
        self.assertEqual(self.capped_render(), 'duplicate')
        self.assertEqual(self.redis.zcard(self.key), 1)


if __name__ == '__main__':
    unittest.main()
