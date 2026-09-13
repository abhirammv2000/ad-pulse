from datetime import datetime

from app.enums.States import States
from app.models.ad import Ad
from app.services import crud
from config.db import session_scope

UPDATABLE_FIELDS = (
    'adname', 'campaignid', 'advertiserid', 'creativeid', 'startdate', 'enddate',
    'landingurl', 'budget', 'frequencycaps', 'bidinfo', 'adtype', 'adpriority',
    'targetinginfo', 'updatedby', 'ad_unit_targeted',
)


def generate_adid():
    return crud.generate_id("AD")


def create_ad(json_data):
    now = datetime.now()
    with session_scope() as session:
        ad = Ad(
            adid=generate_adid(),
            adname=json_data.get('adname'),
            campaignid=json_data.get('campaignid'),
            advertiserid=json_data.get('advertiserid'),
            creativeid=json_data.get('creativeid'),
            startdate=json_data.get('startdate'),
            enddate=json_data.get('enddate'),
            landingurl=json_data.get('landingurl'),
            budget=json_data.get('budget'),
            frequencycaps=json_data.get('frequencycaps'),
            bidinfo=json_data.get('bidinfo'),
            adtype=json_data.get('adtype'),
            adpriority=json_data.get('adpriority'),
            targetinginfo=json_data.get('targetinginfo'),
            createdat=now,
            updatedat=now,
            createdby=json_data.get('createdby'),
            updatedby=json_data.get('updatedby'),
            adstate=States.CREATED.value,
            ad_unit_targeted=json_data.get('ad_unit_targeted'),
        )
        session.add(ad)
        return ad.to_dict()


def update_ad(json_data):
    with session_scope() as session:
        ad = session.query(Ad).filter_by(adid=json_data.get('adid')).first()
        if ad is None:
            return None
        crud.apply_updates(ad, json_data, UPDATABLE_FIELDS)
        return ad.to_dict()


def get_ad_by_id(ad_id):
    return crud.get_by_id(Ad, Ad.adid, ad_id)


def get_all_ads():
    return crud.get_all(Ad)


def update_ad_state(ad_id, new_state):
    return crud.update_state(Ad, Ad.adid, ad_id, 'adstate', new_state)


def get_ad_by_state(state):
    return crud.get_where(Ad, adstate=state)


def get_ad_by_campaign_and_advertiser_id(advertiser_id, campaign_id):
    return crud.get_where(Ad, campaignid=campaign_id, advertiserid=advertiser_id)
