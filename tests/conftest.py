"""Test configuration and fixtures."""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.database import Base, get_db
from src.main import app

# Test database URL - use SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    future=True
)

# Create test session
TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Create test database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Generator:
    """Create a test client."""
    yield TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client using ASGI transport."""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_tenant(db_session: AsyncSession):
    """Create a sample tenant for testing."""
    from src.models.tenant import Tenant

    tenant = Tenant(
        name="Test Tenant",
        tenant_id="test-tenant-123",
        client_id="test-client-id",
        client_secret="gAAAAABe...",  # Encrypted placeholder
        is_active=True
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin user for testing."""
    from src.models.user import User
    import bcrypt

    password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()

    user = User(
        username="admin",
        password_hash=password_hash,
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# Rate limiter fixture - uses in-memory, not Redis
@pytest.fixture
def rate_limiter():
    """Create a rate limiter with in-memory storage (no Redis)."""
    from src.services.rate_limit import rate_limiter as rl
    # Clear any existing state
    rl._memory_storage.clear()
    return rl


# Mock database fixture for unit tests
@pytest.fixture
def mock_db():
    """Create a mock database session for unit tests."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.add = MagicMock()
    mock.add_all = MagicMock()
    mock.delete = AsyncMock()
    mock.close = AsyncMock()
    
    # Common query result patterns
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar_one.return_value = None
    mock_result.scalars.return_value = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_result.scalars().first.return_value = None
    mock.execute.return_value = mock_result
    
    return mock


# Alias for compatibility with tests that use test_db
@pytest.fixture
def test_db(mock_db):
    """Alias for mock_db fixture."""
    return mock_db


# Mock tenant fixture
@pytest.fixture
def mock_tenant():
    """Create a mock tenant for testing."""
    from unittest.mock import MagicMock
    
    tenant = MagicMock()
    tenant.id = "test-tenant-id"
    tenant.tenant_id = "test-tenant-123"
    tenant.name = "Test Tenant"
    tenant.client_id = "test-client-id"
    tenant.client_secret = "encrypted-secret"
    tenant.is_active = True
    tenant.connection_status = "healthy"
    tenant.connection_error = None
    return tenant


# Mock for MS Graph client
@pytest.fixture
def mock_ms_graph():
    """Create a mock MS Graph client."""
    from unittest.mock import MagicMock, AsyncMock

    mock = MagicMock()
    mock.get_users = AsyncMock(return_value=[{"id": "1", "displayName": "Test User"}])
    mock.get_audit_logs = AsyncMock(return_value=[])
    mock.get_signin_logs = AsyncMock(return_value=[])
    return mock