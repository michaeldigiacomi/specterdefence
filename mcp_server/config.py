"""Configuration for the SpecterDefence MCP server.

All values come from environment variables:

- SPECTER_BASE_URL   — SpecterDefence backend base URL (default http://localhost:8000)
- SPECTER_USERNAME   — SpecterDefence username (default: admin)
- SPECTER_PASSWORD   — SpecterDefence password (required)
- SPECTER_TIMEOUT    — request timeout in seconds (default: 30)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class McpConfigError(RuntimeError):
    """Raised when required configuration is missing."""


@dataclass(frozen=True)
class McpConfig:
    base_url: str
    username: str
    password: str
    request_timeout: float

    @classmethod
    def from_env(cls) -> McpConfig:
        base_url = os.environ.get("SPECTER_BASE_URL", "http://localhost:8000").rstrip("/")
        username = os.environ.get("SPECTER_USERNAME", "admin")
        password = os.environ.get("SPECTER_PASSWORD", "")
        timeout = float(os.environ.get("SPECTER_TIMEOUT", "30"))

        if not password:
            raise McpConfigError(
                "SPECTER_PASSWORD is not set. The MCP server needs credentials for "
                "SpecterDefence to authenticate against its API. "
                "Set it in the MCP server environment (see docs/MCP.md)."
            )

        return cls(
            base_url=base_url,
            username=username,
            password=password,
            request_timeout=timeout,
        )