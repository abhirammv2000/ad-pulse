from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def create_session():
    engine = create_engine("postgresql://postgres.htppxkcokqiphaqkpnjc:REDACTED@aws-0-us-west-1.pooler.supabase.com:5432/postgres")
    Session = sessionmaker(bind=engine)
    session = Session()
    return session
