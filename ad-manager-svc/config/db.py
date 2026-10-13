import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_Session = None
_engine = None


def _get_database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Point it at the Postgres instance, e.g. "
            "postgresql://user:password@host:5432/postgres"
        )
    # This service installs psycopg2, but SQLAlchemy 2.1 made psycopg 3 the
    # default driver for a plain postgresql:// url, which crashes at startup.
    # Naming the driver works with every SQLAlchemy version.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_get_database_url(), pool_pre_ping=True)
    return _engine


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
        _Session = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _Session()


def init_db():
    """Create any tables that don't exist yet.

    This is what builds the schema when the service starts. It only creates missing tables, so it is safe to
    call on every startup, including against a database that already has data. It never changes an existing
    table. Changes to existing tables go through the Alembic migrations in migrations/ (see the README).
    """
    from app.models import Base  # noqa: F401 imports every model so it registers on Base.metadata

    Base.metadata.create_all(_get_engine())


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
