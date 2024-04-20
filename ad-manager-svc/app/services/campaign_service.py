from app.models.campaign import Campaign
from config.db import create_session
import time
from datetime import datetime
from app.enums.States import States


def generate_campaignid():
    current_time = time.localtime()
    formatted_time = time.strftime("%Y%m%d%H%M%S", current_time)
    milliseconds = int(time.time() * 1000) % 1000
    formatted_time += '{:03d}'.format(milliseconds)
    return "C" + formatted_time

def get_all_campaigns():
    session = create_session()
    campaigns = session.query(Campaign).all()
    campaign_list = []
    for campaign in campaigns:
        campaign_data = {
            'campaignid': campaign.campaignid,
            'campaignname': campaign.campaignname,
            'advertiserid': campaign.advertiserid,
            'startdate': campaign.startdate.isoformat(),
            'enddate': campaign.enddate.isoformat(),
            'budget': campaign.budget,
            'frequencycaps': campaign.frequencycaps,
            'createdby': campaign.createdby,
            'updatedby': campaign.updatedby,
            'createdat': campaign.createdat.isoformat(),
            'updatedat': campaign.updatedat.isoformat(),
            'campaignstate': campaign.campaignstate
        }
        campaign_list.append(campaign_data)
    session.close()
    return campaign_list

def get_campaign_by_id(campaignid):
    session = create_session()
    campaign = session.query(Campaign).filter(Campaign.campaignid == campaignid).first()
    if campaign is None:
        return None
    campaign_data = {
        'campaignid': campaign.campaignid,
        'campaignname': campaign.campaignname,
        'advertiserid': campaign.advertiserid,
        'startdate': campaign.startdate.isoformat(),
        'enddate': campaign.enddate.isoformat(),
        'budget': campaign.budget,
        'frequencycaps': campaign.frequencycaps,
        'createdby': campaign.createdby,
        'updatedby': campaign.updatedby,
        'createdat': campaign.createdat.isoformat(),
        'updatedat': campaign.updatedat.isoformat(),
        'campaignstate': campaign.campaignstate
    }
    session.close()
    return campaign_data

def get_campaign_by_state(state):
    session = create_session()
    campaigns = session.query(Campaign).filter(Campaign.campaignstate == state).all()
    campaign_list = []
    for campaign in campaigns:
        campaign_data = {
            'campaignid': campaign.campaignid,
            'campaignname': campaign.campaignname,
            'advertiserid': campaign.advertiserid,
            'startdate': campaign.startdate.isoformat(),
            'enddate': campaign.enddate.isoformat(),
            'budget': campaign.budget,
            'frequencycaps': campaign.frequencycaps,
            'createdby': campaign.createdby,
            'updatedby': campaign.updatedby,
            'createdat': campaign.createdat.isoformat(),
            'updatedat': campaign.updatedat.isoformat(),
            'campaignstate': campaign.campaignstate
        }
        campaign_list.append(campaign_data)
    session.close()
    return campaign_list

def create_campaign(json_data):
    session = create_session()
    current_time = datetime.now()

    new_campaign = Campaign(
        campaignid=generate_campaignid(),
        campaignname=json_data.get('campaignname'),
        advertiserid=json_data.get('advertiserid'),
        startdate=json_data.get('startdate'),
        enddate=json_data.get('enddate'),
        budget=json_data.get('budget'),
        frequencycaps=json_data.get('frequencycaps'),
        createdby=json_data.get('createdby'),
        updatedby=json_data.get('updatedby'),
        createdat=current_time,
        updatedat=current_time,
        campaignstate=States.CREATED.value
    )
    session.add(new_campaign)
    session.commit()

    # Return the created campaign data
    created_campaign = {
        'campaignid': new_campaign.campaignid,
        'campaignname': new_campaign.campaignname,
        'advertiserid': new_campaign.advertiserid,
        'startdate': new_campaign.startdate.isoformat(),
        'enddate': new_campaign.enddate.isoformat(),
        'budget': new_campaign.budget,
        'frequencycaps': new_campaign.frequencycaps,
        'createdby': new_campaign.createdby,
        'updatedby': new_campaign.updatedby,
        'createdat': new_campaign.createdat.isoformat(),
        'updatedat': new_campaign.updatedat.isoformat(),
        'campaignstate': new_campaign.campaignstate
    }

    session.close()
    return created_campaign

def update_campaign(json_data):
    session = create_session()
    campaign_id = json_data.get('campaignid')
    campaign = session.query(Campaign).filter_by(campaignid=campaign_id).first()
    current_time = datetime.now()

    if campaign:
        campaign.campaignname = json_data.get('campaignname', campaign.campaignname)
        campaign.advertiserid = json_data.get('advertiserid', campaign.advertiserid)
        campaign.startdate = json_data.get('startdate', campaign.startdate)
        campaign.enddate = json_data.get('enddate', campaign.enddate)
        campaign.budget = json_data.get('budget', campaign.budget)
        campaign.frequencycaps = json_data.get('frequencycaps', campaign.frequencycaps)
        campaign.updatedby = json_data.get('updatedby', campaign.updatedby)
        campaign.updatedat = current_time

        session.commit()

        updated_campaign = {
            'campaignid': campaign.campaignid,
            'campaignname': campaign.campaignname,
            'advertiserid': campaign.advertiserid,
            'startdate': campaign.startdate.isoformat(),
            'enddate': campaign.enddate.isoformat(),
            'budget': campaign.budget,
            'frequencycaps': campaign.frequencycaps,
            'createdby': campaign.createdby,
            'updatedby': campaign.updatedby,
            'createdat': campaign.createdat.isoformat(),
            'updatedat': campaign.updatedat.isoformat(),
            'campaignstate': campaign.campaignstate
        }
        session.close()
        return updated_campaign
    else:
        session.close()
        return None

def update_campaign_state(campaign_id, state):
    session = create_session()
    campaign = session.query(Campaign).filter_by(campaignid=campaign_id).first()
    if campaign:
        campaign.campaignstate = state
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False
    
def get_campaign_by_advertiser_id(advertiser_id):
    session = create_session()
    campaigns = session.query(Campaign).filter(Campaign.advertiserid == advertiser_id).all()
    campaign_list = []
    for campaign in campaigns:
        campaign_data = {
            'campaignid': campaign.campaignid,
            'campaignname': campaign.campaignname,
            'advertiserid': campaign.advertiserid,
            'startdate': campaign.startdate.isoformat(),
            'enddate': campaign.enddate.isoformat(),
            'budget': campaign.budget,
            'frequencycaps': campaign.frequencycaps,
            'createdby': campaign.createdby,
            'updatedby': campaign.updatedby,
            'createdat': campaign.createdat.isoformat(),
            'updatedat': campaign.updatedat.isoformat(),
            'campaignstate': campaign.campaignstate
        }
        campaign_list.append(campaign_data)
    session.close()
    return campaign_list