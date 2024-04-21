import json
from flask import current_app
from config.redis import get_redis_client
from app.models.campaign import Campaign
from app.models.ad import Ad
from app.models.creative import Creative
from config.db import create_session

redis_client = get_redis_client()

def fetch_and_cache_active_campaigns():

    with current_app.app_context():

        session = create_session()

        redis_client.delete('campaigns')
        
        active_campaigns = session.query(Campaign).filter(Campaign.campaignstate == 'ACTIVE').all()

        session.close()

        cache_active_campaigns(active_campaigns)

def cache_active_campaigns(active_campaigns):
    key = "campaigns"
    campaigns_list = []
    for campaign in active_campaigns:
        campaign_json = {key: getattr(campaign, key) for key in campaign.__dict__.keys() if key != '_sa_instance_state'}        
        campaign_json['startdate'] = campaign_json['startdate'].isoformat() if campaign_json['startdate'] else None
        campaign_json['enddate'] = campaign_json['enddate'].isoformat() if campaign_json['enddate'] else None
        campaign_json['createdat'] = campaign_json['createdat'].isoformat() if campaign_json['createdat'] else None
        campaign_json['updatedat'] = campaign_json['updatedat'].isoformat() if campaign_json['updatedat'] else None
        campaigns_list.append(campaign_json)
    value = json.dumps(campaigns_list)
    redis_client.set(key, value)

def fetch_and_cache_active_ads():

    with current_app.app_context():

        session = create_session()

        keys_to_delete = redis_client.keys('C*')

        for key in keys_to_delete:
            redis_client.delete(key)
        
        active_ads = session.query(Ad).filter(Ad.adstate == 'ACTIVE').all()

        session.close()

        cache_active_ads(active_ads)

def cache_active_ads(active_ads):
    for ad in active_ads:
        key = ad.campaignid
        ad_json = {key: getattr(ad, key) for key in ad.__dict__.keys() if key != '_sa_instance_state'}
        ad_json['startdate'] = ad_json['startdate'].isoformat() if ad_json['startdate'] else None
        ad_json['enddate'] = ad_json['enddate'].isoformat() if ad_json['enddate'] else None
        ad_json['createdat'] = ad_json['createdat'].isoformat() if ad_json['createdat'] else None
        ad_json['updatedat'] = ad_json['updatedat'].isoformat() if ad_json['updatedat'] else None
        value = json.dumps(ad_json)
        redis_client.hset(key, ad.adid, value)

def fetch_and_cache_active_creatives():

    with current_app.app_context():

        session = create_session()

        keys_to_delete = redis_client.keys('CR*')

        for key in keys_to_delete:
            redis_client.delete(key)
        
        active_creatives = session.query(Creative).filter(Creative.creativestate == 'ACTIVE').all()

        session.close()

        cache_active_creatives(active_creatives)

def cache_active_creatives(active_creatives):
    for creative in active_creatives:
        key = creative.creativeid
        creative_json = {key: getattr(creative, key) for key in creative.__dict__.keys() if key != '_sa_instance_state'}
        creative_json['createdat'] = creative_json['createdat'].isoformat() if creative_json['createdat'] else None
        creative_json['updatedat'] = creative_json['updatedat'].isoformat() if creative_json['updatedat'] else None
        value = json.dumps(creative_json)
        redis_client.set(key, value)