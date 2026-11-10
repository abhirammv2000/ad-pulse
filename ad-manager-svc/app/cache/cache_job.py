"""Projects the live campaign/ad/creative rows into Redis for the ad server.

Key layout (read by ad-server-svc):
  campaigns        -> JSON list of every ACTIVE campaign
  <campaignid>     -> hash of adid -> ad JSON, for every ACTIVE ad
  <creativeid>     -> creative JSON, for every ACTIVE creative

Each refresh has to clear the previous generation of keys. Deleting by glob is
not safe here: campaign ids look like `C2024...` and creative ids like
`CR2024...`, so a `C*` sweep for ads also wiped every creative. Instead each
refresh records the exact keys it wrote in an index set and clears those.
"""

import json
import logging

from pymongo.errors import PyMongoError

from app.models.ad import Ad
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.services.reporting_service import engagement_counts
from config.db import session_scope
from config.redis import get_redis_client

log = logging.getLogger(__name__)

CAMPAIGNS_KEY = "campaigns"
AD_KEYS_INDEX = "index:ad_campaign_keys"
CREATIVE_KEYS_INDEX = "index:creative_keys"


def _replace_keys(redis_client, index_key, new_keys, write):
    """Swap one generation of cache keys for the next.

    Deletes the keys the previous refresh wrote but this one did not, applies
    `write` for the new data, and leaves `index_key` holding the new key set.
    """
    stale = redis_client.smembers(index_key) - set(new_keys)

    pipe = redis_client.pipeline()
    if stale:
        pipe.delete(*stale)
    write(pipe)
    pipe.delete(index_key)
    if new_keys:
        pipe.sadd(index_key, *new_keys)
    pipe.execute()


def fetch_and_cache_active_campaigns():
    with session_scope() as session:
        campaigns = session.query(Campaign).filter(Campaign.campaignstate == 'ACTIVE').all()
        payload = json.dumps([campaign.to_dict() for campaign in campaigns])

    get_redis_client().set(CAMPAIGNS_KEY, payload)


def add_engagement_stats(rows):
    """Give each CPC ad its clicks and renders so far, for the ad server's ranking.

    A CPC ad competes on its expected click-through rate, so it needs its counts. They
    change all the time, but the cache is rebuilt every few seconds, which is fresh
    enough for a rate. If MongoDB can't be reached the ads are cached without them,
    and the ad server ranks those ads on its prior rate until the next refresh.
    """
    cpc_ids = [
        row['adid'] for row in rows
        if isinstance(row.get('bidinfo'), dict) and row['bidinfo'].get('bidType') == 'CPC'
    ]
    try:
        counts = engagement_counts(cpc_ids)
    except (PyMongoError, RuntimeError) as exc:
        log.warning("caching ads without click and render counts: %s", exc)
        return
    for row in rows:
        report = counts.get(row['adid'])
        if report:
            row['stats'] = {'clicks': report.get('click', 0), 'renders': report.get('render', 0)}


def fetch_and_cache_active_ads():
    with session_scope() as session:
        rows = [ad.to_dict() for ad in session.query(Ad).filter(Ad.adstate == 'ACTIVE').all()]
    add_engagement_stats(rows)

    # One hash per campaign, keyed by ad id.
    by_campaign = {}
    for row in rows:
        by_campaign.setdefault(row['campaignid'], {})[row['adid']] = json.dumps(row)

    def write(pipe):
        for campaign_id, ads_json in by_campaign.items():
            # Replace the hash wholesale so ads that went inactive disappear.
            pipe.delete(campaign_id)
            pipe.hset(campaign_id, mapping=ads_json)

    _replace_keys(get_redis_client(), AD_KEYS_INDEX, list(by_campaign), write)


def fetch_and_cache_active_creatives():
    with session_scope() as session:
        creatives = session.query(Creative).filter(Creative.creativestate == 'ACTIVE').all()
        payload = {creative.creativeid: json.dumps(creative.to_dict()) for creative in creatives}

    def write(pipe):
        for key, value in payload.items():
            pipe.set(key, value)

    _replace_keys(get_redis_client(), CREATIVE_KEYS_INDEX, list(payload), write)
