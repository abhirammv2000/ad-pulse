from sqlalchemy import Column, String, DateTime, JSON, ForeignKey

from app.models.advertiser import Advertiser
from app.models.base import Base


class Creative(Base):
    __tablename__ = 'creative'

    creativeid = Column(String, primary_key=True, nullable=False)
    creativetype = Column(String)
    creativename = Column(String)
    creativestate = Column(String)
    advertiserid = Column(String, ForeignKey(Advertiser.advertiserid), nullable=False)
    createdby = Column(String)
    updatedby = Column(String)
    createdat = Column(DateTime)
    updatedat = Column(DateTime)
    assets = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Creative(creativeid='{self.creativeid}', creativename='{self.creativename}', creativestate='{self.creativestate}')>"
