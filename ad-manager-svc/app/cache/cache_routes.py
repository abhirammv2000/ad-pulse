"""Cache refresh endpoints.

Each GET rebuilds one slice of the Redis cache and returns what it wrote, so
the caller can confirm the refresh landed. ad-refresh-cache-svc polls these on
a timer; they are also useful by hand when debugging a stale cache.
"""

import json

from flask import Blueprint, jsonify

from app.cache.cache_job import (
    AD_KEYS_INDEX,
    CAMPAIGNS_KEY,
    CREATIVE_KEYS_INDEX,
    fetch_and_cache_active_ads,
    fetch_and_cache_active_campaigns,
    fetch_and_cache_active_creatives,
)
from config.redis import get_redis_client

cache_blueprint = Blueprint('cache', __name__)


@cache_blueprint.route('/cache/campaigns', methods=['GET'])
def get_cached_campaigns():
    fetch_and_cache_active_campaigns()
    cached = get_redis_client().get(CAMPAIGNS_KEY)
    return jsonify(json.loads(cached) if cached else []), 200


@cache_blueprint.route('/cache/ads', methods=['GET'])
def get_cached_ads():
    fetch_and_cache_active_ads()
    redis_client = get_redis_client()
    return jsonify({
        campaign_id: {
            ad_id: json.loads(ad_json)
            for ad_id, ad_json in redis_client.hgetall(campaign_id).items()
        }
        for campaign_id in redis_client.smembers(AD_KEYS_INDEX)
    }), 200


@cache_blueprint.route('/cache/creatives', methods=['GET'])
def get_cached_creatives():
    fetch_and_cache_active_creatives()
    redis_client = get_redis_client()
    # A list, not the set smembers returns: mget's result is positional, so the
    # ids have to keep a stable order to zip back against.
    creative_ids = sorted(redis_client.smembers(CREATIVE_KEYS_INDEX))
    values = redis_client.mget(creative_ids) if creative_ids else []
    return jsonify({
        creative_id: json.loads(value)
        for creative_id, value in zip(creative_ids, values)
        if value
    }), 200
