from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class Ad(Base):
    __tablename__ = 'ads'

    adid = Column(String, primary_key=True)
    adname = Column(String)
    campaignid = Column(String, ForeignKey('campaign.campaignid'))
    advertiserid = Column(String, ForeignKey('advertiser.advertiserid'))
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

    def __repr__(self):
        return f"<Ad(adid='{self.adid}', adname='{self.adname}', adstate='{self.adstate}')>"
