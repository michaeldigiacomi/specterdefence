"""Collector package for Office 365 audit log collection."""

from src.collector.main import TenantCollector, collect_logs
from src.collector.o365_feed import CONTENT_TYPES, O365ManagementClient

__all__ = [
    "O365ManagementClient",
    "CONTENT_TYPES",
    "collect_logs",
    "TenantCollector",
]
