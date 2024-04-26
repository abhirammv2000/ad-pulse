from config.db import create_session
from app.models.ad import Ad
from datetime import datetime
import time
from app.enums.States import States


def generate_adid():
    current_time = time.localtime()
    formatted_time = time.strftime("%Y%m%d%H%M%S", current_time)
    milliseconds = int(time.time() * 1000) % 1000
    formatted_time += '{:03d}'.format(milliseconds)
    return "AD" + formatted_time


def create_ad(json_data):
    session = create_session()
    current_time = datetime.now()

    new_ad = Ad(
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
        createdat=current_time,
        updatedat=current_time,
        createdby=json_data.get('createdby'),
        updatedby=json_data.get('updatedby'),
        adstate=States.CREATED.value,
        ad_unit_targeted=json_data.get('ad_unit_targeted')
    )
    session.add(new_ad)
    session.commit()

    # Return the created ad data
    created_ad = {
        'adid': new_ad.adid,
        'adname': new_ad.adname,
        'campaignid': new_ad.campaignid,
        'advertiserid': new_ad.advertiserid,
        'creativeid': new_ad.creativeid,
        'startdate': new_ad.startdate.isoformat(),
        'enddate': new_ad.enddate.isoformat(),
        'landingurl': new_ad.landingurl,
        'budget': new_ad.budget,
        'frequencycaps': new_ad.frequencycaps,
        'bidinfo': new_ad.bidinfo,
        'adtype': new_ad.adtype,
        'adpriority': new_ad.adpriority,
        'targetinginfo': new_ad.targetinginfo,
        'createdby': new_ad.createdby,
        'updatedby': new_ad.updatedby,
        'createdat': new_ad.createdat.isoformat(),
        'updatedat': new_ad.updatedat.isoformat(),
        'adstate': new_ad.adstate,
        'ad_unit_targeted': new_ad.ad_unit_targeted
    }

    session.close()
    return created_ad


def get_all_ads():
    session = create_session()
    ads = session.query(Ad).all()
    ads_data = []
    for ad in ads:
        ad_data = {
            'adid': ad.adid,
            'adname': ad.adname,
            'campaignid': ad.campaignid,
            'advertiserid': ad.advertiserid,
            'creativeid': ad.creativeid,
            'startdate': ad.startdate.isoformat(),
            'enddate': ad.enddate.isoformat(),
            'landingurl': ad.landingurl,
            'budget': ad.budget,
            'frequencycaps': ad.frequencycaps,
            'bidinfo': ad.bidinfo,
            'adtype': ad.adtype,
            'adpriority': ad.adpriority,
            'targetinginfo': ad.targetinginfo,
            'createdby': ad.createdby,
            'updatedby': ad.updatedby,
            'createdat': ad.createdat,
            'updatedat': ad.updatedat,
            'adstate': ad.adstate,
            'ad_unit_targeted': ad.ad_unit_targeted
        }
        ads_data.append(ad_data)
    session.close()
    return ads_data

def get_ad_by_id(ad_id):
    session = create_session()
    ad = session.query(Ad).filter_by(adid=ad_id).first()
    if ad:
        ad_data = {
            'adid': ad.adid,
            'adname': ad.adname,
            'campaignid': ad.campaignid,
            'advertiserid': ad.advertiserid,
            'creativeid': ad.creativeid,
            'startdate': ad.startdate.isoformat(),
            'enddate': ad.enddate.isoformat(),
            'landingurl': ad.landingurl,
            'budget': ad.budget,
            'frequencycaps': ad.frequencycaps,
            'bidinfo': ad.bidinfo,
            'adtype': ad.adtype,
            'adpriority': ad.adpriority,
            'targetinginfo': ad.targetinginfo,
            'createdby': ad.createdby,
            'updatedby': ad.updatedby,
            'createdat': ad.createdat,
            'updatedat': ad.updatedat,
            'adstate': ad.adstate,
            'ad_unit_targeted': ad.ad_unit_targeted
        }
        session.close()
        return ad_data
    else:
        session.close()
        return None

def get_ad_by_state(state):
    session = create_session()
    ads = session.query(Ad).filter_by(adstate=state).all()
    ads_data = []
    for ad in ads:
        ad_data = {
            'adid': ad.adid,
            'adname': ad.adname,
            'campaignid': ad.campaignid,
            'advertiserid': ad.advertiserid,
            'creativeid': ad.creativeid,
            'startdate': ad.startdate.isoformat(),
            'enddate': ad.enddate.isoformat(),
            'landingurl': ad.landingurl,
            'budget': ad.budget,
            'frequencycaps': ad.frequencycaps,
            'bidinfo': ad.bidinfo,
            'adtype': ad.adtype,
            'adpriority': ad.adpriority,
            'targetinginfo': ad.targetinginfo,
            'createdby': ad.createdby,
            'updatedby': ad.updatedby,
            'createdat': ad.createdat,
            'updatedat': ad.updatedat,
            'adstate': ad.adstate,
            'ad_unit_targeted': ad.ad_unit_targeted
        }
        ads_data.append(ad_data)
    session.close()
    return ads_data

def update_ad_state(ad_id, new_state):
    session = create_session()
    ad = session.query(Ad).filter_by(adid=ad_id).first()
    if ad:
        ad.adstate = new_state
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False

def update_ad(json_data):
    session = create_session()
    ad = session.query(Ad).filter_by(adid=json_data.get('adid')).first()
    if ad:
        ad.adname = json_data.get('adname')
        ad.campaignid = json_data.get('campaignid')
        ad.advertiserid = json_data.get('advertiserid')
        ad.creativeid = json_data.get('creativeid')
        ad.startdate = json_data.get('startdate')
        ad.enddate = json_data.get('enddate')
        ad.landingurl = json_data.get('landingurl')
        ad.budget = json_data.get('budget')
        ad.frequencycaps = json_data.get('frequencycaps')
        ad.bidinfo = json_data.get('bidinfo')
        ad.adtype = json_data.get('adtype')
        ad.adpriority = json_data.get('adpriority')
        ad.targetinginfo = json_data.get('targetinginfo')
        ad.updatedat = datetime.now()
        ad.updatedby = json_data.get('updatedby')
        ad.ad_unit_targeted = json_data.get('ad_unit_targeted')
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False
    
def get_ad_by_campaign_and_advertiser_id(advertiser_id, campaign_id):
    session = create_session()
    print(campaign_id, advertiser_id)
    ads = session.query(Ad).filter_by(campaignid=campaign_id, advertiserid=advertiser_id).all()
    print(ads)
    ads_data = []
    for ad in ads:
        ad_data = {
            'adid': ad.adid,
            'adname': ad.adname,
            'campaignid': ad.campaignid,
            'advertiserid': ad.advertiserid,
            'creativeid': ad.creativeid,
            'startdate': ad.startdate.isoformat(),
            'enddate': ad.enddate.isoformat(),
            'landingurl': ad.landingurl,
            'budget': ad.budget,
            'frequencycaps': ad.frequencycaps,
            'bidinfo': ad.bidinfo,
            'adtype': ad.adtype,
            'adpriority': ad.adpriority,
            'targetinginfo': ad.targetinginfo,
            'createdby': ad.createdby,
            'updatedby': ad.updatedby,
            'createdat': ad.createdat,
            'updatedat': ad.updatedat,
            'adstate': ad.adstate,
            'ad_unit_targeted': ad.ad_unit_targeted
        }
        ads_data.append(ad_data)
    session.close()
    return ads_data