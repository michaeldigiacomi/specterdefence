"""Alerts package for SpecterDefence."""

from src.alerts.discord import DiscordWebhookClient, DiscordWebhookError
from src.alerts.rules import AlertRuleService, AlertRuleNotFoundError
from src.alerts.engine import AlertEngine
from src.models.alerts import (
    AlertWebhookModel,
    AlertRuleModel,
    AlertHistoryModel,
    SeverityLevel,
    EventType,
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
