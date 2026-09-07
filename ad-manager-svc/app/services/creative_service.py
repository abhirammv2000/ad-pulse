from datetime import datetime

from app.enums.States import States
from app.models.creative import Creative
from app.services import crud
from config.db import session_scope

UPDATABLE_FIELDS = ('creativetype', 'creativename', 'advertiserid', 'assets', 'updatedby')


def generate_creativeid():
    return crud.generate_id("CR")


def create_creative(json_data):
    now = datetime.now()
    with session_scope() as session:
        creative = Creative(
            creativeid=generate_creativeid(),
            creativetype=json_data.get('creativetype'),
            creativename=json_data.get('creativename'),
            # Creatives go live immediately: they carry no flight dates of their
            # own, so there is nothing to schedule.
            creativestate=States.ACTIVE.value,
            advertiserid=json_data.get('advertiserid'),
            createdby=json_data.get('createdby'),
            updatedby=json_data.get('updatedby'),
            createdat=now,
            updatedat=now,
            assets=json_data.get('assets'),
        )
        session.add(creative)
        return creative.to_dict()


def update_creative(json_data):
    with session_scope() as session:
        creative = session.query(Creative).filter_by(creativeid=json_data.get('creativeid')).first()
        if creative is None:
            return None
        crud.apply_updates(creative, json_data, UPDATABLE_FIELDS)
        return creative.to_dict()


def get_creative_by_id(creative_id):
    return crud.get_by_id(Creative, Creative.creativeid, creative_id)


def get_all_creatives():
    return crud.get_all(Creative)


def update_creative_state(creative_id, new_state):
    return crud.update_state(Creative, Creative.creativeid, creative_id, 'creativestate', new_state)


def get_creative_by_state(creative_state):
    return crud.get_where(Creative, creativestate=creative_state)


def get_creative_by_advertiser_id(advertiser_id):
    return crud.get_where(Creative, advertiserid=advertiser_id)
