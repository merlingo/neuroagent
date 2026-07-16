from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import get_settings


def normalize_db_url(url: str) -> str:
    """Force the psycopg3 dialect. We ship psycopg[binary] (psycopg3), not psycopg2,
    so a bare ``postgresql://`` URL (which SQLAlchemy maps to psycopg2) must be
    rewritten to ``postgresql+psycopg://``. Used by both the app engine and Alembic.
    ``postgresql://`` does NOT contain ``postgres://`` as a substring, so we slice."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


@lru_cache
def get_engine():
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for the SQLAlchemy repository")
    return create_engine(normalize_db_url(settings.database_url))


def get_session_local():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


SessionLocal = get_session_local
