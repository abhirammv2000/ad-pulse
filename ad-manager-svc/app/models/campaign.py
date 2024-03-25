from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Campaign(Base):
    __tablename__ = 'campaign'
    
    campaignid = Column(String, primary_key=True, nullable=False)
    campaignname = Column(String)
    advertiserid = Column(String, ForeignKey('advertiser.advertiserid'))
    startdate = Column(DateTime)
    enddate = Column(DateTime)
    budget = Column(JSONB)
    frequencycaps = Column(JSONB)
    createdat = Column(DateTime)
    updatedat = Column(DateTime)
    createdby = Column(String)
    updatedby = Column(String)
    campaignstate = Column(String) 
    # Define relationship with advertiser table
    # advertiser = relationship("Advertiser", back_populates="campaigns")

    def __repr__(self):
        return f"<Campaign(campaignid='{self.campaignid}', campaignname='{self.campaignname}', campaignstate='{self.campaignstate}')>"
