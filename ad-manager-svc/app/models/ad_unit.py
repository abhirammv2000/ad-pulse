from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from app.models.publisher import Publisher

class AdUnit(Base):
    __tablename__ = 'adunit'

    adunitid = Column(String, primary_key=True)
    adunittype = Column(String)
    adunitname = Column(String)
    publisherid = Column(String, ForeignKey(Publisher.publisherid), nullable=False)
    adunitstate = Column(String)
    createdby = Column(String)
    updatedby = Column(String)
    createdat = Column(DateTime)
    updatedat = Column(DateTime)
    preference = Column(JSON)

    def __repr__(self):
        return f"<AdUnit(adunitid='{self.adunitid}', adunitname='{self.adunitname}', adunitstate='{self.adunitstate}')>"