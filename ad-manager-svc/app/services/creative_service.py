from config.db import create_session
from app.models.creative import Creative
import time
from datetime import datetime
from app.enums.States import States

def generate_creativeid():
    current_time = time.localtime()
    formatted_time = time.strftime("%Y%m%d%H%M%S", current_time)
    milliseconds = int(time.time() * 1000) % 1000
    formatted_time += '{:03d}'.format(milliseconds)
    return "CR" + formatted_time

def create_creative(json_data):
    session = create_session()
    current_time = datetime.now()

    new_creative = Creative(
        creativeid=generate_creativeid(),
        creativetype=json_data.get('creativetype'),
        creativename=json_data.get('creativename'),
        creativestate=States.ACTIVE.value,
        advertiserid=json_data.get('advertiserid'),
        createdby=json_data.get('createdby'),
        updatedby=json_data.get('updatedby'),
        createdat=current_time,
        updatedat=current_time,
        assets=json_data.get('assets')
    )
    session.add(new_creative)
    session.commit()

    created_creative = {
        'creativeid': new_creative.creativeid,
        'creativetype': new_creative.creativetype,
        'creativename': new_creative.creativename,
        'creativestate': new_creative.creativestate,
        'advertiserid': new_creative.advertiserid,
        'createdby': new_creative.createdby,
        'updatedby': new_creative.updatedby,
        'createdat': new_creative.createdat.isoformat(),
        'updatedat': new_creative.updatedat.isoformat(),
        'assets': new_creative.assets
    }

    session.close()
    return created_creative

def update_creative(json_data):
    session = create_session()
    creative_id = json_data.get('creativeid')
    creative = session.query(Creative).filter_by(creativeid=creative_id).first()
    current_time = datetime.now()
    
    if creative:
        creative.creativetype = json_data.get('creativetype', creative.creativetype)
        creative.creativename = json_data.get('creativename', creative.creativename)
        creative.advertiserid = json_data.get('advertiserid', creative.advertiserid)
        creative.assets = json_data.get('assets', creative.assets)
        creative.updatedby = json_data.get('updatedby', creative.updatedby)
        creative.updatedat = current_time
        
        session.commit()
        
        updated_creative = {
            'creativeid': creative.creativeid,
            'creativetype': creative.creativetype,
            'creativename': creative.creativename,
            'creativestate': creative.creativestate,
            'advertiserid': creative.advertiserid,
            'createdby': creative.createdby,
            'updatedby': creative.updatedby,
            'createdat': creative.createdat.isoformat(),
            'updatedat': creative.updatedat.isoformat(),
            'assets': creative.assets
        }
        
        session.close()
        
        return updated_creative
    else:
        session.close()
        return None

def get_creative_by_id(creative_id):
    session = create_session()
    creative = session.query(Creative).filter_by(creativeid=creative_id).first()
    
    if creative:
        creative_data = {
            'creativeid': creative.creativeid,
            'creativetype': creative.creativetype,
            'creativename': creative.creativename,
            'creativestate': creative.creativestate,
            'advertiserid': creative.advertiserid,
            'createdby': creative.createdby,
            'updatedby': creative.updatedby,
            'createdat': creative.createdat.isoformat(),
            'updatedat': creative.updatedat.isoformat(),
            'assets': creative.assets
        }
        
        session.close()
        
        return creative_data
    else:
        session.close()
        return None

def get_all_creatives():
    session = create_session()
    creatives = session.query(Creative).all()
    
    creatives_data = []
    for creative in creatives:
        creative_data = {
            'creativeid': creative.creativeid,
            'creativetype': creative.creativetype,
            'creativename': creative.creativename,
            'creativestate': creative.creativestate,
            'advertiserid': creative.advertiserid,
            'createdby': creative.createdby,
            'updatedby': creative.updatedby,
            'createdat': creative.createdat.isoformat(),
            'updatedat': creative.updatedat.isoformat(),
            'assets': creative.assets
        }
        creatives_data.append(creative_data)
    
    session.close()
    
    return creatives_data

def update_creative_state(creative_id, new_state):
    session = create_session()
    creative = session.query(Creative).filter_by(creativeid=creative_id).first()
    
    if creative:
        creative.creativestate = new_state
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False
    
def get_creative_by_state(creative_state):
    session = create_session()
    creatives = session.query(Creative).filter_by(creativestate=creative_state).all()
    
    creatives_data = []
    for creative in creatives:
        creative_data = {
            'creativeid': creative.creativeid,
            'creativetype': creative.creativetype,
            'creativename': creative.creativename,
            'creativestate': creative.creativestate,
            'advertiserid': creative.advertiserid,
            'createdby': creative.createdby,
            'updatedby': creative.updatedby,
            'createdat': creative.createdat.isoformat(),
            'updatedat': creative.updatedat.isoformat(),
            'assets': creative.assets
        }
        creatives_data.append(creative_data)
    
    session.close()
    
    return creatives_data

def get_creative_by_advertiser_id(advertiser_id):
    session = create_session()
    creatives = session.query(Creative).filter(Creative.advertiserid == advertiser_id).all()
    creative_list = []
    for creative in creatives:
        creative_data = {
            'creativeid': creative.creativeid,
            'creativetype': creative.creativetype,
            'creativename': creative.creativename,
            'creativestate': creative.creativestate,
            'advertiserid': creative.advertiserid,
            'createdby': creative.createdby,
            'updatedby': creative.updatedby,
            'createdat': creative.createdat.isoformat(),
            'updatedat': creative.updatedat.isoformat(),
            'assets': creative.assets
        }
        creative_list.append(creative_data)
    
    session.close()
    
    return creative_list
