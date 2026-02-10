import os
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None
_init_lock = threading.Lock()


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://opensource:opensource@postgres:5432/incident_management",
    )


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _session_factory


def init_models() -> None:
    if os.environ.get("DB_AUTO_CREATE", "1") != "1":
        return
    with _init_lock:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
