import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mockproj.db")

# check_same_thread=False is needed only for SQLite to allow multiple threads
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    """Generator function yielding DB session, compatible with FastAPI Depends."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Context manager version for manual session handling in other files
get_session_ctx = contextmanager(get_session)
