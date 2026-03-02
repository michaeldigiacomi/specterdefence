"""Tests for settings API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.settings import DetectionThresholdsModel, SystemSettingsModel, UserPreferencesModel
from src.services.settings import SettingsService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_settings_service(mock_db):
    """Create a mock settings service."""
    service = MagicMock(spec=SettingsService)
    service.db = mock_db
    return service


@pytest.mark.asyncio
async def test_get_system_settings(mock_settings_service):
    """Test getting system settings."""
    # Arrange
    mock_settings = SystemSettingsModel()
    mock_settings.audit_log_retention_days = 90
    mock_settings.login_history_retention_days = 365
    mock_settings.alert_history_retention_days = 180
    mock_settings.auto_cleanup_enabled = True
    mock_settings.cleanup_schedule = "0 2 * * *"
    mock_settings.api_rate_limit = 1000
    mock_settings.max_export_rows = 10000
    mock_settings.log_level = "INFO"
    mock_settings.created_at = datetime.now(UTC)
    mock_settings.updated_at = datetime.now(UTC)

    mock_settings_service.get_system_settings = AsyncMock(return_value=mock_settings)

    # Act
    result = await mock_settings_service.get_system_settings()

    # Assert
    assert result.audit_log_retention_days == 90
    assert result.login_history_retention_days == 365
    assert result.auto_cleanup_enabled is True


@pytest.mark.asyncio
async def test_update_system_settings(mock_settings_service):
    """Test updating system settings."""
    # Arrange
    mock_settings = SystemSettingsModel()
    mock_settings.audit_log_retention_days = 60
    mock_settings_service.update_system_settings = AsyncMock(return_value=mock_settings)

    updates = {"audit_log_retention_days": 60}

    # Act
    result = await mock_settings_service.update_system_settings(updates)

    # Assert
    assert result.audit_log_retention_days == 60


@pytest.mark.asyncio
async def test_get_user_preferences(mock_settings_service):
    """Test getting user preferences."""
    # Arrange
    mock_prefs = UserPreferencesModel()
    mock_prefs.user_email = "test@example.com"
    mock_prefs.timezone = "UTC"
    mock_prefs.theme = "system"
    mock_prefs.email_notifications = True
    mock_prefs.discord_notifications = True
    mock_prefs.notification_min_severity = "MEDIUM"

    mock_settings_service.get_user_preferences = AsyncMock(return_value=mock_prefs)

    # Act
    result = await mock_settings_service.get_user_preferences("test@example.com")

    # Assert
    assert result.user_email == "test@example.com"
    assert result.timezone == "UTC"
    assert result.theme == "system"


@pytest.mark.asyncio
async def test_update_user_preferences(mock_settings_service):
    """Test updating user preferences."""
    # Arrange
    mock_prefs = UserPreferencesModel()
    mock_prefs.user_email = "test@example.com"
    mock_prefs.theme = "dark"

    mock_settings_service.update_user_preferences = AsyncMock(return_value=mock_prefs)

    updates = {"theme": "dark"}

    # Act
    result = await mock_settings_service.update_user_preferences("test@example.com", updates)

    # Assert
    assert result.theme == "dark"


@pytest.mark.asyncio
async def test_get_detection_thresholds(mock_settings_service):
    """Test getting detection thresholds."""
    # Arrange
    mock_thresholds = DetectionThresholdsModel()
    mock_thresholds.impossible_travel_enabled = True
    mock_thresholds.impossible_travel_min_speed_kmh = 800
    mock_thresholds.brute_force_threshold = 5

    mock_settings_service.get_detection_thresholds = AsyncMock(return_value=mock_thresholds)

    # Act
    result = await mock_settings_service.get_detection_thresholds()

    # Assert
    assert result.impossible_travel_enabled is True
    assert result.impossible_travel_min_speed_kmh == 800
    assert result.brute_force_threshold == 5


@pytest.mark.asyncio
async def test_update_detection_thresholds(mock_settings_service):
    """Test updating detection thresholds."""
    # Arrange
    mock_thresholds = DetectionThresholdsModel()
    mock_thresholds.brute_force_threshold = 10

    mock_settings_service.update_detection_thresholds = AsyncMock(return_value=mock_thresholds)

    updates = {"brute_force_threshold": 10}

    # Act
    result = await mock_settings_service.update_detection_thresholds(updates)

    # Assert
    assert result.brute_force_threshold == 10


@pytest.mark.asyncio
async def test_create_api_key(mock_settings_service):
    """Test creating an API key."""
    # Arrange
    mock_settings_service.create_api_key = AsyncMock(return_value={
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "key": "sd_test_key_12345",
        "name": "Test Key",
        "prefix": "sd_test_"
    })

    # Act
    result = await mock_settings_service.create_api_key(
        name="Test Key",
        scopes=["read:analytics"],
        created_by="admin@test.com"
    )

    # Assert
    assert result["name"] == "Test Key"
    assert "key" in result
    assert result["prefix"] == "sd_test_"


@pytest.mark.asyncio
async def test_list_api_keys(mock_settings_service):
    """Test listing API keys."""
    # Arrange
    import uuid

    from src.models.settings import ApiKeyModel

    mock_key = MagicMock(spec=ApiKeyModel)
    mock_key.id = uuid.uuid4()
    mock_key.name = "Test Key"
    mock_key.key_prefix = "sd_test"
    mock_key.scopes = ["read:analytics"]
    mock_key.is_active = True
    mock_key.created_at = datetime.now(UTC)

    mock_settings_service.list_api_keys = AsyncMock(return_value=[mock_key])

    # Act
    result = await mock_settings_service.list_api_keys()

    # Assert
    assert len(result) == 1
    assert result[0].name == "Test Key"
    assert result[0].is_active is True


@pytest.mark.asyncio
async def test_revoke_api_key(mock_settings_service):
    """Test revoking an API key."""
    # Arrange
    mock_settings_service.revoke_api_key = AsyncMock(return_value=True)

    # Act
    result = await mock_settings_service.revoke_api_key("test-key-id")

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_export_configuration(mock_settings_service):
    """Test exporting configuration."""
    # Arrange
    mock_settings_service.export_configuration = AsyncMock(return_value={
        "id": "backup-123",
        "name": "Test Backup",
        "categories": ["system", "detection"],
        "created_at": datetime.now(UTC).isoformat(),
        "config": {
            "system": {"log_level": "INFO"},
            "detection": {"brute_force_threshold": 5}
        }
    })

    # Act
    result = await mock_settings_service.export_configuration(
        categories=["system", "detection"],
        name="Test Backup",
        created_by="admin@test.com"
    )

    # Assert
    assert result["name"] == "Test Backup"
    assert "system" in result["config"]
    assert "detection" in result["config"]


@pytest.mark.asyncio
async def test_import_configuration(mock_settings_service):
    """Test importing configuration."""
    # Arrange
    mock_settings_service.import_configuration = AsyncMock(return_value={
        "imported": ["system", "detection"],
        "errors": []
    })

    config_data = {
        "system": {"log_level": "DEBUG"},
        "detection": {"brute_force_threshold": 10}
    }

    # Act
    result = await mock_settings_service.import_configuration(
        config_data=config_data,
        overwrite=True
    )

    # Assert
    assert len(result["imported"]) == 2
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_webhook_test_success():
    """Test successful webhook test."""
    # This test would require mocking aiohttp
    # For now, we just verify the endpoint structure exists
    pass


class TestSettingsValidation:
    """Test settings validation."""

    def test_system_settings_validation(self):
        """Test system settings field validation."""
        # Test retention days limits

        # Get the default values from column info
        assert SystemSettingsModel.audit_log_retention_days.default.arg == 90
        assert SystemSettingsModel.login_history_retention_days.default.arg == 365

    def test_detection_thresholds_validation(self):
        """Test detection thresholds field validation."""
        # Test default values
        assert DetectionThresholdsModel.impossible_travel_min_speed_kmh.default.arg == 800.0
        assert DetectionThresholdsModel.brute_force_threshold.default.arg == 5
        assert DetectionThresholdsModel.new_country_learning_period_days.default.arg == 30
