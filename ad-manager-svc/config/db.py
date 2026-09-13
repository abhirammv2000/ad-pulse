import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_Session = None


def _get_database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Point it at the Postgres instance, e.g. "
            "postgresql://user:password@host:5432/postgres"
        )
    return url


def create_session():
    """Return a new Session from the shared engine.

    The engine owns the connection pool, so it is built once and reused; the
    previous version created a fresh pool on every call.

    ``expire_on_commit`` is off so callers can still read an object's fields
    after the transaction closes, which is what the service layer does when it
    serializes a row it has just written.
    """
    global _Session
    if _Session is None:
        engine = create_engine(_get_database_url(), pool_pre_ping=True)
        _Session = sessionmaker(bind=engine, expire_on_commit=False)
    return _Session()


@contextmanager
def session_scope():
    """Run a block in one transaction, rolling back and always closing."""
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
