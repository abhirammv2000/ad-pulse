from config.db import create_session
from app.models.ad_unit import AdUnit
import time
from datetime import datetime
from app.enums.States import States
from app.models.publisher import Publisher

def generate_adunitid():
    current_time = time.localtime()
    formatted_time = time.strftime("%Y%m%d%H%M%S", current_time)
    milliseconds = int(time.time() * 1000) % 1000
    formatted_time += '{:03d}'.format(milliseconds)
    return "ADU" + formatted_time

def create_ad_unit(json_data):
    session = create_session()
    current_time = datetime.now()

    new_ad_unit = AdUnit(
        adunitid=generate_adunitid(),
        adunittype=json_data.get('adunittype'),
        adunitname=json_data.get('adunitname'),
        publisherid=json_data.get('publisherid'),
        adunitstate=States.CREATED.value,
        createdby=json_data.get('createdby'),
        updatedby=json_data.get('updatedby'),
        createdat=current_time,
        updatedat=current_time,
        preference=json_data.get('preference')
    )
    session.add(new_ad_unit)
    session.commit()

    created_ad_unit = {
        'adunitid': new_ad_unit.adunitid,
        'adunittype': new_ad_unit.adunittype,
        'adunitname': new_ad_unit.adunitname,
        'publisherid': new_ad_unit.publisherid,
        'adunitstate': new_ad_unit.adunitstate,
        'createdby': new_ad_unit.createdby,
        'updatedby': new_ad_unit.updatedby,
        'createdat': new_ad_unit.createdat.isoformat(),
        'updatedat': new_ad_unit.updatedat.isoformat(),
        'preference': new_ad_unit.preference
    }

    session.close()
    return created_ad_unit

def update_ad_unit(json_data):
    session = create_session()
    ad_unit_id = json_data.get('adunitid')
    ad_unit = session.query(AdUnit).filter_by(adunitid=ad_unit_id).first()
    current_time = datetime.now()
    
    if ad_unit:
        ad_unit.adunittype = json_data.get('adunittype', ad_unit.adunittype)
        ad_unit.adunitname = json_data.get('adunitname', ad_unit.adunitname)
        ad_unit.publisherid = json_data.get('publisherid', ad_unit.publisherid)
        ad_unit.updatedby = json_data.get('updatedby', ad_unit.updatedby)
        ad_unit.updatedat = current_time
        ad_unit.preference = json_data.get('preference', ad_unit.preference)
        
        session.commit()
        
        updated_ad_unit = {
            'adunitid': ad_unit.adunitid,
            'adunittype': ad_unit.adunittype,
            'adunitname': ad_unit.adunitname,
            'publisherid': ad_unit.publisherid,
            'adunitstate': ad_unit.adunitstate,
            'createdby': ad_unit.createdby,
            'updatedby': ad_unit.updatedby,
            'createdat': ad_unit.createdat.isoformat(),
            'updatedat': ad_unit.updatedat.isoformat(),
            'preference': ad_unit.preference
        }
        
        session.close()
        
        return updated_ad_unit
    else:
        session.close()
        return None

def get_ad_unit_by_id(ad_unit_id):
    session = create_session()
    ad_unit = session.query(AdUnit).filter_by(adunitid=ad_unit_id).first()
    
    if ad_unit:
        ad_unit_data = {
            'adunitid': ad_unit.adunitid,
            'adunittype': ad_unit.adunittype,
            'adunitname': ad_unit.adunitname,
            'publisherid': ad_unit.publisherid,
            'adunitstate': ad_unit.adunitstate,
            'createdby': ad_unit.createdby,
            'updatedby': ad_unit.updatedby,
            'createdat': ad_unit.createdat.isoformat(),
            'updatedat': ad_unit.updatedat.isoformat(),
            'preference': ad_unit.preference
        }
        
        session.close()
        
        return ad_unit_data
    else:
        session.close()
        return None

def get_all_ad_units():
    session = create_session()
    ad_units = session.query(AdUnit).all()
    
    ad_units_data = []
    for ad_unit in ad_units:
        ad_unit_data = {
            'adunitid': ad_unit.adunitid,
            'adunittype': ad_unit.adunittype,
            'adunitname': ad_unit.adunitname,
            'publisherid': ad_unit.publisherid,
            'adunitstate': ad_unit.adunitstate,
            'createdby': ad_unit.createdby,
            'updatedby': ad_unit.updatedby,
            'createdat': ad_unit.createdat.isoformat(),
            'updatedat': ad_unit.updatedat.isoformat(),
            'preference': ad_unit.preference
        }
        ad_units_data.append(ad_unit_data)
    
    session.close()
    
    return ad_units_data

def update_ad_unit_state(ad_unit_id, new_state):
    session = create_session()
    ad_unit = session.query(AdUnit).filter_by(adunitid=ad_unit_id).first()
    
    if ad_unit:
        ad_unit.adunitstate = new_state
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False
    
def get_ad_unit_by_state(ad_unit_state):
    session = create_session()
    ad_units = session.query(AdUnit).filter_by(adunitstate=ad_unit_state).all()
    
    ad_units_data = []
    for ad_unit in ad_units:
        ad_unit_data = {
            'adunitid': ad_unit.adunitid,
            'adunittype': ad_unit.adunittype,
            'adunitname': ad_unit.adunitname,
            'publisherid': ad_unit.publisherid,
            'adunitstate': ad_unit.adunitstate,
            'createdby': ad_unit.createdby,
            'updatedby': ad_unit.updatedby,
            'createdat': ad_unit.createdat.isoformat(),
            'updatedat': ad_unit.updatedat.isoformat(),
            'preference': ad_unit.preference
        }
        ad_units_data.append(ad_unit_data)
    
    session.close()
    
    return ad_units_data

def get_ad_unit_by_publisher(publisher_id):
    session = create_session()
    ad_units = session.query(AdUnit).filter_by(publisherid=publisher_id).all()
    
    ad_units_data = []
    for ad_unit in ad_units:
        ad_unit_data = {
            'adunitid': ad_unit.adunitid,
            'adunittype': ad_unit.adunittype,
            'adunitname': ad_unit.adunitname,
            'publisherid': ad_unit.publisherid,
            'adunitstate': ad_unit.adunitstate,
            'createdby': ad_unit.createdby,
            'updatedby': ad_unit.updatedby,
            'createdat': ad_unit.createdat.isoformat(),
            'updatedat': ad_unit.updatedat.isoformat(),
            'preference': ad_unit.preference
        }
        ad_units_data.append(ad_unit_data)
    
    session.close()
    
    return ad_units_data
