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
    # psycopg3 (psycopg[binary]) requires postgresql+psycopg:// dialect prefix
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return create_engine(url)


def get_session_local():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


SessionLocal = get_session_local
