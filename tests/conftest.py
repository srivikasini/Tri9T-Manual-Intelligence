"""Pytest configuration and shared fixtures."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.models
from app.core.database import Base, get_db
from app.main import app
from app.api.ingest import perform_ingestion

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=eng)
    return eng

@pytest.fixture(scope="session")
def db_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def populated_db(db_session_factory):
    """Session-scoped database pre-populated with v1 and v2 manuals."""
    db = db_session_factory()
    try:
        # Ingest v1 and v2
        v1_path = Path("data/ct200_manual.pdf")
        v2_path = Path("data/ct200_manual_v2.pdf")
        
        perform_ingestion(v1_path, "v1", "ct200_manual", db)
        perform_ingestion(v2_path, "v2", "ct200_manual", db)
        
        yield db
    finally:
        db.close()

@pytest.fixture
def db(db_session_factory):
    """Function-scoped database session."""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def client(populated_db):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield populated_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
