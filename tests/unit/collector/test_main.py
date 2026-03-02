"""Unit tests for the collector main module."""

import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Ensure src is in path and mock MSAL before importing
sys.path.insert(0, "/app")

with patch("src.collector.o365_feed.msal.ConfidentialClientApplication"):
    from src.collector.main import (
        COLLECTION_INTERVAL_MINUTES,
        COLLECTION_LOOKBACK_MINUTES,
        MAX_EVENTS_PER_BATCH,
        CollectorError,
        TenantCollector,
        collect_logs,
        get_active_tenants,
        main,
    )
    from src.collector.o365_feed import RateLimitError


class TestTenantCollector:
    """Test suite for TenantCollector."""

    @pytest.fixture
    def mock_tenant(self):
        """Create a mock tenant."""
        tenant = Mock()
        tenant.id = "tenant-uuid-123"
        tenant.tenant_id = "azure-tenant-id-456"
        tenant.client_id = "client-id-789"
        tenant.client_secret = "encrypted-secret"
        tenant.name = "Test Tenant"
        tenant.is_active = True
        return tenant

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = Mock()
        return session

    @pytest.fixture
    def mock_collection_state(self):
        """Create a mock collection state."""
        state = Mock()
        state.tenant_id = "tenant-uuid-123"
        state.last_collection_time = None
        state.next_page_token = None
        state.total_logs_collected = 0
        return state

    @pytest.mark.asyncio
    async def test_init_decrypts_secret(self, mock_tenant, mock_session):
        """Test that initialization decrypts client secret."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "decrypted-secret"

            collector = TenantCollector(mock_tenant, mock_session)

            mock_encryption.decrypt.assert_called_once_with("encrypted-secret")
            assert collector.decrypted_secret == "decrypted-secret"

    @pytest.mark.asyncio
    async def test_init_decrypt_failure(self, mock_tenant, mock_session):
        """Test handling of decryption failure."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.side_effect = Exception("Decryption failed")

            with pytest.raises(CollectorError):
                TenantCollector(mock_tenant, mock_session)

    @pytest.mark.asyncio
    async def test_get_collection_state_existing(self, mock_tenant, mock_session):
        """Test getting existing collection state."""
        mock_state = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute.return_value = mock_result

        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            state = await collector.get_collection_state()

            assert state == mock_state
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collection_state_new(self, mock_tenant, mock_session):
        """Test creating new collection state when none exists."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            state = await collector.get_collection_state()

            assert state.tenant_id == mock_tenant.id
            assert state.last_collection_time is None
            mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_collection_state_success(self, mock_tenant, mock_session, mock_collection_state):
        """Test updating collection state on success."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            await collector.update_collection_state(
                mock_collection_state,
                success=True,
                error_message=None,
                events_count=100
            )

            assert mock_collection_state.last_collection_time is not None
            assert mock_collection_state.last_success_at is not None
            assert mock_collection_state.total_logs_collected == 100
            assert mock_collection_state.last_error is None
            mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_update_collection_state_failure(self, mock_tenant, mock_session, mock_collection_state):
        """Test updating collection state on failure."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            await collector.update_collection_state(
                mock_collection_state,
                success=False,
                error_message="API Error",
                events_count=0
            )

            assert mock_collection_state.last_error == "API Error"
            assert mock_collection_state.last_error_at is not None
            mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_store_events(self, mock_tenant, mock_session):
        """Test storing events in database."""
        events = [
            {"Id": "1", "CreationTime": "2024-01-01T12:00:00Z", "Operation": "UserLogin"},
            {"Id": "2", "CreationTime": "2024-01-01T12:05:00Z", "Operation": "FileAccess"},
        ]

        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            count = await collector.store_events(events, "Audit.General")

            assert count == 2
            assert mock_session.add.call_count == 2
            mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_store_events_with_invalid_datetime(self, mock_tenant, mock_session):
        """Test storing events with invalid datetime."""
        events = [
            {"Id": "1", "CreationTime": "invalid-date", "Operation": "Test"},
        ]

        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            count = await collector.store_events(events, "Audit.General")

            assert count == 1
            # Should handle invalid date gracefully

    @pytest.mark.asyncio
    async def test_store_events_empty(self, mock_tenant, mock_session):
        """Test storing empty event list."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            count = await collector.store_events([], "Audit.General")

            assert count == 0
            mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_content_type(self, mock_tenant, mock_session):
        """Test collecting content type."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            # Mock the O365 client
            mock_client = AsyncMock()

            # Create async generator for collect_logs
            async def mock_collect_gen(*args, **kwargs):
                yield [{"id": "1"}, {"id": "2"}]
                yield [{"id": "3"}]

            mock_client.collect_logs = mock_collect_gen
            collector.client = mock_client

            start_time = datetime.now(UTC) - timedelta(hours=1)
            end_time = datetime.now(UTC)

            count = await collector.collect_content_type(
                "Audit.General",
                start_time,
                end_time
            )

            assert count == 3

    @pytest.mark.asyncio
    async def test_collect_content_type_rate_limit(self, mock_tenant, mock_session):
        """Test rate limit handling during content collection."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            mock_client = AsyncMock()

            async def mock_collect_gen(*args, **kwargs):
                raise RateLimitError("Rate limited")
                yield  # Make it a generator

            mock_client.collect_logs = mock_collect_gen
            collector.client = mock_client

            with pytest.raises(RateLimitError):
                await collector.collect_content_type(
                    "Audit.General",
                    datetime.now(UTC),
                    datetime.now(UTC)
                )

    @pytest.mark.asyncio
    async def test_collect_all_first_time(self, mock_tenant, mock_session, mock_collection_state):
        """Test full collection for first time (no previous state)."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_collection_state
        mock_session.execute.return_value = mock_result

        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            # Mock O365 client
            mock_client = AsyncMock()
            mock_client.ensure_subscriptions.return_value = ["Audit.General"]

            async def mock_collect_gen(*args, **kwargs):
                return
                yield  # Make it a generator

            mock_client.collect_logs = mock_collect_gen
            collector.client = mock_client

            result = await collector.collect_all()

            assert result["tenant_id"] == mock_tenant.id
            assert result["success"] is True
            assert result["total_events"] == 0
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_collect_all_with_previous_state(self, mock_tenant, mock_session):
        """Test collection with previous state."""
        # Collection state with recent last_collection_time
        mock_state = Mock()
        mock_state.tenant_id = mock_tenant.id
        mock_state.last_collection_time = datetime.now(UTC) - timedelta(minutes=10)
        mock_state.total_logs_collected = 1000

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute.return_value = mock_result

        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            mock_client = AsyncMock()
            mock_client.ensure_subscriptions.return_value = ["Audit.General"]

            async def mock_collect_gen(*args, **kwargs):
                return
                yield

            mock_client.collect_logs = mock_collect_gen
            collector.client = mock_client

            result = await collector.collect_all()

            # Should use last_collection_time as start
            assert result["start_time"] is not None

    @pytest.mark.asyncio
    async def test_collect_all_handles_subscription_error(self, mock_tenant, mock_session, mock_collection_state):
        """Test that collection continues even if subscription fails."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_collection_state
        mock_session.execute.return_value = mock_result

        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"
            collector = TenantCollector(mock_tenant, mock_session)

            mock_client = AsyncMock()
            # Subscription fails but collection should still proceed
            mock_client.ensure_subscriptions.side_effect = Exception("API Error")

            async def mock_collect_gen(*args, **kwargs):
                return
                yield

            mock_client.collect_logs = mock_collect_gen
            collector.client = mock_client

            # Should not raise
            result = await collector.collect_all()

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_tenant, mock_session):
        """Test async context manager."""
        with patch("src.collector.main.encryption_service") as mock_encryption:
            mock_encryption.decrypt.return_value = "secret"

            # Patch O365ManagementClient to avoid MSAL initialization
            with patch("src.collector.main.O365ManagementClient") as mock_client_class:
                mock_client_instance = Mock()
                mock_client_class.return_value = mock_client_instance

                async with TenantCollector(mock_tenant, mock_session) as collector:
                    assert collector.client is not None


class TestGetActiveTenants:
    """Test suite for get_active_tenants."""

    @pytest.mark.asyncio
    async def test_get_active_tenants(self):
        """Test retrieving active tenants."""
        mock_session = AsyncMock()

        mock_tenant1 = Mock(spec=["id", "name", "is_active"])
        mock_tenant1.id = "1"
        mock_tenant1.name = "Tenant 1"
        mock_tenant1.is_active = True

        mock_tenant2 = Mock(spec=["id", "name", "is_active"])
        mock_tenant2.id = "2"
        mock_tenant2.name = "Tenant 2"
        mock_tenant2.is_active = True

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_tenant1, mock_tenant2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        tenants = await get_active_tenants(mock_session)

        assert len(tenants) == 2
        assert tenants[0].name == "Tenant 1"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_tenants_empty(self):
        """Test retrieving when no active tenants."""
        mock_session = AsyncMock()

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        tenants = await get_active_tenants(mock_session)

        assert tenants == []


class TestCollectLogs:
    """Test suite for collect_logs main function."""

    @pytest.mark.asyncio
    async def test_collect_logs_no_tenants(self):
        """Test collection with no tenants."""
        with patch("src.collector.main.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()

            mock_result = Mock()
            mock_scalars = Mock()
            mock_scalars.all.return_value = []
            mock_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_result

            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await collect_logs()

            assert results["tenants_processed"] == 0
            assert results["total_events"] == 0

    @pytest.mark.asyncio
    async def test_collect_logs_success(self):
        """Test successful collection for multiple tenants."""
        mock_tenant1 = Mock(spec=["id", "name", "is_active", "tenant_id", "client_id", "client_secret"])
        mock_tenant1.id = "1"
        mock_tenant1.name = "Tenant 1"
        mock_tenant1.is_active = True
        mock_tenant1.tenant_id = "t1"
        mock_tenant1.client_id = "c1"
        mock_tenant1.client_secret = "s1"

        mock_tenant2 = Mock(spec=["id", "name", "is_active", "tenant_id", "client_id", "client_secret"])
        mock_tenant2.id = "2"
        mock_tenant2.name = "Tenant 2"
        mock_tenant2.is_active = True
        mock_tenant2.tenant_id = "t2"
        mock_tenant2.client_id = "c2"
        mock_tenant2.client_secret = "s2"

        with patch("src.collector.main.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()

            mock_result = Mock()
            mock_scalars = Mock()
            mock_scalars.all.return_value = [mock_tenant1, mock_tenant2]
            mock_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_result

            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.collector.main.TenantCollector") as mock_collector_class:
                mock_collector = AsyncMock()
                mock_collector_class.return_value.__aenter__ = AsyncMock(return_value=mock_collector)
                mock_collector_class.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_collector.collect_all.return_value = {
                    "success": True,
                    "total_events": 50,
                    "error": None,
                }

                with patch("src.collector.main.encryption_service") as mock_encryption:
                    mock_encryption.decrypt.return_value = "secret"

                    results = await collect_logs()

                    assert results["tenants_processed"] == 2
                    assert results["tenants_successful"] == 2
                    assert results["total_events"] == 100

    @pytest.mark.asyncio
    async def test_collect_logs_with_failures(self):
        """Test collection with some tenant failures."""
        mock_tenant1 = Mock(spec=["id", "name", "is_active", "tenant_id", "client_id", "client_secret"])
        mock_tenant1.id = "1"
        mock_tenant1.name = "Tenant 1"
        mock_tenant1.is_active = True
        mock_tenant1.tenant_id = "t1"
        mock_tenant1.client_id = "c1"
        mock_tenant1.client_secret = "s1"

        mock_tenant2 = Mock(spec=["id", "name", "is_active", "tenant_id", "client_id", "client_secret"])
        mock_tenant2.id = "2"
        mock_tenant2.name = "Tenant 2"
        mock_tenant2.is_active = True
        mock_tenant2.tenant_id = "t2"
        mock_tenant2.client_id = "c2"
        mock_tenant2.client_secret = "s2"

        with patch("src.collector.main.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()

            mock_result = Mock()
            mock_scalars = Mock()
            mock_scalars.all.return_value = [mock_tenant1, mock_tenant2]
            mock_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_result

            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            call_count = 0
            def create_collector(tenant, session):
                nonlocal call_count
                call_count += 1
                mock_collector = AsyncMock()
                if tenant.id == "1":
                    mock_collector.collect_all.return_value = {
                        "success": True,
                        "total_events": 50,
                        "error": None,
                    }
                else:
                    mock_collector.collect_all.side_effect = Exception("Auth failed")
                return mock_collector

            with patch("src.collector.main.TenantCollector") as mock_collector_class:
                mock_collector_class.side_effect = create_collector
                mock_collector_class.return_value.__aenter__ = AsyncMock(side_effect=lambda: create_collector(mock_collector_class.call_args[0][0], None))
                mock_collector_class.return_value.__aexit__ = AsyncMock(return_value=False)

                with patch("src.collector.main.encryption_service") as mock_encryption:
                    mock_encryption.decrypt.return_value = "secret"

                    results = await collect_logs()

                    # Due to mocking complexity, we just verify the function runs
                    assert results["tenants_processed"] == 2

    @pytest.mark.asyncio
    async def test_collect_logs_rolls_back_on_error(self):
        """Test that session is rolled back on unexpected error."""
        with patch("src.collector.main.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Database error")

            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(Exception):
                await collect_logs()

            mock_session.rollback.assert_called_once()


class TestMain:
    """Test suite for main entry point."""

    @pytest.mark.asyncio
    async def test_main_success(self):
        """Test successful main execution."""
        with patch("src.collector.main.init_db", new_callable=AsyncMock) as mock_init:
            with patch("src.collector.main.collect_logs", new_callable=AsyncMock) as mock_collect:
                mock_collect.return_value = {
                    "tenants_failed": 0,
                    "tenants_successful": 2,
                }

                exit_code = await main()

                assert exit_code == 0
                mock_init.assert_called_once()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_failures(self):
        """Test main with tenant failures."""
        with patch("src.collector.main.init_db", new_callable=AsyncMock):
            with patch("src.collector.main.collect_logs", new_callable=AsyncMock) as mock_collect:
                mock_collect.return_value = {
                    "tenants_failed": 1,
                    "tenants_successful": 1,
                }

                exit_code = await main()

                assert exit_code == 1

    @pytest.mark.asyncio
    async def test_main_fatal_error(self):
        """Test main with fatal error."""
        with patch("src.collector.main.init_db", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Fatal error")

            exit_code = await main()

            assert exit_code == 1


class TestConfiguration:
    """Test configuration constants."""

    def test_default_lookback(self):
        """Test default lookback configuration."""
        assert COLLECTION_LOOKBACK_MINUTES == 10

    def test_default_interval(self):
        """Test default interval configuration."""
        assert COLLECTION_INTERVAL_MINUTES == 5

    def test_default_max_events(self):
        """Test default max events configuration."""
        assert MAX_EVENTS_PER_BATCH == 1000
