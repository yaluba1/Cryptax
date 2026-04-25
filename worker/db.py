"""
Database connection and session management for the worker.
Replicates the SQLAlchemy setup from the API.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from worker.config import settings

# MariaDB connection string
# Format: mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Check connection health before using it
    pool_recycle=3600,   # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db_session():
    """Returns a new database session."""
    return SessionLocal()
