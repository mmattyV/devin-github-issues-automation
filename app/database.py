"""
Database setup and session management using SQLAlchemy.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging

from app.config import get_settings
from app.models import Base

logger = logging.getLogger(__name__)


# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """
    Get or create the SQLAlchemy engine.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        
        # Special handling for SQLite to enable foreign keys and use static pool
        if settings.database_url.startswith("sqlite"):
            _engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.log_level == "DEBUG"
            )
            
            # Enable foreign key support for SQLite
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            _engine = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                echo=settings.log_level == "DEBUG"
            )
        
        logger.info(f"Database engine created: {settings.database_url}")
    
    return _engine


def get_session_factory():
    """
    Get or create the session factory.
    
    Returns:
        sessionmaker: SQLAlchemy session factory
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db():
    """
    Initialize the database by creating all tables.
    Safe to call multiple times - only creates tables that don't exist.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")


def drop_db():
    """
    Drop all tables from the database.
    WARNING: This deletes all data! Use only for testing or cleanup.
    """
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


@contextmanager
def get_db() -> Generator[SQLAlchemySession, None, None]:
    """
    Context manager for database sessions.
    Automatically handles commit/rollback and session cleanup.
    
    Usage:
        with get_db() as db:
            db.query(Issue).all()
    
    Yields:
        Session: SQLAlchemy database session
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error, rolling back: {e}")
        raise
    finally:
        db.close()


def get_db_session() -> SQLAlchemySession:
    """
    Get a database session (for dependency injection in FastAPI).
    
    Usage in FastAPI:
        @app.get("/")
        def read_root(db: Session = Depends(get_db_session)):
            ...
    
    Yields:
        Session: SQLAlchemy database session
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """
    Reset the database by dropping and recreating all tables.
    WARNING: This deletes all data! Use only for testing.
    """
    drop_db()
    init_db()
    logger.info("Database reset complete")
