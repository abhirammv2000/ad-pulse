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
    return "A" + formatted_time

def create_ad(json_data):
    session = create_session()
    current_time = datetime.now()

    new_ad = Ad(
        adid=generate_adid(),
        adname=json_data.get('adname'),
        adstate=States.CREATED,
        adtype=json_data.get('adtype'),
        adformat=json_data.get('adformat'),
        adsize=json_data.get('adsize'),
        adcontent=json_data.get('adcontent'),
        createdby=json_data.get('createdby'),
        updatedby=json_data.get('updatedby'),
        createdat=current_time,
        updatedat=current_time,
        preference=json_data.get('preference')
    )
    session.add(new_ad)
    session.commit()

    # Return the created ad data
    created_ad = {
        'adid': new_ad.adid,
        'adname': new_ad.adname,
        'adstate': new_ad.adstate,
        'adtype': new_ad.adtype,
        'adformat': new_ad.adformat,
        'adsize': new_ad.adsize,
        'adcontent': new_ad.adcontent,
        'createdby': new_ad.createdby,
        'updatedby': new_ad.updatedby,
        'createdat': new_ad.createdat.isoformat(),
        'updatedat': new_ad.updatedat.isoformat(),
        'preference': new_ad.preference
    }

    session.close()
    return created_ad

def update_ad(json_data):
    session = create_session()
    ad_id = json_data.get('adid')
    ad = session.query(Ad).filter_by(adid=ad_id).first()

    if ad:
        # Update allowed fields
        ad.adname = json_data.get('adname', ad.adname)
        ad.adtype = json_data.get('adtype', ad.adtype)
        ad.adformat = json_data.get('adformat', ad.adformat)
        ad.adsize = json_data.get('adsize', ad.adsize)
        ad.adcontent = json_data.get('adcontent', ad.adcontent)
        ad.updatedby = json_data.get('updatedby', ad.updatedby)
        ad.updatedat = datetime.now()
        ad.preference = json_data.get('preference', ad.preference)
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False

def get_ad_by_id(ad_id):
    session = create_session()
    ad = session.query(Ad).filter_by(adid=ad_id).first()
    if ad:
        ad_data = {
            'adid': ad.adid,
            'adname': ad.adname,
            'adstate': ad.adstate,
            'adtype': ad.adtype,
            'adformat': ad.adformat,
            'adsize': ad.adsize,
            'adcontent': ad.adcontent,
            'createdby': ad.createdby,
            'updatedby': ad.updatedby,
            'createdat': ad.createdat.isoformat(),
            'updatedat': ad.updatedat.isoformat(),
            'preference': ad.preference
        }
        session.close()
        return ad_data
    else:
        session.close()
        return None

def get_all_ads():
    session = create_session()
    ads = session.query(Ad).all()
    ads_data = []
    for ad in ads:
        ad_data = {
            'adid': ad.adid,
            'adname': ad.adname,
            'adstate': ad.adstate,
            'adtype': ad.adtype,
            'adformat': ad.adformat,
            'adsize': ad.adsize,
            'adcontent': ad.adcontent,
            'createdby': ad.createdby,
            'updatedby': ad.updatedby,
            'createdat': ad.createdat.isoformat(),
            'updatedat': ad.updatedat.isoformat(),
            'preference': ad.preference
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

# def get_ad_state(ad_id):
#     session = create_session()
#     ad = session.query(Ad).filter_by(adid=ad_id).first()
#     if ad:
#         ad_state = ad.adstate
#         session.close()
#         return ad_state
#     else:
#         session.close()
#         return None

def get_ad_by_state(ad_state):
    session = create_session()
    ads = session.query(Ad).filter_by(adstate=ad_state).all()
    ads_data = []
    for ad in ads:
        ad_data = {
            'adid': ad.adid,
            'adname': ad.adname,
            'adstate': ad.adstate,
            'adtype': ad.adtype,
            'adformat': ad.adformat,
            'adsize': ad.adsize,
            'adcontent': ad.adcontent,
            'createdby': ad.createdby,
            'updatedby': ad.updatedby,
            'createdat': ad.createdat.isoformat(),
            'updatedat': ad.updatedat.isoformat(),
            'preference': ad.preference
        }
        ads_data.append(ad_data)
    session.close()
    return ads_data


