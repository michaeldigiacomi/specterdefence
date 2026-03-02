"""Clients package for SpecterDefence."""

from src.clients.ms_graph import (
    MSGraphAPIError,
    MSGraphAuthError,
    MSGraphClient,
    validate_tenant_credentials,
)

__all__ = [
    "MSGraphClient",
    "MSGraphAuthError",
    "MSGraphAPIError",
    "validate_tenant_credentials",
]
