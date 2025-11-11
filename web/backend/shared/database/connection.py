"""
Database connection and session management
Handles SQLAlchemy engine and session creation
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import os
import logging

logger = logging.getLogger(__name__)

# Database configuration
# Use absolute path for SQLite database to ensure consistency
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
default_db_path = os.path.join(backend_root, 'hydroclaude_web.db')
DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{default_db_path}')

# Create engine
if DATABASE_URL.startswith('sqlite'):
    # SQLite specific configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL query logging
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session
    Usage in FastAPI:
        def my_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database
    Create all tables if they don't exist
    """
    from .models import Base

    logger.info("Initializing database...")
    logger.info(f"Database URL: {DATABASE_URL}")

    # Create all tables
    Base.metadata.create_all(bind=engine)

    logger.info("Database initialized successfully")


def drop_db():
    """
    Drop all database tables
    WARNING: This will delete all data!
    """
    from .models import Base

    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


def reset_db():
    """
    Reset database (drop and recreate)
    WARNING: This will delete all data!
    """
    drop_db()
    init_db()
