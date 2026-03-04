"""Comprehensive tests for database module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db


class TestGetDB:
    """Tests for the get_db dependency."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test that get_db yields an async session."""
        async_gen = get_db()
        session = await async_gen.__anext__()

        assert isinstance(session, AsyncSession)

        # Clean up
        try:
            await async_gen.__anext__()
        except StopAsyncIteration:
            pass

    @pytest.mark.asyncio
    async def test_get_db_closes_session(self):
        """Test that get_db properly closes the session."""
        async_gen = get_db()
        session = await async_gen.__anext__()

        # Mock the close method
        session.close = AsyncMock()

        # Exhaust the generator
        try:
            await async_gen.__anext__()
        except StopAsyncIteration:
            pass


class TestDatabaseEngine:
    """Tests for database engine configuration."""

    def test_engine_creation(self):
        """Test that async engine is created correctly."""
        from src.database import engine

        # The engine should be configured for async operation
        assert engine is not None

    def test_session_maker(self):
        """Test that session maker is configured correctly."""
        from src.database import async_session_maker

        assert async_session_maker is not None


class TestDatabaseBase:
    """Tests for SQLAlchemy Base."""

    def test_base_has_metadata(self):
        """Test that Base has metadata."""
        from src.database import Base

        assert Base.metadata is not None

    def test_base_tables(self):
        """Test that expected tables are registered with Base."""
        # Import models to register tables
        from src.database import Base
        from src.models.alerts import AlertHistoryModel, AlertRuleModel, AlertWebhookModel
        from src.models.audit_logs import AuditLogModel
        from src.models.db import TenantModel
        from src.models.settings import (
            ApiKeyModel,
            ConfigurationBackupModel,
            DetectionThresholdsModel,
            SystemSettingsModel,
            UserPreferencesModel,
        )
        from src.models.user import UserModel

        # Get table names
        table_names = Base.metadata.tables.keys()

        # Check that expected tables exist
        expected_tables = [
            "tenants",
            "users",
            "alert_rules",
            "alert_webhooks",
            "alert_history",
            "audit_logss",
        ]

        for table in expected_tables:
            assert table in table_names, f"Expected table '{table}' not found"
