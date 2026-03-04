"""Comprehensive tests for the Settings API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.models.settings import (
    ApiKeyModel,
    ConfigurationBackupModel,
    DetectionThresholdsModel,
    SystemSettingsModel,
    UserPreferencesModel,
)


class TestSystemSettingsAPI:
    """Tests for system settings endpoints."""

    async def test_get_system_settings(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/system."""
        # Create system settings first
        settings = SystemSettingsModel(
            audit_log_retention_days=90,
            login_history_retention_days=30,
            alert_history_retention_days=365,
            auto_cleanup_enabled=True,
            cleanup_schedule="0 2 * * *",
            api_rate_limit=1000,
            max_export_rows=10000,
            log_level="INFO",
        )
        test_db.add(settings)
        await test_db.commit()

        response = await async_client.get("/api/v1/settings/system")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["audit_log_retention_days"] == 90
        assert data["log_level"] == "INFO"
        assert data["auto_cleanup_enabled"] is True

    async def test_update_system_settings(self, async_client: AsyncClient, test_db):
        """Test PATCH /api/v1/settings/system."""
        # Create initial settings
        settings = SystemSettingsModel(
            audit_log_retention_days=90,
            login_history_retention_days=30,
            alert_history_retention_days=365,
            auto_cleanup_enabled=True,
            cleanup_schedule="0 2 * * *",
            api_rate_limit=1000,
            max_export_rows=10000,
            log_level="INFO",
        )
        test_db.add(settings)
        await test_db.commit()

        update_data = {
            "audit_log_retention_days": 180,
            "log_level": "DEBUG",
            "api_rate_limit": 2000,
        }

        response = await async_client.patch("/api/v1/settings/system", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["audit_log_retention_days"] == 180
        assert data["log_level"] == "DEBUG"
        assert data["api_rate_limit"] == 2000

    async def test_update_system_settings_validation_error(self, async_client: AsyncClient, test_db):
        """Test PATCH /api/v1/settings/system with invalid data."""
        # Create initial settings
        settings = SystemSettingsModel(
            audit_log_retention_days=90,
            login_history_retention_days=30,
            alert_history_retention_days=365,
            auto_cleanup_enabled=True,
            cleanup_schedule="0 2 * * *",
            api_rate_limit=1000,
            max_export_rows=10000,
            log_level="INFO",
        )
        test_db.add(settings)
        await test_db.commit()

        # Invalid log level
        update_data = {"log_level": "INVALID"}

        response = await async_client.patch("/api/v1/settings/system", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_system_settings_default_creation(self, async_client: AsyncClient):
        """Test that default settings are created if none exist."""
        response = await async_client.get("/api/v1/settings/system")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "audit_log_retention_days" in data
        assert "log_level" in data


class TestUserPreferencesAPI:
    """Tests for user preferences endpoints."""

    async def test_get_user_preferences(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/preferences/{user_email}."""
        prefs = UserPreferencesModel(
            user_email="test@example.com",
            timezone="UTC",
            date_format="ISO",
            theme="dark",
            email_notifications=True,
            discord_notifications=False,
            notification_min_severity="MEDIUM",
            default_dashboard_view="overview",
            refresh_interval_seconds=60,
        )
        test_db.add(prefs)
        await test_db.commit()

        response = await async_client.get("/api/v1/settings/preferences/test@example.com")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_email"] == "test@example.com"
        assert data["theme"] == "dark"
        assert data["timezone"] == "UTC"

    async def test_update_user_preferences(self, async_client: AsyncClient, test_db):
        """Test PATCH /api/v1/settings/preferences/{user_email}."""
        prefs = UserPreferencesModel(
            user_email="test@example.com",
            timezone="UTC",
            date_format="ISO",
            theme="light",
        )
        test_db.add(prefs)
        await test_db.commit()

        update_data = {
            "theme": "dark",
            "timezone": "America/New_York",
            "email_notifications": True,
        }

        response = await async_client.patch(
            "/api/v1/settings/preferences/test@example.com", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["theme"] == "dark"
        assert data["timezone"] == "America/New_York"
        assert data["email_notifications"] is True

    async def test_get_user_preferences_default_creation(self, async_client: AsyncClient):
        """Test that default preferences are created for new users."""
        response = await async_client.get("/api/v1/settings/preferences/newuser@example.com")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_email"] == "newuser@example.com"
        assert data["theme"] == "system"  # Default value


class TestDetectionThresholdsAPI:
    """Tests for detection thresholds endpoints."""

    async def test_get_detection_thresholds_global(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/detection without tenant_id."""
        thresholds = DetectionThresholdsModel(
            tenant_id=None,
            impossible_travel_enabled=True,
            impossible_travel_min_speed_kmh=800.0,
            impossible_travel_time_window_minutes=30,
            new_country_enabled=True,
            new_country_learning_period_days=30,
            brute_force_enabled=True,
            brute_force_threshold=5,
            brute_force_window_minutes=5,
        )
        test_db.add(thresholds)
        await test_db.commit()

        response = await async_client.get("/api/v1/settings/detection")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["impossible_travel_enabled"] is True
        assert data["impossible_travel_min_speed_kmh"] == 800.0

    async def test_get_detection_thresholds_with_tenant(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/detection with tenant_id."""
        from src.models.db import TenantModel

        tenant = TenantModel(
            id="test-tenant-123",
            name="Test Tenant",
            tenant_id="ms-tenant-id",
            client_id="client-id",
            client_secret="secret",
        )
        test_db.add(tenant)

        thresholds = DetectionThresholdsModel(
            tenant_id="test-tenant-123",
            impossible_travel_enabled=False,
            brute_force_threshold=10,
        )
        test_db.add(thresholds)
        await test_db.commit()

        response = await async_client.get("/api/v1/settings/detection?tenant_id=test-tenant-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tenant_id"] == "test-tenant-123"
        assert data["impossible_travel_enabled"] is False
        assert data["brute_force_threshold"] == 10

    async def test_update_detection_thresholds(self, async_client: AsyncClient, test_db):
        """Test PATCH /api/v1/settings/detection."""
        thresholds = DetectionThresholdsModel(
            tenant_id=None,
            impossible_travel_enabled=True,
            impossible_travel_min_speed_kmh=800.0,
        )
        test_db.add(thresholds)
        await test_db.commit()

        update_data = {
            "impossible_travel_enabled": False,
            "impossible_travel_min_speed_kmh": 900.0,
            "brute_force_threshold": 15,
        }

        response = await async_client.patch("/api/v1/settings/detection", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["impossible_travel_enabled"] is False
        assert data["impossible_travel_min_speed_kmh"] == 900.0
        assert data["brute_force_threshold"] == 15


class TestApiKeysAPI:
    """Tests for API key management endpoints."""

    async def test_create_api_key(self, async_client: AsyncClient, test_db):
        """Test POST /api/v1/settings/api-keys."""
        key_data = {
            "name": "Test API Key",
            "scopes": ["read:tenants", "read:alerts"],
            "tenant_id": None,
            "expires_days": 30,
        }

        response = await async_client.post("/api/v1/settings/api-keys", json=key_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert "key" in data
        assert data["name"] == "Test API Key"
        assert data["prefix"].startswith("sd_")
        assert "message" in data

    async def test_list_api_keys(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/api-keys."""
        # Create test API keys
        import uuid

        key1 = ApiKeyModel(
            id=uuid.uuid4(),
            name="Key 1",
            key_hash="hash1",
            key_prefix="sd_abc123",
            scopes=["read"],
            is_active=True,
        )
        key2 = ApiKeyModel(
            id=uuid.uuid4(),
            name="Key 2",
            key_hash="hash2",
            key_prefix="sd_def456",
            scopes=["read", "write"],
            is_active=True,
        )
        test_db.add_all([key1, key2])
        await test_db.commit()

        response = await async_client.get("/api/v1/settings/api-keys")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] in ["Key 1", "Key 2"]
        assert "key_prefix" in data[0]

    async def test_get_api_key(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/api-keys/{key_id}."""
        import uuid

        key = ApiKeyModel(
            id=uuid.uuid4(),
            name="Test Key",
            key_hash="hash123",
            key_prefix="sd_test",
            scopes=["read", "write"],
            is_active=True,
        )
        test_db.add(key)
        await test_db.commit()

        response = await async_client.get(f"/api/v1/settings/api-keys/{key.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Key"
        assert data["key_prefix"] == "sd_test"
        assert data["scopes"] == ["read", "write"]

    async def test_get_api_key_not_found(self, async_client: AsyncClient):
        """Test GET /api/v1/settings/api-keys/{key_id} with non-existent key."""
        import uuid

        response = await async_client.get(f"/api/v1/settings/api-keys/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_api_key(self, async_client: AsyncClient, test_db):
        """Test PATCH /api/v1/settings/api-keys/{key_id}."""
        import uuid

        key = ApiKeyModel(
            id=uuid.uuid4(),
            name="Old Name",
            key_hash="hash123",
            key_prefix="sd_test",
            scopes=["read"],
            is_active=True,
        )
        test_db.add(key)
        await test_db.commit()

        update_data = {"name": "New Name", "scopes": ["read", "write"], "is_active": False}

        response = await async_client.patch(f"/api/v1/settings/api-keys/{key.id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Name"
        assert data["scopes"] == ["read", "write"]
        assert data["is_active"] is False

    async def test_revoke_api_key(self, async_client: AsyncClient, test_db):
        """Test DELETE /api/v1/settings/api-keys/{key_id}."""
        import uuid

        key = ApiKeyModel(
            id=uuid.uuid4(),
            name="Key to Revoke",
            key_hash="hash123",
            key_prefix="sd_test",
            scopes=["read"],
            is_active=True,
        )
        test_db.add(key)
        await test_db.commit()

        response = await async_client.delete(f"/api/v1/settings/api-keys/{key.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify key is revoked
        response = await async_client.get(f"/api/v1/settings/api-keys/{key.id}")
        data = response.json()
        assert data["is_active"] is False

    async def test_revoke_api_key_not_found(self, async_client: AsyncClient):
        """Test DELETE /api/v1/settings/api-keys/{key_id} with non-existent key."""
        import uuid

        response = await async_client.delete(f"/api/v1/settings/api-keys/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestConfigBackupAPI:
    """Tests for configuration backup endpoints."""

    async def test_export_configuration(self, async_client: AsyncClient, test_db):
        """Test POST /api/v1/settings/config/export."""
        # Create required data
        settings = SystemSettingsModel(
            audit_log_retention_days=90,
            login_history_retention_days=30,
            alert_history_retention_days=365,
            auto_cleanup_enabled=True,
            cleanup_schedule="0 2 * * *",
            api_rate_limit=1000,
            max_export_rows=10000,
            log_level="INFO",
        )
        test_db.add(settings)
        await test_db.commit()

        export_data = {
            "categories": ["system"],
            "name": "Test Export",
            "description": "Test configuration export",
        }

        response = await async_client.post("/api/v1/settings/config/export", json=export_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Export"
        assert "id" in data
        assert "download_url" in data

    async def test_list_configuration_backups(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/config/backups."""
        import uuid

        backup1 = ConfigurationBackupModel(
            id=uuid.uuid4(),
            name="Backup 1",
            description="First backup",
            config_data={"system": {}},
            categories=["system"],
        )
        backup2 = ConfigurationBackupModel(
            id=uuid.uuid4(),
            name="Backup 2",
            description="Second backup",
            config_data={"detection": {}},
            categories=["detection"],
        )
        test_db.add_all([backup1, backup2])
        await test_db.commit()

        response = await async_client.get("/api/v1/settings/config/backups")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] in ["Backup 1", "Backup 2"]

    async def test_download_configuration(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/config/export/{backup_id}/download."""
        import uuid

        backup = ConfigurationBackupModel(
            id=uuid.uuid4(),
            name="Test Backup",
            description="Test backup for download",
            config_data={"system": {"audit_log_retention_days": 90}},
            categories=["system"],
        )
        test_db.add(backup)
        await test_db.commit()

        response = await async_client.get(f"/api/v1/settings/config/export/{backup.id}/download")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["system"]["audit_log_retention_days"] == 90

    async def test_download_configuration_not_found(self, async_client: AsyncClient):
        """Test GET /api/v1/settings/config/export/{backup_id}/download with non-existent backup."""
        import uuid

        response = await async_client.get(f"/api/v1/settings/config/export/{uuid.uuid4()}/download")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_import_configuration(self, async_client: AsyncClient, test_db):
        """Test POST /api/v1/settings/config/import."""
        import_data = {
            "config": {
                "system": {"audit_log_retention_days": 180, "log_level": "DEBUG"},
                "detection": {"impossible_travel_enabled": False, "brute_force_threshold": 15},
            },
            "overwrite": True,
        }

        # Create existing settings to update
        settings = SystemSettingsModel(
            audit_log_retention_days=90,
            login_history_retention_days=30,
            alert_history_retention_days=365,
            auto_cleanup_enabled=True,
            cleanup_schedule="0 2 * * *",
            api_rate_limit=1000,
            max_export_rows=10000,
            log_level="INFO",
        )
        test_db.add(settings)

        thresholds = DetectionThresholdsModel(tenant_id=None, impossible_travel_enabled=True)
        test_db.add(thresholds)
        await test_db.commit()

        response = await async_client.post("/api/v1/settings/config/import", json=import_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "system" in data["imported"]
        assert "detection" in data["imported"]

    async def test_delete_configuration_backup(self, async_client: AsyncClient, test_db):
        """Test DELETE /api/v1/settings/config/backups/{backup_id}."""
        import uuid

        backup = ConfigurationBackupModel(
            id=uuid.uuid4(),
            name="Backup to Delete",
            description="This will be deleted",
            config_data={},
            categories=["system"],
        )
        test_db.add(backup)
        await test_db.commit()

        response = await async_client.delete(f"/api/v1/settings/config/backups/{backup.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify backup is deleted
        response = await async_client.get("/api/v1/settings/config/backups")
        data = response.json()
        assert len(data) == 0

    async def test_delete_configuration_backup_not_found(self, async_client: AsyncClient):
        """Test DELETE /api/v1/settings/config/backups/{backup_id} with non-existent backup."""
        import uuid

        response = await async_client.delete(f"/api/v1/settings/config/backups/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWebhookTestAPI:
    """Tests for webhook test endpoint."""

    @patch("aiohttp.ClientSession")
    async def test_test_webhook_discord_success(self, mock_session_class, async_client: AsyncClient):
        """Test POST /api/v1/settings/webhooks/test with Discord webhook."""
        mock_session = MagicMock()
        mock_response = AsyncMock()
        mock_response.status = 204
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        test_data = {
            "webhook_url": "https://discord.com/api/webhooks/123/test",
            "webhook_type": "discord",
            "message": "Test notification",
        }

        response = await async_client.post("/api/v1/settings/webhooks/test", json=test_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "latency_ms" in data

    @patch("aiohttp.ClientSession")
    async def test_test_webhook_failure(self, mock_session_class, async_client: AsyncClient):
        """Test POST /api/v1/settings/webhooks/test with failed webhook."""
        mock_session = MagicMock()
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        test_data = {
            "webhook_url": "https://discord.com/api/webhooks/123/test",
            "webhook_type": "discord",
            "message": "Test notification",
        }

        response = await async_client.post("/api/v1/settings/webhooks/test", json=test_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "HTTP 400" in data["message"]


class TestTenantSettingsAPI:
    """Tests for tenant-specific settings endpoints."""

    async def test_get_tenant_settings(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/settings/tenants/{tenant_id}."""
        from src.models.db import TenantModel

        tenant = TenantModel(
            id="test-tenant-123",
            name="Test Tenant",
            tenant_id="ms-tenant-id",
            client_id="client-id",
            client_secret="secret",
        )
        test_db.add(tenant)

        thresholds = DetectionThresholdsModel(
            tenant_id="test-tenant-123",
            impossible_travel_enabled=True,
            impossible_travel_min_speed_kmh=900.0,
            brute_force_threshold=10,
        )
        test_db.add(thresholds)
        await test_db.commit()

        response = await async_client.get("/api/v1/settings/tenants/test-tenant-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tenant_id"] == "test-tenant-123"
        assert data["detection"]["impossible_travel_enabled"] is True
        assert data["detection"]["impossible_travel_min_speed_kmh"] == 900.0
