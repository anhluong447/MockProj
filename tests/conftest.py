import sys
from pathlib import Path

# Add project root to sys.path to ensure src imports work properly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.db.models import Base
from src.db.repository import HistoryRepository
from src.db.database import get_session
from src.api import app

@pytest.fixture(scope="function")
def db_session():
    """Provides a thread-safe, isolated SQLite in-memory session per test function."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()

@pytest.fixture(scope="function")
def repo(db_session):
    """Provides a HistoryRepository associated with the isolated test session."""
    return HistoryRepository(db_session)

@pytest.fixture(scope="function")
def api_client(db_session):
    """Provides a FastAPI TestClient with the database dependency overridden with the test session."""
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
