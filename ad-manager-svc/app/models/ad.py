from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

from app.models.campaign import Campaign
from app.models.advertiser import Advertiser

Base = declarative_base()

class Ad(Base):
    __tablename__ = 'ads'

    adid = Column(String, primary_key=True)
    adname = Column(String)
    campaignid = Column(String, ForeignKey(Campaign.campaignid), nullable=False)
    advertiserid = Column(String, ForeignKey(Advertiser.advertiserid), nullable=False)
    creativeid = Column(String)
    startdate = Column(DateTime)
    enddate = Column(DateTime)
    landingurl = Column(String)
    budget = Column(JSONB)
    frequencycaps = Column(JSONB)
    bidinfo = Column(JSONB)
    adtype = Column(String)
    adpriority = Column(Integer)
    targetinginfo = Column(JSONB)
    createdat = Column(DateTime)
    updatedat = Column(DateTime)
    createdby = Column(String)
    updatedby = Column(String)
    adstate = Column(String)
    ad_unit_targeted = Column(String)

    def __repr__(self):
        return f"<Ad(adid='{self.adid}', adname='{self.adname}', adstate='{self.adstate}')>"
