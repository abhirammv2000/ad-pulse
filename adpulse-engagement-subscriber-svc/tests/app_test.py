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
        served = int(datetime(2026, 11, 7, 23, 59, 30, tzinfo=timezone.utc).timestamp())
        ids = [spend_id for spend_id, _ in app.spend_totals('AD1', 'C1', served)]
        self.assertEqual(ids, ['ad:AD1', 'ad:AD1:2026-11-07', 'campaign:C1', 'campaign:C1:2026-11-07'])


class CounterKeysTest(unittest.TestCase):
    def test_an_event_goes_into_the_counters_of_its_own_type(self):
        event = engagement(user_id='alice', counters=['AD:CSC', 'CAMPAIGN:CSC', 'CAMPAIGN:CLK'])
        self.assertEqual(app.counter_keys('render', event), ['fc:AD:AD1:CSC:alice', 'fc:CAMPAIGN:C1:CSC:alice'])
        self.assertEqual(app.counter_keys('click', event), ['fc:CAMPAIGN:C1:CLK:alice'])

    def test_no_user_means_no_counters(self):
        self.assertEqual(app.counter_keys('render', engagement(counters=['AD:CSC'])), [])


class TooOldTest(unittest.TestCase):
    def test_an_event_served_more_than_48_hours_ago_is_not_recorded_and_nothing_is_touched(self):
        database, redis_client = Mock(), Mock()
        event = engagement(served_at=NOW - timedelta(hours=48, seconds=1))
        result = app.record_event(database, redis_client, 'click', event, NOW)
        self.assertEqual(result, 'too_old')
        database.inbox.insert_one.assert_not_called()
        redis_client.pipeline.assert_not_called()

    def test_the_count_window_ends_before_the_inbox_forgets(self):
        # This is what makes a late copy impossible to count twice. See the comment on COUNT_WINDOW.
        self.assertLess(app.COUNT_WINDOW, app.INBOX_TTL)


class CallbackTest(unittest.TestCase):
    def setUp(self):
        self.callback = app.make_callback(Mock(), Mock(), 'click')

    @patch('app.record_event', return_value='recorded')
    def test_a_recorded_event_is_acked(self, record):
        message = message_with(event_body())
        self.callback(message)
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        self.assertEqual(record.call_args.args[2:4], ('click', app.Engagement('AD7', 'C1', 'B1', NOW, '', 0)))

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
    def test_a_bad_event_is_acked_without_trying_to_record_it(self, record):
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


class FoldForeverTest(unittest.TestCase):
    def test_a_failed_fold_is_counted_and_the_loop_keeps_going(self):
        from prometheus_client import REGISTRY

        failures = REGISTRY.get_sample_value('subscriber_fold_failures_total') or 0
        stop = threading.Event()
        calls = []

        def fold(*_):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('mongo is down')
            stop.set()
            return 0

        with patch('app.fold', side_effect=fold), patch.object(app, 'FOLD_INTERVAL', 0):
            app.fold_forever(Mock(), Mock(), Mock(), stop)

        self.assertEqual(len(calls), 2)
        self.assertEqual((REGISTRY.get_sample_value('subscriber_fold_failures_total') or 0) - failures, 1)


class MetricsTest(unittest.TestCase):
    """The metrics are global, so these compare counts before and after."""

    def count(self, result):
        from prometheus_client import REGISTRY

        return REGISTRY.get_sample_value('subscriber_events_total', {'event': 'click', 'result': result}) or 0

    def test_every_outcome_is_counted(self):
        callback = app.make_callback(Mock(), Mock(), 'click')
        before = {r: self.count(r) for r in ('recorded', 'duplicate', 'too_old', 'malformed', 'failed')}

        for result in ('recorded', 'duplicate', 'too_old'):
            with patch('app.record_event', return_value=result):
                callback(message_with(event_body()))
        callback(message_with(b'{not json'))
        with patch('app.record_event', side_effect=RuntimeError('down')):
            callback(message_with(event_body()))

        for result, was in before.items():
            self.assertEqual(self.count(result) - was, 1, result)


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
        self.redis = Mock()  # replaced in the Redis tests, unused by events with no price or counters

    def tearDown(self):
        self.client.drop_database(self.database.name)

    def record(self, event_type='click', event=None):
        return app.record_event(self.database, self.redis, event_type, event or engagement(), NOW)

    def fold(self, batch=app.FOLD_BATCH):
        return app.fold(self.client, self.database, self.redis, NOW, batch)

    def fold_all(self):
        total = 0
        while True:
            folded = self.fold()
            total += folded
            if folded == 0:
                return total

    def report(self, ad_id='AD1'):
        return self.database.reports.find_one({'_id': ad_id})


@unittest.skipUnless(os.getenv('MONGODB_TEST_URI'), 'set MONGODB_TEST_URI to a MongoDB replica set to run these')
class ExactlyOnceTest(MongoTestCase):
    def test_an_event_is_counted_once_it_is_folded(self):
        self.assertEqual(self.record(), 'recorded')
        self.assertIsNone(self.report())
        self.assertEqual(self.fold(), 1)
        self.assertEqual(self.report(), {'_id': 'AD1', 'click': 1, 'render': 0})
        self.assertEqual(self.fold(), 0)

    def test_a_replayed_url_is_counted_once(self):
        results = [self.record() for _ in range(5)]
        self.assertEqual(results, ['recorded'] + ['duplicate'] * 4)
        self.fold_all()
        self.assertEqual(self.report()['click'], 1)

    def test_a_message_delivered_again_after_it_was_recorded_is_counted_once(self):
        # The worker records the event, then dies before it can ack, so Pub/Sub sends it again.
        self.assertEqual(self.record(), 'recorded')
        self.assertEqual(self.record(), 'duplicate')
        self.fold_all()
        self.assertEqual(self.report()['click'], 1)

    def test_a_replay_after_the_fold_is_still_a_duplicate(self):
        self.record()
        self.fold_all()
        self.assertEqual(self.record(), 'duplicate')
        self.assertEqual(self.fold_all(), 0)
        self.assertEqual(self.report()['click'], 1)

    def test_a_fold_that_fails_part_way_leaves_nothing_behind(self):
        # The counts are added, then the fold dies before it marks the events. Without the transaction the
        # counts would stay, and the next fold would add them again.
        from pymongo.collection import Collection

        self.record()
        real_update_many = Collection.update_many

        def fail_on_inbox(collection, *args, **kwargs):
            if collection.name == 'inbox':
                raise ConnectionError('the fold died here')
            return real_update_many(collection, *args, **kwargs)

        with patch.object(Collection, 'update_many', autospec=True, side_effect=fail_on_inbox):
            with self.assertRaises(ConnectionError):
                self.fold()

        self.assertIsNone(self.report())
        self.assertEqual(self.fold_all(), 1)
        self.assertEqual(self.report()['click'], 1)

    def test_the_click_and_the_render_of_one_bid_both_count(self):
        self.record('click')
        self.record('render')
        self.fold_all()
        self.assertEqual(self.report(), {'_id': 'AD1', 'click': 1, 'render': 1})

    def test_different_bids_of_the_same_ad_each_count(self):
        for bid_id in ('B1', 'B2', 'B3'):
            self.record(event=engagement(bid_id=bid_id))
        self.fold_all()
        self.assertEqual(self.report()['click'], 3)

    def test_the_same_event_arriving_on_several_threads_at_once_is_recorded_once(self):
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

        self.assertEqual(sorted(results), ['duplicate'] * (threads - 1) + ['recorded'])
        self.fold_all()
        self.assertEqual(self.report()['click'], 1)

    def test_folds_running_at_once_count_every_event_exactly_once(self):
        # Several subscribers fold the same backlog. Their transactions collide on the events, and each event
        # ends up in exactly one of them.
        events = 600
        for n in range(events):
            self.record(event=engagement(bid_id=f'B{n}'))
        folded, lock = [], threading.Lock()
        start = threading.Barrier(4)

        def folder():
            start.wait()
            while True:
                n = self.fold(batch=50)
                with lock:
                    folded.append(n)
                if n == 0:
                    return

        threads = [threading.Thread(target=folder) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(folded), events)
        self.assertEqual(self.report()['click'], events)
        self.assertEqual(self.database.inbox.count_documents({'folded': False}), 0)

    def test_a_fold_takes_at_most_a_batch_oldest_first(self):
        for n in range(5):
            app.record_event(self.database, self.redis, 'click', engagement(bid_id=f'B{n}'), NOW + timedelta(seconds=n))
        self.assertEqual([self.fold(batch=2) for _ in range(4)], [2, 2, 1, 0])
        first = self.database.inbox.find_one({'_id': 'click:B0'})
        self.assertTrue(first['folded'])

    def test_records_from_before_folding_existed_are_never_folded(self):
        # The old subscriber counted as it recorded, and its records have no folded field.
        self.database.inbox.insert_one({'_id': 'click:OLD', 'seen_at': NOW})
        self.assertEqual(self.fold(), 0)
        self.assertIsNone(self.report())

    def test_the_inbox_forgets_after_72_hours_and_folds_find_the_oldest_quickly(self):
        indexes = {tuple(i['key'].items()): i for i in self.database.inbox.list_indexes()}
        self.assertEqual(indexes[(('seen_at', 1),)]['expireAfterSeconds'], 72 * 3600)
        self.assertIn((('folded', 1), ('seen_at', 1)), indexes)

    def test_folding_records_how_long_after_serving_each_event_was_counted(self):
        from prometheus_client import REGISTRY

        before_count = REGISTRY.get_sample_value('subscriber_serve_to_count_seconds_count') or 0
        before_sum = REGISTRY.get_sample_value('subscriber_serve_to_count_seconds_sum') or 0
        for n in range(3):
            self.record(event=engagement(bid_id=f'B{n}', served_at=NOW - timedelta(seconds=10)))
        self.fold_all()
        self.assertEqual(REGISTRY.get_sample_value('subscriber_serve_to_count_seconds_count') - before_count, 3)
        self.assertAlmostEqual(REGISTRY.get_sample_value('subscriber_serve_to_count_seconds_sum') - before_sum, 30)

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
    """Spend is added when events are folded, and copied to Redis after the commit."""

    def cpm_render(self, bid_id='B1', price=1_000_000):
        return self.record('render', engagement(self.ad, bid_id, 'CPM', price, campaign_id=self.campaign))

    def spent(self):
        """The four totals, from MongoDB and from Redis."""
        ids = [f'ad:{self.ad}', f'ad:{self.ad}:2026-11-08', f'campaign:{self.campaign}', f'campaign:{self.campaign}:2026-11-08']
        rows = {row['_id']: row['nanos'] for row in self.database.spend.find({'_id': {'$in': ids}})}
        mongo = [rows.get(i) for i in ids]
        cached = [None if v is None else int(v) for v in self.redis.mget([f'spend:{i}' for i in ids])]
        return mongo, cached

    def test_folded_events_add_their_prices_to_all_four_totals_in_both_places(self):
        self.cpm_render(price=1_000_000)
        self.cpm_render(bid_id='B2', price=500)
        self.fold_all()
        mongo, cached = self.spent()
        self.assertEqual(mongo, [1_000_500] * 4)
        self.assertEqual(cached, [1_000_500] * 4)

    def test_nothing_is_spent_until_the_fold(self):
        self.cpm_render()
        self.assertEqual(self.spent(), ([None] * 4, [None] * 4))

    def test_an_event_its_bid_type_does_not_pay_for_costs_nothing(self):
        self.record('click', engagement(self.ad, 'B1', 'CPM', 1_000_000, campaign_id=self.campaign))
        self.fold_all()
        self.assertEqual(self.spent(), ([None] * 4, [None] * 4))

    def test_a_replay_is_not_charged_twice(self):
        for _ in range(4):
            self.cpm_render()
        self.fold_all()
        self.assertEqual(self.spent(), ([1_000_000] * 4, [1_000_000] * 4))

    def test_if_redis_fails_after_a_fold_the_next_fold_of_that_ad_repairs_it(self):
        broken = Mock()
        broken.register_script.side_effect = ConnectionError('redis is down')
        self.cpm_render()
        self.redis = broken
        with self.assertRaises(ConnectionError):
            self.fold()
        # The fold committed, so MongoDB is right and the event is not folded again.
        self.redis = self.real_redis
        self.assertEqual(self.spent(), ([1_000_000] * 4, [None] * 4))
        self.assertEqual(self.fold(), 0)

        # The ad still looks like it has budget, so it serves, and its next event's fold copies the true totals.
        self.cpm_render(bid_id='B2')
        self.fold_all()
        self.assertEqual(self.spent(), ([2_000_000] * 4, [2_000_000] * 4))

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
        self.fold_all()
        daily = self.redis.ttl(f'spend:ad:{self.ad}:2026-11-08')
        total = self.redis.ttl(f'spend:ad:{self.ad}')
        self.assertTrue(47 * 3600 < daily <= 48 * 3600, daily)
        self.assertTrue(29 * 86400 < total <= 30 * 86400, total)

    def test_many_events_of_one_ad_at_once_add_up_exactly(self):
        # The case that used to conflict: many events of one ad recorded at the same moment.
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
        self.fold_all()

        want = sum(1_000 + n for n in range(threads))
        self.assertEqual(self.spent(), ([want] * 4, [want] * 4))


@unittest.skipUnless(
    os.getenv('MONGODB_TEST_URI') and os.getenv('REDIS_TEST_URL'),
    'set MONGODB_TEST_URI and REDIS_TEST_URL to run these',
)
class CounterTest(RedisTestCase):
    """A capped ad's events go into its user's sorted sets as they are recorded, for the ad server's caps."""

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
