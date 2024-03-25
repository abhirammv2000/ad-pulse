from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Publisher(Base):
    __tablename__ = 'publisher'
    
    publisherid = Column(String, primary_key=True, nullable=False)
    publishername = Column(String)
    contactinfo = Column(JSON)
    publisherstate = Column(String)
    publisherdomain = Column(String)
    createdby = Column(String)
    updatedby = Column(String)
    createdat = Column(DateTime)
    updatedat = Column(DateTime)
    preference = Column(JSON)

    def __repr__(self):
        return f"<Publisher(id={self.publisherid}, name='{self.publishername}', state='{self.publisherstate}')>"