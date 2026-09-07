from datetime import date, datetime

from sqlalchemy import inspect
from sqlalchemy.orm import declarative_base


def _jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class _Model:
    """Behaviour shared by every table.

    ``to_dict`` replaces the hand-written field-by-field dictionaries that used
    to appear in every service function, so adding a column no longer means
    editing six call sites.
    """

    @classmethod
    def column_names(cls):
        return [attr.key for attr in inspect(cls).mapper.column_attrs]

    def to_dict(self):
        return {name: _jsonable(getattr(self, name)) for name in self.column_names()}


# One declarative base for all models. Previously each module built its own,
# which put every table in a separate MetaData and left the ForeignKey targets
# unresolvable from any single registry.
Base = declarative_base(cls=_Model)
