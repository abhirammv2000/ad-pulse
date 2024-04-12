from config.db import create_session
from app.models.advertiser import Advertiser
import time
from datetime import datetime
from app.enums.States import States

def generate_advertiserid():
    current_time = time.localtime()
    formatted_time = time.strftime("%Y%m%d%H%M%S", current_time)
    milliseconds = int(time.time() * 1000) % 1000
    formatted_time += '{:03d}'.format(milliseconds)
    return "A" + formatted_time

def create_advertiser(json_data):
    session = create_session()
    current_time = datetime.now()

    new_advertiser = Advertiser(
        advertiserid=generate_advertiserid(),
        advertisername=json_data.get('advertisername'),
        industry=json_data.get('industry'),
        brands=json_data.get('brands'),
        contactinfo=json_data.get('contactinfo'),
        advertisertype=json_data.get('advertisertype'),
        createdby=json_data.get('createdby'),
        updatedby=json_data.get('updatedby'),
        createdat=current_time,
        updatedat=current_time,
        advertiserstate= States.CREATED.value
    )
    session.add(new_advertiser)
    session.commit()

    created_advertiser = {
        'advertiserid': new_advertiser.advertiserid,
        'advertisername': new_advertiser.advertisername,
        'industry': new_advertiser.industry,
        'brands': new_advertiser.brands,
        'contactinfo': new_advertiser.contactinfo,
        'advertisertype': new_advertiser.advertisertype,
        'createdby': new_advertiser.createdby,
        'updatedby': new_advertiser.updatedby,
        'createdat': new_advertiser.createdat.isoformat(),
        'updatedat': new_advertiser.updatedat.isoformat(),
        'advertiserstate': new_advertiser.advertiserstate
    }

    session.close()
    return created_advertiser

def update_advertiser(json_data):
    session = create_session()
    advertiser_id = json_data.get('advertiserid')
    advertiser = session.query(Advertiser).filter_by(advertiserid=advertiser_id).first()
    current_time = datetime.now()
    
    if advertiser:
        advertiser.advertisername = json_data.get('advertisername', advertiser.advertisername)
        advertiser.industry = json_data.get('industry', advertiser.industry)
        advertiser.brands = json_data.get('brands', advertiser.brands)
        advertiser.contactinfo = json_data.get('contactinfo', advertiser.contactinfo)
        advertiser.advertisertype = json_data.get('advertisertype', advertiser.advertisertype)
        advertiser.updatedby = json_data.get('updatedby', advertiser.updatedby)
        advertiser.updatedat = current_time
        
        session.commit()
        
        updated_advertiser = {
            'advertiserid': advertiser.advertiserid,
            'advertisername': advertiser.advertisername,
            'industry': advertiser.industry,
            'brands': advertiser.brands,
            'contactinfo': advertiser.contactinfo,
            'advertisertype': advertiser.advertisertype,
            'createdby': advertiser.createdby,
            'updatedby': advertiser.updatedby,
            'createdat': advertiser.createdat.isoformat(),
            'updatedat': advertiser.updatedat.isoformat(),
            'advertiserstate': advertiser.advertiserstate
        }
        
        session.close()
        
        return updated_advertiser
    else:
        session.close()
        return None

def get_advertiser_by_id(advertiser_id):
    session = create_session()
    advertiser = session.query(Advertiser).filter_by(advertiserid=advertiser_id).first()
    
    if advertiser:
        advertiser_data = {
            'advertiserid': advertiser.advertiserid,
            'advertisername': advertiser.advertisername,
            'industry': advertiser.industry,
            'brands': advertiser.brands,
            'contactinfo': advertiser.contactinfo,
            'advertisertype': advertiser.advertisertype,
            'createdby': advertiser.createdby,
            'updatedby': advertiser.updatedby,
            'createdat': advertiser.createdat.isoformat(),
            'updatedat': advertiser.updatedat.isoformat(),
            'advertiserstate': advertiser.advertiserstate
        }
        
        session.close()
        
        return advertiser_data
    else:
        session.close()
        return None

def get_all_advertisers():
    session = create_session()
    advertisers = session.query(Advertiser).all()
    
    advertisers_data = []
    for advertiser in advertisers:
        advertiser_data = {
            'advertiserid': advertiser.advertiserid,
            'advertisername': advertiser.advertisername,
            'industry': advertiser.industry,
            'brands': advertiser.brands,
            'contactinfo': advertiser.contactinfo,
            'advertisertype': advertiser.advertisertype,
            'createdby': advertiser.createdby,
            'updatedby': advertiser.updatedby,
            'createdat': advertiser.createdat.isoformat(),
            'updatedat': advertiser.updatedat.isoformat(),
            'advertiserstate': advertiser.advertiserstate
        }
        advertisers_data.append(advertiser_data)
    
    session.close()
    
    return advertisers_data

def update_advertiser_state(advertiser_id, new_state):
    session = create_session()
    advertiser = session.query(Advertiser).filter_by(advertiserid=advertiser_id).first()
    
    if advertiser:
        advertiser.advertiserstate = new_state
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False
    
def get_advertiser_by_state(advertiser_state):
    session = create_session()
    advertisers = session.query(Advertiser).filter_by(advertiserstate=advertiser_state).all()
    
    advertisers_data = []
    for advertiser in advertisers:
        advertiser_data = {
            'advertiserid': advertiser.advertiserid,
            'advertisername': advertiser.advertisername,
            'industry': advertiser.industry,
            'brands': advertiser.brands,
            'contactinfo': advertiser.contactinfo,
            'advertisertype': advertiser.advertisertype,
            'createdby': advertiser.createdby,
            'updatedby': advertiser.updatedby,
            'createdat': advertiser.createdat.isoformat(),
            'updatedat': advertiser.updatedat.isoformat(),
            'advertiserstate': advertiser.advertiserstate
        }
        advertisers_data.append(advertiser_data)
    
    session.close()
    
    return advertisers_data
