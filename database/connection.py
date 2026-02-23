"""
Database connection and session management.
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
from .models import Base


def _ensure_database_exists():
    """Create the MySQL database if it does not already exist."""
    # Only attempt to create a database for server-based DBs (e.g. MySQL).
    # For SQLite (file or memory) there's no server to create.
    from urllib.parse import urlparse

    parsed = urlparse(settings.database_url)
    scheme = parsed.scheme or ""
    if scheme.startswith("mysql") or scheme.startswith("postgres"):
        db_name = parsed.path.lstrip("/")
        # Build a URL without the database name so we can connect to the server
        server_url = settings.database_url.rsplit("/", 1)[0]
        tmp_engine = create_engine(server_url, pool_pre_ping=True)
        with tmp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        tmp_engine.dispose()
    else:
        # No-op for SQLite and other file-based DBs
        return


# Create engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# If using SQLite locally, create tables immediately to make scripts/tests
# usable without running the API lifespan initializer.
from urllib.parse import urlparse
if settings.database_url.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)


def init_db():
    """Initialize database by creating database and tables."""
    _ensure_database_exists()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.
    Use as dependency injection in FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database session.
    Use for non-FastAPI contexts.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
