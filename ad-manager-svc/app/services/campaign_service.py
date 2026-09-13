from datetime import datetime

from app.enums.States import States
from app.models.campaign import Campaign
from app.services import crud
from config.db import session_scope

UPDATABLE_FIELDS = ('campaignname', 'advertiserid', 'startdate', 'enddate', 'budget', 'frequencycaps', 'updatedby')


def generate_campaignid():
    return crud.generate_id("C")


def create_campaign(json_data):
    now = datetime.now()
    with session_scope() as session:
        campaign = Campaign(
            campaignid=generate_campaignid(),
            campaignname=json_data.get('campaignname'),
            advertiserid=json_data.get('advertiserid'),
            startdate=json_data.get('startdate'),
            enddate=json_data.get('enddate'),
            budget=json_data.get('budget'),
            frequencycaps=json_data.get('frequencycaps'),
            createdby=json_data.get('createdby'),
            updatedby=json_data.get('updatedby'),
            createdat=now,
            updatedat=now,
            campaignstate=States.CREATED.value,
        )
        session.add(campaign)
        return campaign.to_dict()


def update_campaign(json_data):
    with session_scope() as session:
        campaign = session.query(Campaign).filter_by(campaignid=json_data.get('campaignid')).first()
        if campaign is None:
            return None
        crud.apply_updates(campaign, json_data, UPDATABLE_FIELDS)
        return campaign.to_dict()


def get_campaign_by_id(campaign_id):
    return crud.get_by_id(Campaign, Campaign.campaignid, campaign_id)


def get_all_campaigns():
    return crud.get_all(Campaign)


def update_campaign_state(campaign_id, new_state):
    return crud.update_state(Campaign, Campaign.campaignid, campaign_id, 'campaignstate', new_state)


def get_campaign_by_state(campaign_state):
    return crud.get_where(Campaign, campaignstate=campaign_state)


def get_campaign_by_advertiser_id(advertiser_id):
    return crud.get_where(Campaign, advertiserid=advertiser_id)
