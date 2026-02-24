from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
from .models import Base


def _ensure_database_exists():
    from urllib.parse import urlparse

    parsed = urlparse(settings.database_url)
    scheme = parsed.scheme or ""
    if scheme.startswith("mysql") or scheme.startswith("postgres"):
        db_name = parsed.path.lstrip("/")
        server_url = settings.database_url.rsplit("/", 1)[0]
        tmp_engine = create_engine(server_url, pool_pre_ping=True)
        with tmp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        tmp_engine.dispose()
    else:
        return


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from urllib.parse import urlparse
if settings.database_url.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)


def init_db():
    _ensure_database_exists()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
