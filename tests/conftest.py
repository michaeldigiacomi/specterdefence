"""Pytest configuration and shared fixtures for SpecterDefence tests."""

import asyncio
import os
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Set testing environment variables before importing app
os.environ['TESTING'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-32-chars-long-for-testing'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key-32-chars-for-testing'
os.environ['ADMIN_PASSWORD_HASH'] = '$2b$12$qaI.IhS84lIGdfXRFU8aZOhLqJqsZbhJt1UFx8rWSjzlHynm53.kK'  # Default: "admin123"
os.environ['ENCRYPTION_KEY'] = 'test-encryption-key-32-chars-for-tests='
os.environ['ENCRYPTION_SALT'] = 'test-salt-for-encryption-32chars'

from src.database import Base, get_db
from src.main import app
from src.models.db import TenantModel
from src.models.tenant import TenantCreate, TenantResponse
from src.models.alerts import (
    SeverityLevel,
    EventType,
    AlertWebhookModel,
    AlertRuleModel,
    WebhookType,
)


# =============================================================================
# Database Fixtures
# =============================================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine (function-scoped to avoid scope mismatch)."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine):
    """Create a fresh database session for each test."""
    # Create a connection that we'll use to wrap in a transaction
    async with test_engine.connect() as conn:
        # Begin a transaction
        trans = await conn.begin()
        
        # Create a session bound to the connection
        async_session = async_sessionmaker(
            conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        
        async with async_session() as session:
            yield session
        
        # Rollback the transaction after the test
        await trans.rollback()


@pytest_asyncio.fixture
async def db_session(test_db) -> AsyncSession:
    """Alias for test_db fixture."""
    return test_db


@pytest_asyncio.fixture
async def async_db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Async database session fixture with proper typing."""
    yield test_db


# =============================================================================
# FastAPI Test Client Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database override."""
    from httpx import ASGITransport
    
    async def override_get_db():
        yield test_db
    
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clean up override
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Alias for test_client fixture."""
    from httpx import ASGITransport
    
    async def override_get_db():
        yield test_db
    
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clean up override
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def sync_test_client() -> Generator[TestClient, None, None]:
    """Create a synchronous test client."""
    with TestClient(app) as client:
        yield client


# =============================================================================
# Tenant Fixtures
# =============================================================================

@pytest.fixture
def mock_tenant_data():
    """Return sample tenant data for testing."""
    return {
        "name": "Test Tenant",
        "tenant_id": "12345678-1234-1234-1234-123456789012",
        "client_id": "87654321-4321-4321-4321-210987654321",
        "client_secret": "test-secret-12345",
    }


@pytest.fixture
def mock_tenant_create():
    """Return a TenantCreate model instance."""
    return TenantCreate(
        name="Test Tenant",
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="87654321-4321-4321-4321-210987654321",
        client_secret="test-secret-12345",
    )


@pytest_asyncio.fixture
async def sample_tenant(test_db) -> TenantModel:
    """Create a sample tenant in the database."""
    tenant = TenantModel(
        id=str(uuid.uuid4()),
        name="Sample Tenant",
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="87654321-4321-4321-4321-210987654321",
        client_secret="encrypted-secret-placeholder",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def sample_tenants(test_db) -> list[TenantModel]:
    """Create multiple sample tenants."""
    tenants = []
    for i in range(3):
        tenant = TenantModel(
            id=str(uuid.uuid4()),
            name=f"Sample Tenant {i+1}",
            tenant_id=f"{i+1:08d}-{i+1:04d}-{i+1:04d}-{i+1:04d}-{i+1:012d}",
            client_id=f"{i+10:08d}-{i+10:04d}-{i+10:04d}-{i+10:04d}-{i+10:012d}",
            client_secret=f"encrypted-secret-{i}",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_db.add(tenant)
        tenants.append(tenant)
    
    await test_db.commit()
    for tenant in tenants:
        await test_db.refresh(tenant)
    
    return tenants


# =============================================================================
# MS Graph API Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_ms_graph_token():
    """Return a mock MS Graph access token."""
    return "mock-access-token-12345"


@pytest.fixture
def mock_o365_organization_response():
    """Return a mock Microsoft Graph organization response."""
    return {
        "value": [{
            "id": "12345678-1234-1234-1234-123456789012",
            "displayName": "Test Organization",
            "verifiedDomains": [
                {"name": "test.com", "isDefault": True, "isInitial": False},
                {"name": "test.onmicrosoft.com", "isDefault": False, "isInitial": True},
            ],
            "createdDateTime": "2020-01-01T00:00:00Z",
            "tenantType": "AAD",
        }]
    }


@pytest.fixture
def mock_o365_users_response():
    """Return a mock Microsoft Graph users response."""
    return {
        "value": [
            {
                "id": "user-1-id",
                "displayName": "John Doe",
                "userPrincipalName": "john.doe@test.com",
                "mail": "john.doe@test.com",
                "createdDateTime": "2020-01-01T00:00:00Z",
            },
            {
                "id": "user-2-id",
                "displayName": "Jane Smith",
                "userPrincipalName": "jane.smith@test.com",
                "mail": "jane.smith@test.com",
                "createdDateTime": "2020-06-01T00:00:00Z",
            },
        ],
        "@odata.nextLink": None,
    }


@pytest.fixture
def mock_o365_signins_response():
    """Return a mock Microsoft Graph sign-in logs response."""
    return {
        "value": [
            {
                "id": "signin-1",
                "createdDateTime": "2026-03-01T10:00:00Z",
                "userPrincipalName": "john.doe@test.com",
                "userId": "user-1-id",
                "appDisplayName": "Office 365",
                "ipAddress": "192.168.1.1",
                "location": {
                    "city": "New York",
                    "state": "NY",
                    "countryOrRegion": "US",
                    "geoCoordinates": {"latitude": 40.7128, "longitude": -74.0060},
                },
                "status": {"errorCode": 0, "failureReason": None},
                "clientAppUsed": "Browser",
            },
            {
                "id": "signin-2",
                "createdDateTime": "2026-03-01T09:00:00Z",
                "userPrincipalName": "john.doe@test.com",
                "userId": "user-1-id",
                "appDisplayName": "Office 365",
                "ipAddress": "203.0.113.1",
                "location": {
                    "city": "Tokyo",
                    "countryOrRegion": "JP",
                    "geoCoordinates": {"latitude": 35.6762, "longitude": 139.6503},
                },
                "status": {"errorCode": 0, "failureReason": None},
                "clientAppUsed": "Mobile App",
            },
        ]
    }


@pytest.fixture
def mock_msal_app(mock_ms_graph_token):
    """Return a mock MSAL ConfidentialClientApplication."""
    mock_app = MagicMock()
    mock_app.acquire_token_silent.return_value = None
    mock_app.acquire_token_for_client.return_value = {
        "access_token": mock_ms_graph_token,
        "expires_in": 3600,
    }
    return mock_app


@pytest.fixture
def mock_ms_graph_client(mock_msal_app):
    """Return a mock MSGraphClient instance."""
    with patch("src.clients.ms_graph.msal.ConfidentialClientApplication") as mock_msal_class:
        mock_msal_class.return_value = mock_msal_app
        
        from src.clients.ms_graph import MSGraphClient
        client = MSGraphClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-client-secret",
        )
        yield client


# =============================================================================
# Discord Webhook Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_discord_webhook_url():
    """Return a mock Discord webhook URL."""
    return "https://discord.com/api/webhooks/123456789/test-webhook-token"


@pytest.fixture
def mock_discord_webhook_response():
    """Return a mock Discord webhook success response."""
    return {"id": "123456789", "type": 1, "channel_id": "123456789"}


@pytest_asyncio.fixture
async def sample_webhook(test_db) -> AlertWebhookModel:
    """Create a sample alert webhook in the database."""
    webhook = AlertWebhookModel(
        id=uuid.uuid4(),
        name="Test Webhook",
        webhook_url="encrypted-webhook-url",
        webhook_type=WebhookType.DISCORD,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    test_db.add(webhook)
    await test_db.commit()
    await test_db.refresh(webhook)
    return webhook


@pytest_asyncio.fixture
async def sample_alert_rule(test_db) -> AlertRuleModel:
    """Create a sample alert rule in the database."""
    rule = AlertRuleModel(
        id=uuid.uuid4(),
        name="Test Alert Rule",
        event_types=[EventType.IMPOSSIBLE_TRAVEL, EventType.NEW_COUNTRY],
        min_severity=SeverityLevel.MEDIUM,
        cooldown_minutes=30,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(rule)
    await test_db.commit()
    await test_db.refresh(rule)
    return rule


# =============================================================================
# Event and Alert Fixtures
# =============================================================================

@pytest.fixture
def mock_impossible_travel_event():
    """Return a mock impossible travel event."""
    return {
        "event_type": EventType.IMPOSSIBLE_TRAVEL,
        "user_email": "john.doe@test.com",
        "severity": SeverityLevel.HIGH,
        "title": "Impossible Travel Detected",
        "description": "User login from physically impossible locations",
        "metadata": {
            "previous_location": {
                "city": "New York",
                "country": "US",
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
            "current_location": {
                "city": "Tokyo",
                "country": "JP",
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
            "distance_km": 10847,
            "time_diff_minutes": 30,
            "min_travel_time_minutes": 800,
            "risk_score": 95,
        },
    }


@pytest.fixture
def mock_new_country_event():
    """Return a mock new country login event."""
    return {
        "event_type": EventType.NEW_COUNTRY,
        "user_email": "jane.smith@test.com",
        "severity": SeverityLevel.MEDIUM,
        "title": "New Country Login",
        "description": "User logged in from a new country",
        "metadata": {
            "country_code": "FR",
            "country_name": "France",
            "city": "Paris",
            "known_countries": ["US", "GB"],
            "is_first_login": False,
            "ip_address": "203.0.113.50",
        },
    }


@pytest.fixture
def mock_brute_force_event():
    """Return a mock brute force attack event."""
    return {
        "event_type": EventType.BRUTE_FORCE,
        "user_email": "admin@test.com",
        "severity": SeverityLevel.CRITICAL,
        "title": "Brute Force Attack Detected",
        "description": "Multiple failed login attempts detected",
        "metadata": {
            "recent_failures": 10,
            "failure_reason": "Invalid password",
            "ip_address": "198.51.100.1",
            "time_window_minutes": 15,
        },
    }


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def freezer():
    """Fixture to freeze time for tests."""
    from datetime import datetime, timezone
    frozen_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    with patch("src.models.alerts.utc_now") as mock_utc_now:
        mock_utc_now.return_value = frozen_time
        yield frozen_time


@pytest.fixture
def mock_httpx_client():
    """Return a mock httpx.AsyncClient."""
    mock_client = AsyncMock(spec=AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    return mock_client


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "database: mark test as requiring database")
