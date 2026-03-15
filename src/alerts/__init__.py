"""Alerts package for SpecterDefence."""

from src.alerts.discord import DiscordWebhookClient, DiscordWebhookError
from src.alerts.engine import AlertEngine
from src.alerts.rules import AlertRuleNotFoundError, AlertRuleService
from src.models.alerts import (
    AlertHistoryModel,
    AlertRuleModel,
    AlertWebhookModel,
    EventType,
    SeverityLevel,
    WebhookType,
)

__all__ = [
    "DiscordWebhookClient",
    "DiscordWebhookError",
    "AlertRuleService",
    "AlertRuleNotFoundError",
    "AlertEngine",
    "AlertWebhookModel",
    "AlertRuleModel",
    "AlertHistoryModel",
    "SeverityLevel",
    "EventType",
    "WebhookType",
]
