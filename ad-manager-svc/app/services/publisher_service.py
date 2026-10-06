from datetime import datetime

from app.enums.states import States
from app.models.publisher import Publisher
from app.services import crud
from config.db import session_scope

# Fields a client is allowed to change through PUT /publisher. Everything else
# (id, state, createdat, createdby) is owned by the service.
UPDATABLE_FIELDS = ('publishername', 'contactinfo', 'publisherdomain', 'updatedby', 'preference')


def generate_publisherid():
    return crud.generate_id("P")


def create_publisher(json_data):
    now = datetime.now()
    with session_scope() as session:
        publisher = Publisher(
            publisherid=generate_publisherid(),
            publishername=json_data.get('publishername'),
            contactinfo=json_data.get('contactinfo'),
            publisherstate=States.CREATED.value,
            publisherdomain=json_data.get('publisherdomain'),
            createdby=json_data.get('createdby'),
            updatedby=json_data.get('updatedby'),
            createdat=now,
            updatedat=now,
            preference=json_data.get('preference'),
        )
        session.add(publisher)
        return publisher.to_dict()


def update_publisher(json_data):
    with session_scope() as session:
        publisher = session.query(Publisher).filter_by(publisherid=json_data.get('publisherid')).first()
        if publisher is None:
            return None
        crud.apply_updates(publisher, json_data, UPDATABLE_FIELDS)
        return publisher.to_dict()


def get_publisher_by_id(publisher_id):
    return crud.get_by_id(Publisher, Publisher.publisherid, publisher_id)


def get_all_publishers():
    return crud.get_all(Publisher)


def update_publisher_state(publisher_id, new_state):
    return crud.update_state(Publisher, Publisher.publisherid, publisher_id, 'publisherstate', new_state)


def get_publisher_by_state(publisher_state):
    return crud.get_where(Publisher, publisherstate=publisher_state)
