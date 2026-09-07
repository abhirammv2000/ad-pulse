"""Query helpers shared by the six entity services.

Every entity is keyed by a string id, carries a `<name>state` column and is
returned to the API as a plain dict, so the read paths are identical apart from
the model and column names.
"""

import time
from datetime import datetime

from config.db import session_scope


def generate_id(prefix):
    """Build a sortable id: prefix + UTC-local timestamp to the millisecond."""
    now = time.time()
    return "{}{}{:03d}".format(
        prefix,
        time.strftime("%Y%m%d%H%M%S", time.localtime(now)),
        int(now * 1000) % 1000,
    )


def get_by_id(model, id_column, entity_id):
    with session_scope() as session:
        row = session.query(model).filter(id_column == entity_id).first()
        return row.to_dict() if row else None


def get_all(model):
    with session_scope() as session:
        return [row.to_dict() for row in session.query(model).all()]


def get_where(model, **filters):
    with session_scope() as session:
        return [row.to_dict() for row in session.query(model).filter_by(**filters).all()]


def update_state(model, id_column, entity_id, state_column_name, new_state):
    """Set an entity's state column. Returns False when the id is unknown."""
    with session_scope() as session:
        row = session.query(model).filter(id_column == entity_id).first()
        if row is None:
            return False
        setattr(row, state_column_name, new_state)
        row.updatedat = datetime.now()
        return True


def apply_updates(row, json_data, fields):
    """Copy `fields` from the request body onto `row`, leaving absent keys alone."""
    for field in fields:
        if field in json_data:
            setattr(row, field, json_data[field])
    row.updatedat = datetime.now()
