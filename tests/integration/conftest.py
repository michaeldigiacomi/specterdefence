"""Pytest configuration and fixtures for integration tests.

Uses SQLite+aiosqlite for integration testing when PostgreSQL testcontainers
are not available (e.g., in environments without Docker).
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

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
from src.models.audit_log import AuditLogModel, LogType, CollectionStateModel
from src.models.analytics import (
    LoginAnalyticsModel,
    UserLoginHistoryModel,
    AnomalyDetectionConfig,
)
from src.services.encryption import encryption_service


# =============================================================================
# SQLite Database Fixtures (for environments without Docker)
# =============================================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine using SQLite (session-scoped)."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    
    # Create tables
    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(init_tables())
    
    yield engine
    
    # Cleanup
    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    
    asyncio.run(drop_tables())


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test with transaction rollback."""
    # Create a connection that we'll use to wrap in a transaction
    async with db_engine.connect() as conn:
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
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database override."""
    async def override_get_db():
        yield db_session
    
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clean up override
    app.dependency_overrides.clear()


# =============================================================================
# Tenant Fixtures
# =============================================================================

@pytest.fixture
def mock_tenant_create_data():
    """Return sample tenant creation data."""
    return {
        "name": "Integration Test Tenant",
        "tenant_id": "12345678-1234-1234-1234-123456789012",
        "client_id": "87654321-4321-4321-4321-210987654321",
        "client_secret": "test-secret-12345",
    }


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> TenantModel:
    """Create a test tenant in the database."""
    tenant = TenantModel(
        id=str(uuid.uuid4()),
        name="Test Tenant",
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="87654321-4321-4321-4321-210987654321",
        client_secret=encryption_service.encrypt("test-secret-12345"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_tenants(db_session: AsyncSession) -> list[TenantModel]:
    """Create multiple test tenants."""
    tenants = []
    for i in range(3):
        tenant = TenantModel(
            id=str(uuid.uuid4()),
            name=f"Test Tenant {i+1}",
            tenant_id=f"{i+1:08d}-{i+1:04d}-{i+1:04d}-{i+1:04d}-{i+1:012d}",
            client_id=f"{i+10:08d}-{i+10:04d}-{i+10:04d}-{i+10:04d}-{i+10:012d}",
            client_secret=encryption_service.encrypt(f"test-secret-{i}"),
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(tenant)
        tenants.append(tenant)
    
    await db_session.commit()
    for tenant in tenants:
        await db_session.refresh(tenant)
    
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
        ]
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
def mock_o365_management_api():
    """Return mock O365 Management API responses."""
    return {
        "subscriptions_list": [
            {
                "contentType": "Audit.AzureActiveDirectory",
                "status": "enabled",
            }
        ],
        "content_blobs": {
            "contentUri": [
                "https://mock.blob.core.windows.net/audit-logs/blob1.json",
            ],
            "nextPageUri": None,
        },
        "blob_content": [
            {
                "CreationTime": "2026-03-01T10:00:00Z",
                "Id": "audit-log-1",
                "Operation": "UserLoggedIn",
                "Workload": "AzureActiveDirectory",
                "UserId": "john.doe@test.com",
                "ClientIP": "192.168.1.1",
            }
        ],
    }


# =============================================================================
# Audit Log Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_audit_logs(db_session: AsyncSession, test_tenant: TenantModel) -> list[AuditLogModel]:
    """Create test audit logs for a tenant."""
    logs = []
    for i in range(5):
        log = AuditLogModel(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            log_type=LogType.SIGNIN,
            raw_data={
                "CreationTime": f"2026-03-01T{i:02d}:00:00Z",
                "Id": f"audit-log-{i}",
                "Operation": "UserLoggedIn",
                "UserId": f"user{i}@test.com",
                "ClientIP": f"192.168.1.{i+1}",
            },
            processed=False,
        )
        db_session.add(log)
        logs.append(log)
    
    await db_session.commit()
    for log in logs:
        await db_session.refresh(log)
    
    return logs


@pytest_asyncio.fixture
async def test_collection_state(db_session: AsyncSession, test_tenant: TenantModel) -> CollectionStateModel:
    """Create a test collection state for a tenant."""
    state = CollectionStateModel(
        tenant_id=test_tenant.id,
        last_collection_time=datetime.now(timezone.utc),
        total_logs_collected=100,
    )
    db_session.add(state)
    await db_session.commit()
    await db_session.refresh(state)
    return state


# =============================================================================
# Analytics Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_login_analytics(db_session: AsyncSession, test_tenant: TenantModel) -> list[LoginAnalyticsModel]:
    """Create test login analytics records."""
    records = []
    
    # Create a successful login from US
    record1 = LoginAnalyticsModel(
        id=uuid.uuid4(),
        user_email="john.doe@test.com",
        tenant_id=test_tenant.id,
        ip_address="192.168.1.1",
        country="United States",
        country_code="US",
        city="New York",
        region="NY",
        latitude=40.7128,
        longitude=-74.0060,
        login_time=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        is_success=True,
        anomaly_flags=[],
        risk_score=0,
    )
    db_session.add(record1)
    records.append(record1)
    
    # Create an impossible travel login from Japan (30 min later)
    record2 = LoginAnalyticsModel(
        id=uuid.uuid4(),
        user_email="john.doe@test.com",
        tenant_id=test_tenant.id,
        ip_address="203.0.113.1",
        country="Japan",
        country_code="JP",
        city="Tokyo",
        latitude=35.6762,
        longitude=139.6503,
        login_time=datetime(2026, 3, 1, 10, 30, 0, tzinfo=timezone.utc),
        is_success=True,
        anomaly_flags=["impossible_travel"],
        risk_score=95,
    )
    db_session.add(record2)
    records.append(record2)
    
    await db_session.commit()
    for record in records:
        await db_session.refresh(record)
    
    return records


@pytest_asyncio.fixture
async def test_user_login_history(db_session: AsyncSession, test_tenant: TenantModel) -> UserLoginHistoryModel:
    """Create test user login history."""
    history = UserLoginHistoryModel(
        user_email="john.doe@test.com",
        tenant_id=test_tenant.id,
        known_countries=["US"],
        known_ips=["192.168.1.1"],
        last_login_time=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        last_login_country="US",
        last_login_ip="192.168.1.1",
        last_latitude=40.7128,
        last_longitude=-74.0060,
        total_logins=10,
        failed_attempts_24h=0,
    )
    db_session.add(history)
    await db_session.commit()
    await db_session.refresh(history)
    return history


@pytest_asyncio.fixture
async def test_anomaly_config(db_session: AsyncSession, test_tenant: TenantModel) -> AnomalyDetectionConfig:
    """Create test anomaly detection configuration."""
    config = AnomalyDetectionConfig(
        tenant_id=test_tenant.id,
        enabled=True,
        impossible_travel_enabled=True,
        impossible_travel_speed_kmh=900,
        new_country_enabled=True,
        auto_add_known_countries=False,
        risk_score_threshold=70,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


# =============================================================================
# Alert Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_alert_webhook(db_session: AsyncSession) -> AlertWebhookModel:
    """Create a test alert webhook."""
    webhook = AlertWebhookModel(
        id=uuid.uuid4(),
        name="Test Discord Webhook",
        webhook_url=encryption_service.encrypt("https://discord.com/api/webhooks/123456/test-token"),
        webhook_type=WebhookType.DISCORD,
        is_active=True,
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)
    return webhook


@pytest_asyncio.fixture
async def test_alert_rule(db_session: AsyncSession) -> AlertRuleModel:
    """Create a test alert rule."""
    rule = AlertRuleModel(
        id=uuid.uuid4(),
        name="Test Alert Rule",
        event_types=[EventType.IMPOSSIBLE_TRAVEL.value, EventType.NEW_COUNTRY.value],
        min_severity=SeverityLevel.MEDIUM,
        cooldown_minutes=5,
        is_active=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


@pytest_asyncio.fixture
async def test_alert_rule_brute_force(db_session: AsyncSession) -> AlertRuleModel:
    """Create a test alert rule for brute force detection."""
    rule = AlertRuleModel(
        id=uuid.uuid4(),
        name="Brute Force Detection Rule",
        event_types=[EventType.BRUTE_FORCE.value, EventType.MULTIPLE_FAILURES.value],
        min_severity=SeverityLevel.HIGH,
        cooldown_minutes=1,
        is_active=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


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


# =============================================================================
# Security Event Fixtures
# =============================================================================

@pytest.fixture
def impossible_travel_event_data():
    """Return impossible travel event data."""
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
def brute_force_event_data():
    """Return brute force attack event data."""
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


@pytest.fixture
def new_country_event_data():
    """Return new country login event data."""
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


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "database: mark test as requiring database")
