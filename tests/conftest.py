import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.database import Base


def setup_test_db():
    """Create isolated in-memory test database"""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    engine = create_engine(os.getenv("DATABASE_URL"))
    Base.metadata.create_all(bind=engine)
    return engine


def override_get_db():
    """Test dependency override"""
    engine = setup_test_db()
    TestingSessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    try:
        yield TestingSessionLocal()
    finally:
        TestingSessionLocal.remove()


# Configure test client
from fastapi.testclient import TestClient
from src.main import app

app.dependency_overrides[app.dependency_overrides.get('get_db', lambda: None)] = override_get_db
client = TestClient(app)