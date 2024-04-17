from config.db import create_session
from app.models.publisher import Publisher
import time
from datetime import datetime
from app.enums.States import States

def generate_publisherid():
    current_time = time.localtime()
    formatted_time = time.strftime("%Y%m%d%H%M%S", current_time)
    milliseconds = int(time.time() * 1000) % 1000
    formatted_time += '{:03d}'.format(milliseconds)
    return "P" + formatted_time

def create_publisher(json_data):
    session = create_session()
    current_time = datetime.now()

    new_publisher = Publisher(
        publisherid=generate_publisherid(),
        publishername=json_data.get('publishername'),
        contactinfo=json_data.get('contactinfo'),
        publisherstate= States.CREATED.value,
        publisherdomain=json_data.get('publisherdomain'),
        createdby=json_data.get('createdby'),
        updatedby=json_data.get('updatedby'),
        createdat=current_time,
        updatedat=current_time,
        preference=json_data.get('preference')
    )
    session.add(new_publisher)
    session.commit()

    # Return the created publisher data
    created_publisher = {
        'publisherid': new_publisher.publisherid,
        'publishername': new_publisher.publishername,
        'contactinfo': new_publisher.contactinfo,
        'publisherstate': new_publisher.publisherstate,
        'publisherdomain': new_publisher.publisherdomain,
        'createdby': new_publisher.createdby,
        'updatedby': new_publisher.updatedby,
        'createdat': new_publisher.createdat.isoformat(),
        'updatedat': new_publisher.updatedat.isoformat(),
        'preference': new_publisher.preference
    }

    session.close()
    return created_publisher


def update_publisher(json_data):
    session = create_session()
    publisher_id = json_data.get('publisherid')
    publisher = session.query(Publisher).filter_by(publisherid=publisher_id).first()
    current_time = datetime.now()
    
    if publisher:
        # Update allowed fields
        publisher.publishername = json_data.get('publishername', publisher.publishername)
        publisher.contactinfo = json_data.get('contactinfo', publisher.contactinfo)
        publisher.publisherdomain = json_data.get('publisherdomain', publisher.publisherdomain)
        publisher.updatedby = json_data.get('updatedby', publisher.updatedby)
        publisher.updatedat = current_time
        publisher.preference = json_data.get('preference', publisher.preference)
        
        # Commit changes
        session.commit()
        
        # Return updated publisher data
        updated_publisher = {
            'publisherid': publisher.publisherid,
            'publishername': publisher.publishername,
            'contactinfo': publisher.contactinfo,
            'publisherstate': publisher.publisherstate,
            'publisherdomain': publisher.publisherdomain,
            'createdby': publisher.createdby,
            'updatedby': publisher.updatedby,
            'createdat': publisher.createdat.isoformat(),
            'updatedat': publisher.updatedat.isoformat(),
            'preference': publisher.preference
        }
        
        session.close()
        
        return updated_publisher
    else:
        session.close()
        return None

def get_publisher_by_id(publisher_id):
    session = create_session()
    publisher = session.query(Publisher).filter_by(publisherid=publisher_id).first()
    
    if publisher:
        publisher_data = {
            'publisherid': publisher.publisherid,
            'publishername': publisher.publishername,
            'contactinfo': publisher.contactinfo,
            'publisherstate': publisher.publisherstate,
            'publisherdomain': publisher.publisherdomain,
            'createdby': publisher.createdby,
            'updatedby': publisher.updatedby,
            'createdat': publisher.createdat.isoformat(),
            'updatedat': publisher.updatedat.isoformat(),
            'preference': publisher.preference
        }
        
        session.close()
        
        return publisher_data
    else:
        session.close()
        return None
    
def get_all_publishers():
    session = create_session()
    publishers = session.query(Publisher).all()
    
    publishers_data = []
    for publisher in publishers:
        publisher_data = {
            'publisherid': publisher.publisherid,
            'publishername': publisher.publishername,
            'contactinfo': publisher.contactinfo,
            'publisherstate': publisher.publisherstate,
            'publisherdomain': publisher.publisherdomain,
            'createdby': publisher.createdby,
            'updatedby': publisher.updatedby,
            'createdat': publisher.createdat.isoformat(),
            'updatedat': publisher.updatedat.isoformat(),
            'preference': publisher.preference
        }
        publishers_data.append(publisher_data)
    
    session.close()
    
    return publishers_data

def update_publisher_state(publisher_id, new_state):
    session = create_session()
    publisher = session.query(Publisher).filter_by(publisherid=publisher_id).first()
    
    if publisher:
        publisher.publisherstate = new_state
        session.commit()
        session.close()
        return True
    else:
        session.close()
        return False
    
def get_publisher_by_state(publisher_state):
    session = create_session()
    publishers = session.query(Publisher).filter_by(publisherstate=publisher_state).all()
    
    publishers_data = []
    for publisher in publishers:
        publisher_data = {
            'publisherid': publisher.publisherid,
            'publishername': publisher.publishername,
            'contactinfo': publisher.contactinfo,
            'publisherstate': publisher.publisherstate,
            'publisherdomain': publisher.publisherdomain,
            'createdby': publisher.createdby,
            'updatedby': publisher.updatedby,
            'createdat': publisher.createdat.isoformat(),
            'updatedat': publisher.updatedat.isoformat(),
            'preference': publisher.preference
        }
        publishers_data.append(publisher_data)
    
    session.close()
    
    return publishers_data