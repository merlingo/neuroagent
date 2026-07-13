from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for the SQLAlchemy repository")
    url = settings.database_url
    # psycopg3 (psycopg[binary]) requires the postgresql+psycopg:// dialect prefix.
    # "postgresql://" does NOT contain "postgres://" as a substring, so we slice instead.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    elif url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    return create_engine(url)


def get_session_local():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


SessionLocal = get_session_local
