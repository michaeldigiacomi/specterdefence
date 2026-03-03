"""Integration tests for log collection flow.

Tests the end-to-end flow from O365 Management API to database storage,
including collection state updates and audit log processing.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from src.collector.main import TenantCollector, get_active_tenants
from src.collector.o365_feed import O365ManagementClient
from src.models.audit_log import AuditLogModel, CollectionStateModel, LogType
from src.models.db import TenantModel

pytestmark = pytest.mark.integration


class TestLogCollectionFlow:
    """Test full log collection flow with mocked O365 API."""

    @patch("src.collector.main.O365ManagementClient")
    async def test_tenant_collector_initialization(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test that TenantCollector initializes correctly with decrypted credentials."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.tenant_id = test_tenant.tenant_id
        mock_client_class.return_value = mock_client

        collector = TenantCollector(test_tenant, db_session)

        # Verify client secret is decrypted
        assert collector.decrypted_secret == "test-secret-12345"
        assert collector.tenant.id == test_tenant.id

        # Test context manager
        async with TenantCollector(test_tenant, db_session) as collector_ctx:
            assert collector_ctx.client is not None
            assert collector_ctx.client.tenant_id == test_tenant.tenant_id

    @patch("src.collector.main.O365ManagementClient")
    async def test_collection_state_created_on_first_run(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test that collection state is created on first collection run."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        async with TenantCollector(test_tenant, db_session) as collector:
            state = await collector.get_collection_state()

            assert state is not None
            assert state.tenant_id == test_tenant.id
            assert state.last_collection_time is None
            assert state.total_logs_collected == 0

    @patch("src.collector.main.O365ManagementClient")
    async def test_collection_state_retrieved_existing(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test that existing collection state is retrieved correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create an existing collection state
        existing_state = CollectionStateModel(
            tenant_id=test_tenant.id,
            last_collection_time=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
            total_logs_collected=500,
        )
        db_session.add(existing_state)
        await db_session.commit()

        async with TenantCollector(test_tenant, db_session) as collector:
            state = await collector.get_collection_state()

            assert state.tenant_id == test_tenant.id
            assert state.total_logs_collected == 500
            assert state.last_collection_time is not None

    @patch("src.collector.main.O365ManagementClient")
    async def test_store_events_in_database(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test that events are stored correctly in the database."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        test_events = [
            {
                "CreationTime": "2026-03-01T10:00:00Z",
                "Id": "event-1",
                "Operation": "UserLoggedIn",
                "UserId": "user1@test.com",
                "ClientIP": "192.168.1.1",
            },
            {
                "CreationTime": "2026-03-01T11:00:00Z",
                "Id": "event-2",
                "Operation": "UserLoggedIn",
                "UserId": "user2@test.com",
                "ClientIP": "192.168.1.2",
            },
        ]

        async with TenantCollector(test_tenant, db_session) as collector:
            stored_count = await collector.store_events(test_events, "Audit.AzureActiveDirectory")
            await db_session.commit()

        assert stored_count == 2

        # Verify records in database
        result = await db_session.execute(
            select(AuditLogModel).where(AuditLogModel.tenant_id == test_tenant.id)
        )
        logs = result.scalars().all()
        assert len(logs) == 2

        # Verify log type
        assert logs[0].log_type == LogType.SIGNIN
        assert logs[0].raw_data["Id"] == "event-1"
        assert not logs[0].processed

    @patch("src.collector.main.O365ManagementClient")
    async def test_store_events_with_different_content_types(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test that different content types are mapped to correct log types."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        test_event = {
            "CreationTime": "2026-03-01T10:00:00Z",
            "Id": "event-1",
            "Operation": "FileAccessed",
        }

        async with TenantCollector(test_tenant, db_session) as collector:
            # Test Azure AD content type
            await collector.store_events([test_event], "Audit.AzureActiveDirectory")

            # Test Exchange content type
            await collector.store_events([test_event], "Audit.Exchange")

            # Test SharePoint content type
            await collector.store_events([test_event], "Audit.SharePoint")

            await db_session.commit()

        # Verify records
        result = await db_session.execute(
            select(AuditLogModel).where(AuditLogModel.tenant_id == test_tenant.id)
        )
        logs = result.scalars().all()
        assert len(logs) == 3

        # All should be audit_general except Azure AD
        assert logs[0].log_type == LogType.SIGNIN
        assert logs[1].log_type == LogType.AUDIT_GENERAL
        assert logs[2].log_type == LogType.AUDIT_GENERAL

    @patch("src.collector.main.O365ManagementClient")
    async def test_update_collection_state_success(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test successful collection state update."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        async with TenantCollector(test_tenant, db_session) as collector:
            state = await collector.get_collection_state()

            await collector.update_collection_state(
                state=state,
                success=True,
                error_message=None,
                events_count=100
            )
            await db_session.commit()

        # Verify state was updated
        result = await db_session.execute(
            select(CollectionStateModel).where(CollectionStateModel.tenant_id == test_tenant.id)
        )
        updated_state = result.scalar_one()

        assert updated_state.total_logs_collected == 100
        assert updated_state.last_success_at is not None
        assert updated_state.last_error is None
        assert updated_state.last_collection_time is not None

    @patch("src.collector.main.O365ManagementClient")
    async def test_update_collection_state_failure(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test collection state update on failure."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        async with TenantCollector(test_tenant, db_session) as collector:
            state = await collector.get_collection_state()

            await collector.update_collection_state(
                state=state,
                success=False,
                error_message="Rate limit exceeded",
                events_count=0
            )
            await db_session.commit()

        # Verify state reflects failure
        result = await db_session.execute(
            select(CollectionStateModel).where(CollectionStateModel.tenant_id == test_tenant.id)
        )
        updated_state = result.scalar_one()

        assert updated_state.last_error == "Rate limit exceeded"
        assert updated_state.last_error_at is not None
        assert updated_state.total_logs_collected == 0

    @patch("src.collector.main.O365ManagementClient")
    async def test_collect_all_with_mocked_client(self, mock_client_class, test_tenant: TenantModel, db_session):
        """Test full collection with mocked O365 Management client."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock collect_logs to return test events
        async def mock_collect_logs(*args, **kwargs):
            yield [
                {
                    "CreationTime": "2026-03-01T10:00:00Z",
                    "Id": "audit-1",
                    "Operation": "UserLoggedIn",
                    "UserId": "user@test.com",
                    "ClientIP": "192.168.1.1",
                }
            ]

        mock_client.collect_logs = mock_collect_logs
        mock_client.ensure_subscriptions = AsyncMock(return_value=["Audit.AzureActiveDirectory"])

        async with TenantCollector(test_tenant, db_session) as collector:
            result = await collector.collect_all()

        assert result["tenant_id"] == test_tenant.id
        assert result["success"] is True
        assert result["total_events"] >= 0
        assert "Audit.AzureActiveDirectory" in result["content_types"]

    @patch("src.collector.main.O365ManagementClient")
    async def test_get_active_tenants(self, mock_client_class, test_tenants: list[TenantModel], db_session):
        """Test retrieving active tenants."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Deactivate one tenant
        test_tenants[0].is_active = False
        await db_session.commit()

        active_tenants = await get_active_tenants(db_session)

        # Should return only active tenants
        assert len(active_tenants) == 2
        assert all(t.is_active for t in active_tenants)
        assert test_tenants[0].id not in [t.id for t in active_tenants]


class TestO365ManagementClient:
    """Test O365 Management API client with mocked HTTP responses."""

    @patch("src.collector.o365_feed.msal.ConfidentialClientApplication")
    async def test_client_authentication(self, mock_msal_class, mock_msal_app):
        """Test that client authenticates correctly."""
        mock_msal_class.return_value = mock_msal_app

        client = O365ManagementClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
        )

        token = await client._get_access_token()

        assert token == "mock-access-token-12345"
        mock_msal_app.acquire_token_for_client.assert_called_once()

    @patch("src.collector.o365_feed.msal.ConfidentialClientApplication")
    @patch("httpx.AsyncClient")
    async def test_list_subscriptions(self, mock_http_client, mock_msal_class, mock_msal_app):
        """Test listing subscriptions."""
        mock_msal_class.return_value = mock_msal_app

        # Setup mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"contentType": "Audit.AzureActiveDirectory", "status": "enabled"},
            {"contentType": "Audit.Exchange", "status": "enabled"},
        ]
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_http_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http_client.return_value.__aexit__ = AsyncMock(return_value=None)

        client = O365ManagementClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
        )

        subscriptions = await client.list_subscriptions()

        assert len(subscriptions) == 2
        assert subscriptions[0]["contentType"] == "Audit.AzureActiveDirectory"

    @patch("src.collector.o365_feed.msal.ConfidentialClientApplication")
    @patch("httpx.AsyncClient")
    async def test_get_content_blobs(self, mock_http_client, mock_msal_class, mock_msal_app):
        """Test retrieving content blobs."""
        mock_msal_class.return_value = mock_msal_app

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "contentUri": [
                "https://mock.blob.core.windows.net/audit-logs/blob1.json",
                "https://mock.blob.core.windows.net/audit-logs/blob2.json",
            ],
            "nextPageUri": None,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_http_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http_client.return_value.__aexit__ = AsyncMock(return_value=None)

        client = O365ManagementClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
        )

        result = await client.get_content_blobs(
            content_type="Audit.AzureActiveDirectory",
            start_time=datetime(2026, 3, 1, 0, 0, 0),
            end_time=datetime(2026, 3, 1, 23, 59, 59),
        )

        assert "contentUri" in result
        assert len(result["contentUri"]) == 2

    @patch("src.collector.o365_feed.msal.ConfidentialClientApplication")
    @patch("httpx.AsyncClient")
    async def test_download_content(self, mock_http_client, mock_msal_class, mock_msal_app):
        """Test downloading content from blob URL."""
        mock_msal_class.return_value = mock_msal_app

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '{"Id": "event-1", "Operation": "UserLoggedIn"}\n'
            '{"Id": "event-2", "Operation": "UserLoggedIn"}'
        )
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http_client.return_value.__aexit__ = AsyncMock(return_value=None)

        client = O365ManagementClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-secret",
        )

        events = await client.download_content("https://mock.blob.core.windows.net/audit-logs/blob.json")

        assert len(events) == 2
        assert events[0]["Id"] == "event-1"
        assert events[1]["Id"] == "event-2"


class TestDataPersistence:
    """Test data persistence and retrieval from PostgreSQL."""

    async def test_audit_log_persistence(self, test_tenant: TenantModel, db_session):
        """Test that audit logs are persisted correctly."""
        audit_log = AuditLogModel(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            log_type=LogType.SIGNIN,
            raw_data={
                "Id": "test-audit-1",
                "UserId": "test@example.com",
                "Operation": "UserLoggedIn",
            },
            processed=False,
        )

        db_session.add(audit_log)
        await db_session.commit()

        # Retrieve from database
        result = await db_session.execute(
            select(AuditLogModel).where(AuditLogModel.id == audit_log.id)
        )
        retrieved = result.scalar_one()

        assert retrieved.tenant_id == test_tenant.id
        assert retrieved.raw_data["UserId"] == "test@example.com"
        assert retrieved.processed is False

    async def test_collection_state_persistence(self, test_tenant: TenantModel, db_session):
        """Test that collection state is persisted correctly."""
        state = CollectionStateModel(
            tenant_id=test_tenant.id,
            last_collection_time=datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
            total_logs_collected=1000,
            last_success_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
        )

        db_session.add(state)
        await db_session.commit()

        # Retrieve and verify
        result = await db_session.execute(
            select(CollectionStateModel).where(CollectionStateModel.tenant_id == test_tenant.id)
        )
        retrieved = result.scalar_one()

        assert retrieved.total_logs_collected == 1000
        assert retrieved.last_collection_time is not None

    async def test_audit_log_jsonb_storage(self, test_tenant: TenantModel, db_session):
        """Test that JSONB data is stored and retrieved correctly."""
        complex_data = {
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"},
            },
            "timestamp": "2026-03-01T12:00:00Z",
            "boolean": True,
            "null_value": None,
        }

        audit_log = AuditLogModel(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            log_type=LogType.AUDIT_GENERAL,
            raw_data=complex_data,
            processed=True,
        )

        db_session.add(audit_log)
        await db_session.commit()

        # Retrieve and verify JSONB structure
        result = await db_session.execute(
            select(AuditLogModel).where(AuditLogModel.id == audit_log.id)
        )
        retrieved = result.scalar_one()

        assert retrieved.raw_data["nested"]["array"] == [1, 2, 3]
        assert retrieved.raw_data["nested"]["object"]["key"] == "value"
        assert retrieved.raw_data["boolean"] is True
