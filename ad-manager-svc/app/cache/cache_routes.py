from time import sleep
from flask import jsonify, Blueprint
from config.redis import get_redis_client
import json
from app.cache.cache_job import fetch_and_cache_active_campaigns, fetch_and_cache_active_ads, fetch_and_cache_active_creatives

cache_blueprint = Blueprint('cache', __name__)

redis_client = get_redis_client()

@cache_blueprint.route('/cache/campaigns', methods=['GET'])
def get_cache():
    fetch_and_cache_active_campaigns()
    # sleep(5)
    all_keys = redis_client.keys('campaigns')
    cache_data = []
    for key in all_keys:
        value = redis_client.get(key)
        cache_data.append(json.loads(value))
    return jsonify(cache_data)

@cache_blueprint.route('/cache/ads', methods=['GET'])
def get_cached_ads():

    fetch_and_cache_active_ads()
    ads_by_campaign = {}

    # Iterate over each key in the Redis database
    for key in redis_client.scan_iter("C*"):
        campaign_id = key

        # Get all ad IDs and their corresponding data for the campaign
        ad_data = redis_client.hgetall(key)
        
        # Convert ad data from bytes to string and then to dictionary
        ad_data_dict = {ad_id: json.loads(ad_data[ad_id]) for ad_id in ad_data}

        # Add the ad data to the ads_by_campaign dictionary
        ads_by_campaign[campaign_id] = ad_data_dict

    return jsonify(ads_by_campaign)

@cache_blueprint.route('/cache/creatives', methods=['GET'])
def get_cached_creatives():
    fetch_and_cache_active_creatives()

    creative_keys = redis_client.keys('CR*')
    creatives = {}
    for key in creative_keys:
        creative_json = redis_client.get(key)
        creatives[key] = json.loads(creative_json)
    return jsonify(creatives)


    