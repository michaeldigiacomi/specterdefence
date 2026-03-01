"""Collector package for Office 365 audit log collection."""

from src.collector.o365_feed import O365ManagementClient, CONTENT_TYPES
from src.collector.main import collect_logs, TenantCollector

__all__ = [
    "O365ManagementClient",
    "CONTENT_TYPES",
    "collect_logs",
    "TenantCollector",
]