"""HTTP client for the SpecterDefence API, with JWT login and token caching.

The backend has no service-account/API-key auth yet, so the MCP server logs in
with username/password via POST /api/v1/auth/local/login and reuses the JWT
until the API rejects it with 401, at which point it re-logs in and retries
the request once.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from mcp_server.config import McpConfig

logger = logging.getLogger("specterdefence.mcp")

API_PREFIX = "/api/v1"

# Refresh proactively just before typical token lifetime expires. The backend
# issues tokens with ACCESS_TOKEN_EXPIRE_MINUTES; we don't read its expiry from
# the token itself but re-login on any 401, so this bound is only an optimisation.
_PROACTIVE_REFRESH_SECONDS = 25 * 60


class BackendError(RuntimeError):
    """Raised when the SpecterDefence API returns an error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SpecterClient:
    """Async client for the SpecterDefence backend."""

    def __init__(
        self,
        config: McpConfig,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._http = http or httpx.AsyncClient(
            base_url=config.base_url + API_PREFIX,
            timeout=config.request_timeout,
        )
        self._owns_http = http is None
        self._token: str | None = None
        self._token_time: float = 0.0
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    # ------------------------------------------------------------------ auth

    async def _login(self) -> None:
        try:
            resp = await self._http.post(
                "/auth/local/login",
                json={
                    "username": self._config.username,
                    "password": self._config.password,
                },
            )
        except httpx.HTTPError as e:
            raise BackendError(
                f"Cannot reach SpecterDefence at {self._config.base_url}: {e}"
            ) from e

        if resp.status_code == 401:
            raise BackendError(
                "SpecterDefence rejected the MCP server credentials "
                f"(username: {self._config.username}).", 401
            )
        if resp.status_code == 429:
            raise BackendError(
                "SpecterDefence login rate limit hit (5 failed attempts per 5 minutes "
                "blocks an IP for 15 minutes).", 429
            )
        if resp.status_code != 200:
            raise BackendError(
                f"Login failed with HTTP {resp.status_code}: {resp.text[:300]}", resp.status_code
            )

        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise BackendError("Login response did not contain an access_token")

        self._token = token
        self._token_time = time.monotonic()
        logger.info("Authenticated to SpecterDefence as %s", self._config.username)

    async def _ensure_token(self) -> str:
        async with self._lock:
            stale = time.monotonic() - self._token_time > _PROACTIVE_REFRESH_SECONDS
            if self._token is None or stale:
                await self._login()
            assert self._token is not None
            return self._token

    # ------------------------------------------------------------------ api

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json_body: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", path, json_body=json_body)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        _retried_after_relogin: bool = False,
    ) -> Any:
        token = await self._ensure_token()
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        try:
            resp = await self._http.request(
                method,
                path,
                params=clean_params,
                json=json_body,
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as e:
            raise BackendError(
                f"Cannot reach SpecterDefence at {self._config.base_url}: {e}"
            ) from e

        if resp.status_code == 401 and not _retried_after_relogin:
            # Token expired or was revoked — re-login once and retry.
            async with self._lock:
                self._token = None
            return await self._request(
                method, path, params=params, json_body=json_body, _retried_after_relogin=True
            )

        if resp.status_code >= 400:
            detail = _extract_detail(resp)
            raise BackendError(detail, resp.status_code)

        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}

        try:
            return resp.json()
        except ValueError:
            return {"status": "ok", "raw": resp.text[:2000]}


def _extract_detail(resp: httpx.Response) -> str:
    """Pull a human-readable message out of a FastAPI error response."""
    try:
        body = resp.json()
    except ValueError:
        return f"SpecterDefence API error (HTTP {resp.status_code}): {resp.text[:300]}"

    if isinstance(body, dict) and "detail" in body:
        detail = body["detail"]
        if isinstance(detail, str):
            return detail
        return f"SpecterDefence API error (HTTP {resp.status_code}): {detail}"

    return f"SpecterDefence API error (HTTP {resp.status_code}): {body}"