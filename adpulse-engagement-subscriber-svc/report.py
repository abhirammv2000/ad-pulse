from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Report(Base):
    __tablename__ = 'reports'

    ad_id = Column(String, primary_key=True)
    clicks = Column(Integer)
    renders = Column(Integer)

    def __repr__(self):
        return f"<Report(ad_id='{self.ad_id}', clicks='{self.clicks}', renders='{self.renders}')>"