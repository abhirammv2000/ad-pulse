from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def create_session():
    engine = create_engine("postgresql://postgres.htppxkcokqiphaqkpnjc:OLmxCwYk8i8nan86@aws-0-us-west-1.pooler.supabase.com:6543/postgres")
    Session = sessionmaker(bind=engine)
    session = Session()
    return session
