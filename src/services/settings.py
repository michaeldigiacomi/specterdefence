"""Settings service for SpecterDefence."""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.alerts import AlertRuleModel, AlertWebhookModel
from src.models.settings import (
    ApiKeyModel,
    ConfigurationBackupModel,
    DetectionThresholdsModel,
    SystemSettingsModel,
    UserPreferencesModel,
)


class SettingsNotFoundError(Exception):
    """Exception raised when settings are not found."""

    pass


class ApiKeyNotFoundError(Exception):
    """Exception raised when API key is not found."""

    pass


class InvalidConfigurationError(Exception):
    """Exception raised when configuration is invalid."""

    pass


class SettingsService:
    """Service for managing application settings."""

    def __init__(self, db: AsyncSession):
        """Initialize the settings service.

        Args:
            db: Database session
        """
        self.db = db

    # ========== System Settings ==========

    async def get_system_settings(self) -> SystemSettingsModel:
        """Get system settings (create defaults if not exists).

        Returns:
            System settings model
        """
        result = await self.db.execute(select(SystemSettingsModel))
        settings = result.scalar_one_or_none()

        if not settings:
            settings = SystemSettingsModel()
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)

        return settings

    async def update_system_settings(self, updates: dict[str, Any]) -> SystemSettingsModel:
        """Update system settings.

        Args:
            updates: Dictionary of fields to update

        Returns:
            Updated system settings
        """
        settings = await self.get_system_settings()

        for field, value in updates.items():
            if hasattr(settings, field):
                setattr(settings, field, value)

        settings.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(settings)

        return settings

    # ========== User Preferences ==========

    async def get_user_preferences(self, user_email: str) -> UserPreferencesModel:
        """Get user preferences (create defaults if not exists).

        Args:
            user_email: User email address

        Returns:
            User preferences model
        """
        result = await self.db.execute(
            select(UserPreferencesModel).where(UserPreferencesModel.user_email == user_email)
        )
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = UserPreferencesModel(user_email=user_email)
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(prefs)

        return prefs

    async def update_user_preferences(
        self, user_email: str, updates: dict[str, Any]
    ) -> UserPreferencesModel:
        """Update user preferences.

        Args:
            user_email: User email address
            updates: Dictionary of fields to update

        Returns:
            Updated user preferences
        """
        prefs = await self.get_user_preferences(user_email)

        for field, value in updates.items():
            if hasattr(prefs, field):
                setattr(prefs, field, value)

        prefs.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(prefs)

        return prefs

    # ========== Detection Thresholds ==========

    async def get_detection_thresholds(
        self, tenant_id: str | None = None
    ) -> DetectionThresholdsModel:
        """Get detection thresholds for a tenant (or global defaults).

        Args:
            tenant_id: Optional tenant ID

        Returns:
            Detection thresholds model
        """
        if tenant_id:
            result = await self.db.execute(
                select(DetectionThresholdsModel).where(
                    DetectionThresholdsModel.tenant_id == tenant_id
                )
            )
            thresholds = result.scalar_one_or_none()
            if thresholds:
                return thresholds

        # Get global defaults
        result = await self.db.execute(
            select(DetectionThresholdsModel).where(DetectionThresholdsModel.tenant_id.is_(None))
        )
        thresholds = result.scalar_one_or_none()

        if not thresholds:
            thresholds = DetectionThresholdsModel(tenant_id=None)
            self.db.add(thresholds)
            await self.db.commit()
            await self.db.refresh(thresholds)

        return thresholds

    async def update_detection_thresholds(
        self, updates: dict[str, Any], tenant_id: str | None = None
    ) -> DetectionThresholdsModel:
        """Update detection thresholds.

        Args:
            updates: Dictionary of fields to update
            tenant_id: Optional tenant ID (None for global)

        Returns:
            Updated detection thresholds
        """
        thresholds = await self.get_detection_thresholds(tenant_id)

        for field, value in updates.items():
            if hasattr(thresholds, field):
                setattr(thresholds, field, value)

        thresholds.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(thresholds)

        return thresholds

    # ========== API Keys ==========

    async def create_api_key(
        self,
        name: str,
        scopes: list[str],
        created_by: str | None = None,
        tenant_id: str | None = None,
        expires_days: int | None = None,
    ) -> dict[str, str]:
        """Create a new API key.

        Args:
            name: Display name for the key
            scopes: List of allowed scopes
            created_by: Email of user creating the key
            tenant_id: Optional tenant restriction
            expires_days: Optional expiration in days

        Returns:
            Dictionary with key ID and the full API key (shown only once)
        """
        # Generate a secure API key
        api_key = f"sd_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:8]

        expires_at = None
        if expires_days:
            from datetime import timedelta

            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        api_key_model = ApiKeyModel(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            tenant_id=tenant_id,
            created_by=created_by,
            expires_at=expires_at,
            is_active=True,
        )

        self.db.add(api_key_model)
        await self.db.commit()
        await self.db.refresh(api_key_model)

        return {
            "id": str(api_key_model.id),
            "key": api_key,  # Only shown once!
            "name": name,
            "prefix": key_prefix,
        }

    async def list_api_keys(
        self, tenant_id: str | None = None, include_inactive: bool = False
    ) -> list[ApiKeyModel]:
        """List API keys.

        Args:
            tenant_id: Filter by tenant
            include_inactive: Include inactive keys

        Returns:
            List of API key models
        """
        query = select(ApiKeyModel)

        if tenant_id:
            query = query.where(
                (ApiKeyModel.tenant_id == tenant_id) | (ApiKeyModel.tenant_id.is_(None))
            )

        if not include_inactive:
            query = query.where(ApiKeyModel.is_active.is_(True))

        query = query.order_by(desc(ApiKeyModel.created_at))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_api_key(self, key_id: str) -> ApiKeyModel | None:
        """Get an API key by ID.

        Args:
            key_id: API key UUID

        Returns:
            API key model or None
        """
        result = await self.db.execute(
            select(ApiKeyModel).where(ApiKeyModel.id == uuid.UUID(key_id))
        )
        return result.scalar_one_or_none()

    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            key_id: API key UUID

        Returns:
            True if revoked, False if not found
        """
        api_key = await self.get_api_key(key_id)
        if not api_key:
            return False

        api_key.is_active = False
        await self.db.commit()

        return True

    async def update_api_key(self, key_id: str, updates: dict[str, Any]) -> ApiKeyModel | None:
        """Update an API key.

        Args:
            key_id: API key UUID
            updates: Dictionary of fields to update

        Returns:
            Updated API key or None
        """
        api_key = await self.get_api_key(key_id)
        if not api_key:
            return None

        for field, value in updates.items():
            if hasattr(api_key, field) and field not in ["key_hash", "key_prefix"]:
                setattr(api_key, field, value)

        await self.db.commit()
        await self.db.refresh(api_key)

        return api_key

    async def validate_api_key(self, api_key: str) -> ApiKeyModel | None:
        """Validate an API key and update last used timestamp.

        Args:
            api_key: The API key to validate

        Returns:
            API key model if valid, None otherwise
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        result = await self.db.execute(
            select(ApiKeyModel).where(
                (ApiKeyModel.key_hash == key_hash) & (ApiKeyModel.is_active.is_(True))
            )
        )
        key_model = result.scalar_one_or_none()

        if not key_model:
            return None

        # Check expiration
        if key_model.expires_at and key_model.expires_at < datetime.utcnow():
            return None

        # Update last used
        key_model.last_used_at = datetime.utcnow()
        await self.db.commit()

        return key_model

    # ========== Configuration Backup/Restore ==========

    async def export_configuration(
        self,
        categories: list[str],
        name: str,
        description: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        """Export configuration to JSON.

        Args:
            categories: List of categories to export
            name: Backup name
            description: Optional description
            created_by: User creating the backup

        Returns:
            Configuration export data
        """
        config_data = {}

        if "system" in categories:
            system = await self.get_system_settings()
            config_data["system"] = {
                "audit_log_retention_days": system.audit_log_retention_days,
                "login_history_retention_days": system.login_history_retention_days,
                "alert_history_retention_days": system.alert_history_retention_days,
                "auto_cleanup_enabled": system.auto_cleanup_enabled,
                "cleanup_schedule": system.cleanup_schedule,
                "api_rate_limit": system.api_rate_limit,
                "max_export_rows": system.max_export_rows,
                "log_level": system.log_level,
            }

        if "detection" in categories:
            detection = await self.get_detection_thresholds()
            config_data["detection"] = {
                "impossible_travel_enabled": detection.impossible_travel_enabled,
                "impossible_travel_min_speed_kmh": detection.impossible_travel_min_speed_kmh,
                "impossible_travel_time_window_minutes": detection.impossible_travel_time_window_minutes,
                "new_country_enabled": detection.new_country_enabled,
                "new_country_learning_period_days": detection.new_country_learning_period_days,
                "brute_force_enabled": detection.brute_force_enabled,
                "brute_force_threshold": detection.brute_force_threshold,
                "brute_force_window_minutes": detection.brute_force_window_minutes,
                "new_ip_enabled": detection.new_ip_enabled,
                "new_ip_learning_period_days": detection.new_ip_learning_period_days,
                "multiple_failures_enabled": detection.multiple_failures_enabled,
                "multiple_failures_threshold": detection.multiple_failures_threshold,
                "multiple_failures_window_minutes": detection.multiple_failures_window_minutes,
                "risk_score_base_multiplier": detection.risk_score_base_multiplier,
            }

        if "alert_rules" in categories:
            result = await self.db.execute(select(AlertRuleModel))
            rules = result.scalars().all()
            config_data["alert_rules"] = [
                {
                    "name": r.name,
                    "event_types": r.event_types,
                    "min_severity": r.min_severity,
                    "cooldown_minutes": r.cooldown_minutes,
                    "is_active": r.is_active,
                    "tenant_id": r.tenant_id,
                }
                for r in rules
            ]

        if "webhooks" in categories:
            result = await self.db.execute(
                select(AlertWebhookModel).where(AlertWebhookModel.is_active.is_(True))
            )
            webhooks = result.scalars().all()
            config_data["webhooks"] = [
                {
                    "name": w.name,
                    "webhook_type": w.webhook_type,
                    "is_active": w.is_active,
                    "tenant_id": w.tenant_id,
                }
                for w in webhooks
            ]

        # Save backup record
        backup = ConfigurationBackupModel(
            name=name,
            description=description,
            config_data=config_data,
            categories=categories,
            created_by=created_by,
        )
        self.db.add(backup)
        await self.db.commit()
        await self.db.refresh(backup)

        return {
            "id": str(backup.id),
            "name": name,
            "description": description,
            "categories": categories,
            "created_at": backup.created_at.isoformat(),
            "config": config_data,
        }

    async def import_configuration(
        self, config_data: dict[str, Any], overwrite: bool = False
    ) -> dict[str, Any]:
        """Import configuration from JSON.

        Args:
            config_data: Configuration data to import
            overwrite: Whether to overwrite existing settings

        Returns:
            Import results summary
        """
        results = {"imported": [], "errors": []}

        try:
            if "system" in config_data and overwrite:
                await self.update_system_settings(config_data["system"])
                results["imported"].append("system")

            if "detection" in config_data:
                await self.update_detection_thresholds(config_data["detection"])
                results["imported"].append("detection")

            if "alert_rules" in config_data:
                for rule_data in config_data["alert_rules"]:
                    rule = AlertRuleModel(**rule_data)
                    self.db.add(rule)
                results["imported"].append("alert_rules")

            await self.db.commit()

        except Exception as e:
            results["errors"].append(str(e))

        return results

    async def list_configuration_backups(self) -> list[ConfigurationBackupModel]:
        """List all configuration backups.

        Returns:
            List of backup models
        """
        result = await self.db.execute(
            select(ConfigurationBackupModel).order_by(desc(ConfigurationBackupModel.created_at))
        )
        return list(result.scalars().all())

    async def get_configuration_backup(self, backup_id: str) -> ConfigurationBackupModel | None:
        """Get a specific configuration backup.

        Args:
            backup_id: Backup UUID

        Returns:
            Backup model or None
        """
        result = await self.db.execute(
            select(ConfigurationBackupModel).where(
                ConfigurationBackupModel.id == uuid.UUID(backup_id)
            )
        )
        return result.scalar_one_or_none()

    async def delete_configuration_backup(self, backup_id: str) -> bool:
        """Delete a configuration backup.

        Args:
            backup_id: Backup UUID

        Returns:
            True if deleted, False if not found
        """
        backup = await self.get_configuration_backup(backup_id)
        if not backup:
            return False

        await self.db.delete(backup)
        await self.db.commit()

        return True
