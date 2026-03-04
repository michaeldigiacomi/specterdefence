"""Comprehensive tests for the SettingsService."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.settings import (
    ApiKeyModel,
    ConfigurationBackupModel,
    DetectionThresholdsModel,
    SystemSettingsModel,
    UserPreferencesModel,
)
from src.services.settings import (
    ApiKeyNotFoundError,
    InvalidConfigurationError,
    SettingsNotFoundError,
    SettingsService,
)


class TestSettingsServiceUnit:
    """Unit tests for SettingsService with mocked database."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        mock = MagicMock(spec=AsyncSession)
        mock.execute = AsyncMock()
        mock.commit = AsyncMock()
        mock.refresh = AsyncMock()
        mock.add = MagicMock()
        return mock

    @pytest.fixture
    def service(self, mock_db):
        """Create a SettingsService with mocked database."""
        return SettingsService(mock_db)

    # ========== System Settings Tests ==========

    async def test_get_system_settings_existing(self, service, mock_db):
        """Test getting existing system settings."""
        mock_settings = MagicMock(spec=SystemSettingsModel)
        mock_settings.audit_log_retention_days = 90
        mock_settings.login_history_retention_days = 30
        mock_settings.alert_history_retention_days = 365
        mock_settings.auto_cleanup_enabled = True
        mock_settings.cleanup_schedule = "0 2 * * *"
        mock_settings.api_rate_limit = 1000
        mock_settings.max_export_rows = 10000
        mock_settings.log_level = "INFO"

        # Create a mock result that returns the settings
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_settings
        mock_db.execute.return_value = mock_result

        result = await service.get_system_settings()

        assert result == mock_settings
        mock_db.execute.assert_called_once()

    async def test_get_system_settings_create_default(self, service, mock_db):
        """Test creating default system settings when none exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_system_settings()

        assert isinstance(result, SystemSettingsModel)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_update_system_settings(self, service, mock_db):
        """Test updating system settings."""
        mock_settings = MagicMock(spec=SystemSettingsModel)
        mock_settings.audit_log_retention_days = 90

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_settings
        mock_db.execute.return_value = mock_result

        updates = {"audit_log_retention_days": 180, "log_level": "DEBUG"}
        result = await service.update_system_settings(updates)

        assert result == mock_settings
        assert mock_settings.audit_log_retention_days == 180
        mock_db.commit.assert_called_once()

    # ========== User Preferences Tests ==========

    async def test_get_user_preferences_existing(self, service, mock_db):
        """Test getting existing user preferences."""
        mock_prefs = MagicMock(spec=UserPreferencesModel)
        mock_prefs.user_email = "test@example.com"
        mock_prefs.timezone = "UTC"
        mock_prefs.theme = "dark"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prefs
        mock_db.execute.return_value = mock_result

        result = await service.get_user_preferences("test@example.com")

        assert result == mock_prefs

    async def test_get_user_preferences_create_default(self, service, mock_db):
        """Test creating default preferences for new user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_user_preferences("newuser@example.com")

        assert isinstance(result, UserPreferencesModel)
        assert result.user_email == "newuser@example.com"
        mock_db.add.assert_called_once()

    async def test_update_user_preferences(self, service, mock_db):
        """Test updating user preferences."""
        mock_prefs = MagicMock(spec=UserPreferencesModel)
        mock_prefs.user_email = "test@example.com"
        mock_prefs.theme = "light"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prefs
        mock_db.execute.return_value = mock_result

        updates = {"theme": "dark", "timezone": "America/New_York"}
        result = await service.update_user_preferences("test@example.com", updates)

        assert result == mock_prefs
        assert mock_prefs.theme == "dark"
        mock_db.commit.assert_called_once()

    # ========== Detection Thresholds Tests ==========

    async def test_get_detection_thresholds_existing(self, service, mock_db):
        """Test getting existing detection thresholds."""
        mock_thresholds = MagicMock(spec=DetectionThresholdsModel)
        mock_thresholds.tenant_id = "tenant-123"
        mock_thresholds.impossible_travel_enabled = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thresholds
        mock_db.execute.return_value = mock_result

        result = await service.get_detection_thresholds("tenant-123")

        assert result == mock_thresholds

    async def test_get_detection_thresholds_global(self, service, mock_db):
        """Test getting global detection thresholds."""
        mock_thresholds = MagicMock(spec=DetectionThresholdsModel)
        mock_thresholds.tenant_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thresholds
        mock_db.execute.return_value = mock_result

        result = await service.get_detection_thresholds(None)

        assert result == mock_thresholds

    async def test_update_detection_thresholds(self, service, mock_db):
        """Test updating detection thresholds."""
        mock_thresholds = MagicMock(spec=DetectionThresholdsModel)
        mock_thresholds.impossible_travel_enabled = True
        mock_thresholds.brute_force_threshold = 5

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thresholds
        mock_db.execute.return_value = mock_result

        updates = {
            "impossible_travel_enabled": False,
            "brute_force_threshold": 10,
        }
        result = await service.update_detection_thresholds(updates, "tenant-123")

        assert result == mock_thresholds
        assert mock_thresholds.impossible_travel_enabled is False
        assert mock_thresholds.brute_force_threshold == 10

    # ========== API Key Tests ==========

    async def test_create_api_key(self, service, mock_db):
        """Test creating a new API key."""
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        result = await service.create_api_key(
            name="Test Key",
            scopes=["read", "write"],
            created_by="admin@example.com",
            tenant_id="tenant-123",
            expires_days=30,
        )

        assert "id" in result
        assert "key" in result
        assert result["name"] == "Test Key"
        assert result["prefix"].startswith("sd_")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_list_api_keys(self, service, mock_db):
        """Test listing API keys."""
        mock_key1 = MagicMock(spec=ApiKeyModel)
        mock_key1.id = "key-1"
        mock_key1.name = "Key 1"
        mock_key1.is_active = True

        mock_key2 = MagicMock(spec=ApiKeyModel)
        mock_key2.id = "key-2"
        mock_key2.name = "Key 2"
        mock_key2.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_key1, mock_key2]
        mock_db.execute.return_value = mock_result

        result = await service.list_api_keys()

        assert len(result) == 2
        assert result[0].name == "Key 1"

    async def test_get_api_key(self, service, mock_db):
        """Test getting a specific API key."""
        import uuid

        mock_key = MagicMock(spec=ApiKeyModel)
        mock_key.id = uuid.uuid4()
        mock_key.name = "Test Key"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute.return_value = mock_result

        result = await service.get_api_key(str(mock_key.id))

        assert result == mock_key

    async def test_revoke_api_key(self, service, mock_db):
        """Test revoking an API key."""
        import uuid

        mock_key = MagicMock(spec=ApiKeyModel)
        mock_key.id = uuid.uuid4()
        mock_key.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute.return_value = mock_result

        result = await service.revoke_api_key(str(mock_key.id))

        assert result is True
        assert mock_key.is_active is False
        mock_db.commit.assert_called_once()

    async def test_revoke_api_key_not_found(self, service, mock_db):
        """Test revoking a non-existent API key."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.revoke_api_key("non-existent-id")

        assert result is False

    async def test_validate_api_key_valid(self, service, mock_db):
        """Test validating a valid API key."""
        import hashlib

        mock_key = MagicMock(spec=ApiKeyModel)
        mock_key.is_active = True
        mock_key.expires_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute.return_value = mock_result

        test_key = "sd_test_key_12345"
        result = await service.validate_api_key(test_key)

        assert result == mock_key
        assert mock_key.last_used_at is not None

    async def test_validate_api_key_expired(self, service, mock_db):
        """Test validating an expired API key."""
        mock_key = MagicMock(spec=ApiKeyModel)
        mock_key.is_active = True
        mock_key.expires_at = datetime.utcnow() - timedelta(days=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute.return_value = mock_result

        result = await service.validate_api_key("sd_test_key")

        assert result is None

    async def test_update_api_key(self, service, mock_db):
        """Test updating an API key."""
        import uuid

        mock_key = MagicMock(spec=ApiKeyModel)
        mock_key.id = uuid.uuid4()
        mock_key.name = "Old Name"
        mock_key.scopes = ["read"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key
        mock_db.execute.return_value = mock_result

        updates = {"name": "New Name", "scopes": ["read", "write"]}
        result = await service.update_api_key(str(mock_key.id), updates)

        assert result == mock_key
        assert mock_key.name == "New Name"
        mock_db.commit.assert_called_once()

    # ========== Configuration Backup Tests ==========

    async def test_export_configuration(self, service, mock_db):
        """Test exporting configuration."""
        mock_settings = MagicMock(spec=SystemSettingsModel)
        mock_settings.audit_log_retention_days = 90
        mock_settings.login_history_retention_days = 30

        mock_thresholds = MagicMock(spec=DetectionThresholdsModel)
        mock_thresholds.impossible_travel_enabled = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_settings, mock_thresholds]
        mock_db.execute.return_value = mock_result

        result = await service.export_configuration(
            categories=["system", "detection"],
            name="Test Backup",
            description="Test configuration backup",
            created_by="admin@example.com",
        )

        assert "id" in result
        assert result["name"] == "Test Backup"
        assert "config" in result
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_import_configuration(self, service, mock_db):
        """Test importing configuration."""
        config_data = {
            "system": {"audit_log_retention_days": 180, "log_level": "DEBUG"},
            "detection": {"impossible_travel_enabled": False, "brute_force_threshold": 10},
        }

        mock_settings = MagicMock(spec=SystemSettingsModel)
        mock_thresholds = MagicMock(spec=DetectionThresholdsModel)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_settings, mock_thresholds]
        mock_db.execute.return_value = mock_result

        result = await service.import_configuration(config_data, overwrite=True)

        assert "system" in result["imported"]
        assert "detection" in result["imported"]
        mock_db.commit.assert_called_once()

    async def test_list_configuration_backups(self, service, mock_db):
        """Test listing configuration backups."""
        mock_backup1 = MagicMock(spec=ConfigurationBackupModel)
        mock_backup1.name = "Backup 1"

        mock_backup2 = MagicMock(spec=ConfigurationBackupModel)
        mock_backup2.name = "Backup 2"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_backup1, mock_backup2]
        mock_db.execute.return_value = mock_result

        result = await service.list_configuration_backups()

        assert len(result) == 2
        assert result[0].name == "Backup 1"

    async def test_get_configuration_backup(self, service, mock_db):
        """Test getting a specific configuration backup."""
        import uuid

        mock_backup = MagicMock(spec=ConfigurationBackupModel)
        mock_backup.id = uuid.uuid4()
        mock_backup.name = "Test Backup"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_backup
        mock_db.execute.return_value = mock_result

        result = await service.get_configuration_backup(str(mock_backup.id))

        assert result == mock_backup

    async def test_delete_configuration_backup(self, service, mock_db):
        """Test deleting a configuration backup."""
        import uuid

        mock_backup = MagicMock(spec=ConfigurationBackupModel)
        mock_backup.id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_backup
        mock_db.execute.return_value = mock_result

        result = await service.delete_configuration_backup(str(mock_backup.id))

        assert result is True
        mock_db.delete.assert_called_once_with(mock_backup)
        mock_db.commit.assert_called_once()

    async def test_delete_configuration_backup_not_found(self, service, mock_db):
        """Test deleting a non-existent configuration backup."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.delete_configuration_backup("non-existent-id")

        assert result is False
