from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for the SQLAlchemy repository")
    return create_engine(settings.database_url)


def get_session_local():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


SessionLocal = get_session_local
