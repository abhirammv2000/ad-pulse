from datetime import datetime

from app.enums.states import States
from app.models.advertiser import Advertiser
from app.services import crud
from config.db import session_scope

UPDATABLE_FIELDS = ('advertisername', 'industry', 'brands', 'contactinfo', 'advertisertype', 'updatedby')


def generate_advertiserid():
    return crud.generate_id("A")


def create_advertiser(json_data):
    now = datetime.now()
    with session_scope() as session:
        advertiser = Advertiser(
            advertiserid=generate_advertiserid(),
            advertisername=json_data.get('advertisername'),
            industry=json_data.get('industry'),
            brands=json_data.get('brands'),
            contactinfo=json_data.get('contactinfo'),
            advertisertype=json_data.get('advertisertype'),
            createdby=json_data.get('createdby'),
            updatedby=json_data.get('updatedby'),
            createdat=now,
            updatedat=now,
            advertiserstate=States.CREATED.value,
        )
        session.add(advertiser)
        return advertiser.to_dict()


def update_advertiser(json_data):
    with session_scope() as session:
        advertiser = session.query(Advertiser).filter_by(advertiserid=json_data.get('advertiserid')).first()
        if advertiser is None:
            return None
        crud.apply_updates(advertiser, json_data, UPDATABLE_FIELDS)
        return advertiser.to_dict()


def get_advertiser_by_id(advertiser_id):
    return crud.get_by_id(Advertiser, Advertiser.advertiserid, advertiser_id)


def get_all_advertisers():
    return crud.get_all(Advertiser)


def update_advertiser_state(advertiser_id, new_state):
    return crud.update_state(Advertiser, Advertiser.advertiserid, advertiser_id, 'advertiserstate', new_state)


def get_advertiser_by_state(advertiser_state):
    return crud.get_where(Advertiser, advertiserstate=advertiser_state)
