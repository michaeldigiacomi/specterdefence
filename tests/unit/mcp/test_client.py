"""Unit tests for the SpecterDefence MCP server HTTP client (no mcp dep needed)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from mcp_server.client import API_PREFIX, BackendError, SpecterClient
from mcp_server.config import McpConfig


def make_config() -> McpConfig:
    return McpConfig(
        base_url="http://specter.test", username="agent", password="hunter2", request_timeout=5
    )


class FakeBackend:
    """Mock SpecterDefence API driven through httpx.MockTransport."""

    def __init__(self, login_count: int = 0) -> None:
        self.login_count = login_count
        self.calls: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path

        if path == f"{API_PREFIX}/auth/local/login":
            self.login_count += 1
            body = json.loads(request.content)
            if body["username"] == "agent" and body["password"] == "hunter2":
                return httpx.Response(200, json={"access_token": f"jwt-{self.login_count}"})
            return httpx.Response(401, json={"detail": "Incorrect username or password"})

        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer jwt-{self.login_count}":
            return httpx.Response(401, json={"detail": "Token expired"})

        if path == f"{API_PREFIX}/tenants/" and request.method == "GET":
            return httpx.Response(200, json=[{"id": "t-1", "name": "Acme"}])

        if path == f"{API_PREFIX}/alerts/history":
            return httpx.Response(200, json={"items": [], "total": 0})

        if path == f"{API_PREFIX}/boom":
            return httpx.Response(404, json={"detail": "Not found"})

        return httpx.Response(500, json={"detail": "unhandled route"})


def make_client(backend: FakeBackend) -> SpecterClient:
    http = httpx.AsyncClient(
        base_url="http://specter.test" + API_PREFIX, transport=httpx.MockTransport(backend.handler)
    )
    return SpecterClient(make_config(), http=http)


@pytest.mark.asyncio
async def test_login_happens_once_and_token_is_reused() -> None:
    backend = FakeBackend()
    client = make_client(backend)
    try:
        await client.get("/tenants/")
        await client.get("/tenants/")
        await client.get("/tenants/")
    finally:
        await client.aclose()

    assert backend.login_count == 1
    # 3 API calls + 1 login
    assert len(backend.calls) == 4


@pytest.mark.asyncio
async def test_relogin_after_401_then_retry_succeeds() -> None:
    backend = FakeBackend()
    client = make_client(backend)
    try:
        result = await client.get("/tenants/")
        assert result[0]["name"] == "Acme"
        # Simulate server-side token invalidation: next counter mismatch causes
        # the handler to 401 the first request, forcing re-login.
        backend.login_count += 1
        result = await client.get("/tenants/")
        assert result[0]["name"] == "Acme"
    finally:
        await client.aclose()

    assert backend.login_count == 3  # initial + forced-expired relogin x2 attempts


@pytest.mark.asyncio
async def test_api_error_raises_backend_error_with_detail() -> None:
    backend = FakeBackend()
    client = make_client(backend)
    try:
        with pytest.raises(BackendError) as exc_info:
            await client.get("/boom")
        assert exc_info.value.status_code == 404
        assert "Not found" in str(exc_info.value)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_bad_credentials_raise_on_login() -> None:
    config = McpConfig(
        base_url="http://specter.test", username="wrong", password="nope", request_timeout=5
    )
    backend = FakeBackend()
    http = httpx.AsyncClient(
        base_url="http://specter.test" + API_PREFIX, transport=httpx.MockTransport(backend.handler)
    )
    client = SpecterClient(config, http=http)
    try:
        with pytest.raises(BackendError) as exc_info:
            await client.get("/tenants/")
        assert exc_info.value.status_code == 401
        assert "rejected" in str(exc_info.value)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_none_params_are_stripped() -> None:
    backend = FakeBackend()
    client = make_client(backend)
    try:
        await client.get("/alerts/history", params={"severity": None, "limit": 10})
    finally:
        await client.aclose()

    api_call = [c for c in backend.calls if "history" in c.url.path][0]
    assert "severity" not in api_call.url.params
    assert api_call.url.params["limit"] == "10"


@pytest.mark.parametrize("password", ["", None])
def test_config_requires_password(password: Any) -> None:
    import os

    env_backup = {
        k: os.environ.get(k) for k in ("SPECTER_PASSWORD", "SPECTER_USERNAME", "SPECTER_BASE_URL")
    }
    try:
        for k in env_backup:
            os.environ.pop(k, None)
        if password:
            os.environ["SPECTER_PASSWORD"] = password
        from mcp_server.config import McpConfigError

        with pytest.raises(McpConfigError):
            McpConfig.from_env()
    finally:
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v