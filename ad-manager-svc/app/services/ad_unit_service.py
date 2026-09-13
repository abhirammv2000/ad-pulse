from datetime import datetime

from app.enums.States import States
from app.models.ad_unit import AdUnit
from app.services import crud
from config.db import session_scope

UPDATABLE_FIELDS = ('adunittype', 'adunitname', 'publisherid', 'updatedby', 'preference')


def generate_adunitid():
    return crud.generate_id("ADU")


def create_ad_unit(json_data):
    now = datetime.now()
    with session_scope() as session:
        ad_unit = AdUnit(
            adunitid=generate_adunitid(),
            adunittype=json_data.get('adunittype'),
            adunitname=json_data.get('adunitname'),
            publisherid=json_data.get('publisherid'),
            adunitstate=States.CREATED.value,
            createdby=json_data.get('createdby'),
            updatedby=json_data.get('updatedby'),
            createdat=now,
            updatedat=now,
            preference=json_data.get('preference'),
        )
        session.add(ad_unit)
        return ad_unit.to_dict()


def update_ad_unit(json_data):
    with session_scope() as session:
        ad_unit = session.query(AdUnit).filter_by(adunitid=json_data.get('adunitid')).first()
        if ad_unit is None:
            return None
        crud.apply_updates(ad_unit, json_data, UPDATABLE_FIELDS)
        return ad_unit.to_dict()


def get_ad_unit_by_id(ad_unit_id):
    return crud.get_by_id(AdUnit, AdUnit.adunitid, ad_unit_id)


def get_all_ad_units():
    return crud.get_all(AdUnit)


def update_ad_unit_state(ad_unit_id, new_state):
    return crud.update_state(AdUnit, AdUnit.adunitid, ad_unit_id, 'adunitstate', new_state)


def get_ad_unit_by_state(ad_unit_state):
    return crud.get_where(AdUnit, adunitstate=ad_unit_state)


def get_ad_unit_by_publisher(publisher_id):
    return crud.get_where(AdUnit, publisherid=publisher_id)
