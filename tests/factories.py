"""Test data factories for SpecterDefence tests.

Uses factory_boy for generating test data.
"""

import uuid
from datetime import datetime

import factory
from factory import Faker
from factory.fuzzy import FuzzyChoice, FuzzyInteger

from src.models.alerts import (
    AlertHistoryModel,
    AlertRuleModel,
    AlertWebhookModel,
    EventType,
    SeverityLevel,
    WebhookType,
)
from src.models.db import TenantModel
from src.models.settings import (
    ApiKeyModel,
    ConfigurationBackupModel,
    DetectionThresholdsModel,
    SystemSettingsModel,
    UserPreferencesModel,
)
from src.models.user import UserModel


class TenantFactory(factory.Factory):
    """Factory for creating TenantModel instances."""

    class Meta:
        model = TenantModel

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.Sequence(lambda n: f"Test Tenant {n}")
    tenant_id = factory.LazyFunction(
        lambda: f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:12]}"
    )
    client_id = factory.LazyFunction(
        lambda: f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:12]}"
    )
    client_secret = factory.LazyFunction(lambda: f"encrypted-secret-{uuid.uuid4().hex}")
    is_active = True
    connection_status = FuzzyChoice(["connected", "error", "unknown", "timeout"])
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class UserFactory(factory.Factory):
    """Factory for creating UserModel instances."""

    class Meta:
        model = UserModel

    id = factory.Sequence(lambda n: n + 1)
    username = factory.Sequence(lambda n: f"user{n}")
    password_hash = factory.LazyFunction(
        lambda: "$2b$12$qaI.IhS84lIGdfXRFU8aZOhLqJqsZbhJt1UFx8rWSjzlHynm53.kK"  # admin123
    )
    is_active = True
    is_admin = False
    last_login = factory.LazyFunction(datetime.utcnow)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    username = "admin"
    is_admin = True


class AlertWebhookFactory(factory.Factory):
    """Factory for creating AlertWebhookModel instances."""

    class Meta:
        model = AlertWebhookModel

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Webhook {n}")
    webhook_url = factory.LazyFunction(
        lambda: f"https://discord.com/api/webhooks/{uuid.uuid4().hex[:18]}/{uuid.uuid4().hex[:64]}"
    )
    webhook_type = WebhookType.DISCORD
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)


class AlertRuleFactory(factory.Factory):
    """Factory for creating AlertRuleModel instances."""

    class Meta:
        model = AlertRuleModel

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Alert Rule {n}")
    event_types = factory.LazyFunction(
        lambda: [EventType.IMPOSSIBLE_TRAVEL, EventType.NEW_COUNTRY]
    )
    min_severity = FuzzyChoice(list(SeverityLevel))
    cooldown_minutes = FuzzyInteger(5, 120)
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class AlertHistoryFactory(factory.Factory):
    """Factory for creating AlertHistoryModel instances."""

    class Meta:
        model = AlertHistoryModel

    id = factory.LazyFunction(uuid.uuid4)
    webhook_id = factory.LazyFunction(uuid.uuid4)
    severity = FuzzyChoice(list(SeverityLevel))
    event_type = FuzzyChoice(list(EventType))
    user_email = factory.LazyFunction(lambda: f"user{uuid.uuid4().hex[:8]}@example.com")
    title = factory.Sequence(lambda n: f"Alert {n}")
    message = Faker("sentence")
    alert_metadata = factory.LazyFunction(dict)
    dedup_hash = factory.LazyFunction(lambda: uuid.uuid4().hex)
    sent_at = factory.LazyFunction(datetime.utcnow)


class SystemSettingsFactory(factory.Factory):
    """Factory for creating SystemSettingsModel instances."""

    class Meta:
        model = SystemSettingsModel

    audit_log_retention_days = FuzzyInteger(30, 365)
    login_history_retention_days = FuzzyInteger(7, 90)
    alert_history_retention_days = FuzzyInteger(90, 730)
    auto_cleanup_enabled = FuzzyChoice([True, False])
    cleanup_schedule = "0 2 * * *"
    api_rate_limit = FuzzyInteger(100, 10000)
    max_export_rows = FuzzyInteger(1000, 100000)
    log_level = FuzzyChoice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class UserPreferencesFactory(factory.Factory):
    """Factory for creating UserPreferencesModel instances."""

    class Meta:
        model = UserPreferencesModel

    user_email = factory.LazyFunction(lambda: f"user{uuid.uuid4().hex[:8]}@example.com")
    timezone = FuzzyChoice(["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"])
    date_format = FuzzyChoice(["ISO", "US", "EU"])
    theme = FuzzyChoice(["light", "dark", "system"])
    email_notifications = FuzzyChoice([True, False])
    discord_notifications = FuzzyChoice([True, False])
    notification_min_severity = FuzzyChoice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    default_dashboard_view = "overview"
    refresh_interval_seconds = FuzzyInteger(10, 3600)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class DetectionThresholdsFactory(factory.Factory):
    """Factory for creating DetectionThresholdsModel instances."""

    class Meta:
        model = DetectionThresholdsModel

    tenant_id = None  # Global by default
    impossible_travel_enabled = FuzzyChoice([True, False])
    impossible_travel_min_speed_kmh = FuzzyInteger(600, 1000)
    impossible_travel_time_window_minutes = FuzzyInteger(15, 60)
    new_country_enabled = FuzzyChoice([True, False])
    new_country_learning_period_days = FuzzyInteger(7, 90)
    brute_force_enabled = FuzzyChoice([True, False])
    brute_force_threshold = FuzzyInteger(3, 20)
    brute_force_window_minutes = FuzzyInteger(5, 30)
    new_ip_enabled = FuzzyChoice([True, False])
    new_ip_learning_period_days = FuzzyInteger(7, 90)
    multiple_failures_enabled = FuzzyChoice([True, False])
    multiple_failures_threshold = FuzzyInteger(3, 20)
    multiple_failures_window_minutes = FuzzyInteger(5, 30)
    risk_score_base_multiplier = 1.0
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class ApiKeyFactory(factory.Factory):
    """Factory for creating ApiKeyModel instances."""

    class Meta:
        model = ApiKeyModel

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"API Key {n}")
    key_hash = factory.LazyFunction(lambda: uuid.uuid4().hex)
    key_prefix = factory.LazyFunction(lambda: f"sd_{uuid.uuid4().hex[:7]}")
    scopes = factory.LazyFunction(lambda: ["read:tenants", "read:alerts"])
    is_active = True
    tenant_id = None
    created_by = factory.LazyFunction(lambda: f"admin{uuid.uuid4().hex[:4]}@example.com")
    created_at = factory.LazyFunction(datetime.utcnow)


class ConfigurationBackupFactory(factory.Factory):
    """Factory for creating ConfigurationBackupModel instances."""

    class Meta:
        model = ConfigurationBackupModel

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Backup {n}")
    description = Faker("sentence")
    config_data = factory.LazyFunction(
        lambda: {"system": {"log_level": "INFO"}, "detection": {"enabled": True}}
    )
    categories = factory.LazyFunction(lambda: ["system", "detection"])
    created_by = factory.LazyFunction(lambda: f"admin{uuid.uuid4().hex[:4]}@example.com")
    created_at = factory.LazyFunction(datetime.utcnow)


def create_test_tenant(db_session, **kwargs):
    """Helper function to create a test tenant.

    Args:
        db_session: SQLAlchemy async session
        **kwargs: Override factory defaults

    Returns:
        Created TenantModel instance
    """
    tenant = TenantFactory(**kwargs)
    db_session.add(tenant)
    return tenant


def create_test_user(db_session, **kwargs):
    """Helper function to create a test user.

    Args:
        db_session: SQLAlchemy async session
        **kwargs: Override factory defaults

    Returns:
        Created UserModel instance
    """
    user = UserFactory(**kwargs)
    db_session.add(user)
    return user


def create_test_alert_rule(db_session, **kwargs):
    """Helper function to create a test alert rule.

    Args:
        db_session: SQLAlchemy async session
        **kwargs: Override factory defaults

    Returns:
        Created AlertRuleModel instance
    """
    rule = AlertRuleFactory(**kwargs)
    db_session.add(rule)
    return rule


def create_test_webhook(db_session, **kwargs):
    """Helper function to create a test webhook.

    Args:
        db_session: SQLAlchemy async session
        **kwargs: Override factory defaults

    Returns:
        Created AlertWebhookModel instance
    """
    webhook = AlertWebhookFactory(**kwargs)
    db_session.add(webhook)
    return webhook
