"""Regression test for the cache key collision: refreshing ads used to delete
every cached creative because both were swept with the same `C*` glob.
"""

import unittest
from unittest.mock import MagicMock, patch


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


if __name__ == '__main__':
    unittest.main()
