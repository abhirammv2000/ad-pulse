"""Regression test for the cache key collision: refreshing ads used to delete
every cached creative because both were swept with the same `C*` glob.
"""

import unittest


class FakeRedis:
    """Just enough of the redis-py surface for _replace_keys to run against."""

    def __init__(self):
        self.hashes = {}
        self.strings = {}
        self.sets = {}

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def delete(self, *keys):
        # Real DEL removes a key regardless of its type, so the fake has to
        # check all three maps too.
        for key in keys:
            self.hashes.pop(key, None)
            self.strings.pop(key, None)
            self.sets.pop(key, None)

    def hset(self, key, mapping):
        self.hashes[key] = dict(mapping)

    def set(self, key, value):
        self.strings[key] = value

    def sadd(self, key, *values):
        self.sets.setdefault(key, set()).update(values)

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    def delete(self, *keys):
        self.ops.append(('delete', keys))
        return self

    def hset(self, key, mapping):
        self.ops.append(('hset', key, mapping))
        return self

    def set(self, key, value):
        self.ops.append(('set', key, value))
        return self

    def sadd(self, key, *values):
        self.ops.append(('sadd', key, values))
        return self

    def execute(self):
        for op in self.ops:
            if op[0] == 'delete':
                self.redis.delete(*op[1])
            elif op[0] == 'hset':
                self.redis.hset(op[1], op[2])
            elif op[0] == 'set':
                self.redis.set(op[1], op[2])
            elif op[0] == 'sadd':
                self.redis.sadd(op[1], *op[2])
        self.ops = []


class CacheKeyCollisionTest(unittest.TestCase):

    def test_refreshing_ads_does_not_touch_creative_keys(self):
        from app.cache.cache_job import _replace_keys

        redis = FakeRedis()
        # A creative cached under an id that also matches the old ads glob "C*".
        redis.strings['CR20240101000000000'] = '{"creativeid": "CR20240101000000000"}'
        redis.sets['index:creative_keys'] = {'CR20240101000000000'}

        # One campaign hash from the previous ad refresh.
        redis.hashes['C20240101000000000'] = {'AD1': '{}'}
        redis.sets['index:ad_campaign_keys'] = {'C20240101000000000'}

        def write(pipe):
            pipe.delete('C20240101000000000')
            pipe.hset('C20240101000000000', {'AD2': '{}'})

        _replace_keys(redis, 'index:ad_campaign_keys', ['C20240101000000000'], write)

        self.assertIn('CR20240101000000000', redis.strings)
        self.assertEqual(redis.hashes['C20240101000000000'], {'AD2': '{}'})

    def test_stale_campaign_key_is_dropped_when_campaign_goes_inactive(self):
        from app.cache.cache_job import _replace_keys

        redis = FakeRedis()
        redis.hashes['C_OLD'] = {'AD1': '{}'}
        redis.sets['index:ad_campaign_keys'] = {'C_OLD'}

        _replace_keys(redis, 'index:ad_campaign_keys', [], lambda pipe: None)

        self.assertNotIn('C_OLD', redis.hashes)
        self.assertEqual(redis.smembers('index:ad_campaign_keys'), set())


class EngagementStatsTest(unittest.TestCase):
    """CPC ads are cached with their clicks and renders, for the ad server's ranking."""

    def rows(self):
        return [
            {'adid': 'CPC1', 'bidinfo': {'bid': 1, 'bidType': 'CPC'}},
            {'adid': 'CPC_NEW', 'bidinfo': {'bid': 1, 'bidType': 'CPC'}},
            {'adid': 'CPM1', 'bidinfo': {'bid': 1, 'bidType': 'CPM'}},
            {'adid': 'NO_BID', 'bidinfo': None},
        ]

    def test_only_cpc_ads_are_looked_up_and_given_their_counts(self):
        from unittest.mock import patch

        from app.cache import cache_job

        rows = self.rows()
        reports = {'CPC1': {'_id': 'CPC1', 'click': 3, 'render': 200}}
        with patch.object(cache_job, 'engagement_counts', return_value=reports) as counts:
            cache_job.add_engagement_stats(rows)

        counts.assert_called_once_with(['CPC1', 'CPC_NEW'])
        self.assertEqual(rows[0]['stats'], {'clicks': 3, 'renders': 200})
        # An ad with no report yet gets no stats, and the ad server uses its prior rate.
        self.assertNotIn('stats', rows[1])
        self.assertNotIn('stats', rows[2])
        self.assertNotIn('stats', rows[3])

    def test_without_mongodb_the_ads_are_cached_without_counts(self):
        from unittest.mock import patch

        from pymongo.errors import ServerSelectionTimeoutError

        from app.cache import cache_job

        rows = self.rows()
        with patch.object(cache_job, 'engagement_counts', side_effect=ServerSelectionTimeoutError('down')):
            cache_job.add_engagement_stats(rows)

        self.assertFalse(any('stats' in row for row in rows))


if __name__ == '__main__':
    unittest.main()
