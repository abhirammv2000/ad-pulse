from enum import Enum

class States(Enum):
    CREATED = 'CREATED'
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
    EXPIRED = 'EXPIRED'
    EXHAUSTED = 'EXHAUSTED'