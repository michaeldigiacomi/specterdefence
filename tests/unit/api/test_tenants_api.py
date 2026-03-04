"""Comprehensive tests for the Tenant API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.models.db import TenantModel
from src.models.tenant import TenantCreate, TenantUpdate


class TestTenantListAPI:
    """Tests for listing tenants."""

    async def test_list_tenants_empty(self, async_client: AsyncClient):
        """Test GET /api/v1/tenants with no tenants."""
        response = await async_client.get("/api/v1/tenants")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_tenants(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/tenants with multiple tenants."""
        tenant1 = TenantModel(
            id="tenant-1",
            name="Test Tenant 1",
            tenant_id="ms-tenant-id-1",
            client_id="client-id-1",
            client_secret="encrypted-secret-1",
            is_active=True,
            connection_status="connected",
        )
        tenant2 = TenantModel(
            id="tenant-2",
            name="Test Tenant 2",
            tenant_id="ms-tenant-id-2",
            client_id="client-id-2",
            client_secret="encrypted-secret-2",
            is_active=True,
            connection_status="error",
            connection_error="Authentication failed",
        )
        test_db.add_all([tenant1, tenant2])
        await test_db.commit()

        response = await async_client.get("/api/v1/tenants")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] in ["Test Tenant 1", "Test Tenant 2"]

    async def test_list_tenants_include_inactive(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/tenants with include_inactive parameter."""
        tenant1 = TenantModel(
            id="tenant-1",
            name="Active Tenant",
            tenant_id="ms-tenant-id-1",
            client_id="client-id-1",
            client_secret="encrypted-secret-1",
            is_active=True,
        )
        tenant2 = TenantModel(
            id="tenant-2",
            name="Inactive Tenant",
            tenant_id="ms-tenant-id-2",
            client_id="client-id-2",
            client_secret="encrypted-secret-2",
            is_active=False,
        )
        test_db.add_all([tenant1, tenant2])
        await test_db.commit()

        # Get only active
        response = await async_client.get("/api/v1/tenants?include_inactive=false")
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Active Tenant"

        # Get all including inactive
        response = await async_client.get("/api/v1/tenants?include_inactive=true")
        data = response.json()
        assert len(data) == 2


class TestTenantCreateAPI:
    """Tests for creating tenants."""

    @patch("src.api.tenants.TenantService")
    async def test_create_tenant_success(self, mock_service_class, async_client: AsyncClient):
        """Test POST /api/v1/tenants with valid data."""
        mock_service = MagicMock()
        mock_service.create_tenant = AsyncMock(return_value={
            "tenant": MagicMock(
                id="new-tenant-id",
                name="New Tenant",
                tenant_id="ms-tenant-id",
                client_id="client-id",
                is_active=True,
                connection_status="connected",
            ),
            "validation": MagicMock(valid=True),
        })
        mock_service_class.return_value = mock_service

        tenant_data = {
            "name": "New Tenant",
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "client_id": "87654321-4321-4321-4321-210987654321",
            "client_secret": "test-secret-12345",
            "validate": True,
        }

        response = await async_client.post("/api/v1/tenants", json=tenant_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Tenant"
        assert data["tenant_id"] == "12345678-1234-1234-1234-123456789012"

    async def test_create_tenant_validation_error(self, async_client: AsyncClient):
        """Test POST /api/v1/tenants with invalid data."""
        tenant_data = {
            "name": "",  # Empty name should fail validation
            "tenant_id": "invalid-uuid",
            "client_id": "client-id",
            "client_secret": "secret",
        }

        response = await async_client.post("/api/v1/tenants", json=tenant_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_tenant_already_exists(self, async_client: AsyncClient, test_db):
        """Test POST /api/v1/tenants with duplicate tenant_id."""
        existing_tenant = TenantModel(
            id="existing-id",
            name="Existing Tenant",
            tenant_id="duplicate-tenant-id",
            client_id="client-id",
            client_secret="secret",
        )
        test_db.add(existing_tenant)
        await test_db.commit()

        tenant_data = {
            "name": "New Tenant",
            "tenant_id": "duplicate-tenant-id",
            "client_id": "new-client-id",
            "client_secret": "new-secret",
            "validate": False,
        }

        response = await async_client.post("/api/v1/tenants", json=tenant_data)

        assert response.status_code == status.HTTP_409_CONFLICT


class TestTenantGetAPI:
    """Tests for getting a specific tenant."""

    async def test_get_tenant_success(self, async_client: AsyncClient, test_db):
        """Test GET /api/v1/tenants/{tenant_id}."""
        tenant = TenantModel(
            id="test-tenant-id",
            name="Test Tenant",
            tenant_id="ms-tenant-id",
            client_id="client-id",
            client_secret="encrypted-secret",
            is_active=True,
            connection_status="connected",
            last_health_check=datetime.utcnow(),
        )
        test_db.add(tenant)
        await test_db.commit()

        response = await async_client.get("/api/v1/tenants/test-tenant-id")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "test-tenant-id"
        assert data["name"] == "Test Tenant"
        assert data["tenant_id"] == "ms-tenant-id"
        assert data["connection_status"] == "connected"

    async def test_get_tenant_not_found(self, async_client: AsyncClient):
        """Test GET /api/v1/tenants/{tenant_id} with non-existent tenant."""
        response = await async_client.get("/api/v1/tenants/non-existent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTenantUpdateAPI:
    """Tests for updating tenants."""

    async def test_update_tenant_success(self, async_client: AsyncClient, test_db):
        """Test PATCH /api/v1/tenants/{tenant_id}."""
        tenant = TenantModel(
            id="test-tenant-id",
            name="Old Name",
            tenant_id="ms-tenant-id",
            client_id="client-id",
            client_secret="encrypted-secret",
            is_active=True,
        )
        test_db.add(tenant)
        await test_db.commit()

        update_data = {"name": "New Name", "is_active": False}

        response = await async_client.patch("/api/v1/tenants/test-tenant-id", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Name"
        assert data["is_active"] is False

    async def test_update_tenant_not_found(self, async_client: AsyncClient):
        """Test PATCH /api/v1/tenants/{tenant_id} with non-existent tenant."""
        update_data = {"name": "New Name"}

        response = await async_client.patch("/api/v1/tenants/non-existent-id", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_tenant_partial(self, async_client: AsyncClient, test_db):
        """Test PATCH /api/v1/tenants/{tenant_id} with partial update."""
        tenant = TenantModel(
            id="test-tenant-id",
            name="Test Tenant",
            tenant_id="ms-tenant-id",
            client_id="client-id",
            client_secret="encrypted-secret",
            is_active=True,
        )
        test_db.add(tenant)
        await test_db.commit()

        # Only update name, keep is_active unchanged
        update_data = {"name": "Updated Tenant Name"}

        response = await async_client.patch("/api/v1/tenants/test-tenant-id", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Tenant Name"
        assert data["is_active"] is True  # Unchanged


class TestTenantDeleteAPI:
    """Tests for deleting tenants."""

    async def test_delete_tenant_success(self, async_client: AsyncClient, test_db):
        """Test DELETE /api/v1/tenants/{tenant_id} (soft delete)."""
        tenant = TenantModel(
            id="test-tenant-id",
            name="Test Tenant",
            tenant_id="ms-tenant-id",
            client_id="client-id",
            client_secret="encrypted-secret",
            is_active=True,
        )
        test_db.add(tenant)
        await test_db.commit()

        response = await async_client.delete("/api/v1/tenants/test-tenant-id")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify tenant is soft-deleted (inactive)
        response = await async_client.get("/api/v1/tenants/test-tenant-id")
        data = response.json()
        assert data["is_active"] is False

    async def test_delete_tenant_not_found(self, async_client: AsyncClient):
        """Test DELETE /api/v1/tenants/{tenant_id} with non-existent tenant."""
        response = await async_client.delete("/api/v1/tenants/non-existent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTenantHealthCheckAPI:
    """Tests for tenant health check endpoints."""

    @patch("src.api.tenants.TenantService")
    async def test_health_check_tenant_success(self, mock_service_class, async_client: AsyncClient):
        """Test POST /api/v1/tenants/{tenant_id}/health-check."""
        mock_service = MagicMock()
        mock_health_response = MagicMock()
        mock_health_response.status = "healthy"
        mock_health_response.message = "Connection healthy (latency: 150ms)"
        mock_health_response.connectivity.success = True
        mock_health_response.connectivity.latency_ms = 150
        mock_health_response.authentication.success = True
        mock_health_response.permissions.success = True
        mock_health_response.permissions.granted = ["AuditLog.Read.All"]
        mock_health_response.permissions.missing = []
        mock_health_response.tenant_info.display_name = "Test Organization"
        mock_health_response.tenant_info.verified_domains = [{"name": "test.com"}]
        mock_health_response.timestamp.isoformat.return_value = "2026-03-04T12:00:00"

        mock_service.health_check_tenant = AsyncMock(return_value=mock_health_response)
        mock_service_class.return_value = mock_service

        response = await async_client.post("/api/v1/tenants/test-tenant-id/health-check")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "Connection healthy (latency: 150ms)"

    async def test_health_check_tenant_not_found(self, async_client: AsyncClient):
        """Test POST /api/v1/tenants/{tenant_id}/health-check with non-existent tenant."""
        response = await async_client.post("/api/v1/tenants/non-existent-id/health-check")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.api.tenants.TenantService")
    async def test_health_check_tenant_error(self, mock_service_class, async_client: AsyncClient):
        """Test POST /api/v1/tenants/{tenant_id}/health-check with connection error."""
        mock_service = MagicMock()
        mock_health_response = MagicMock()
        mock_health_response.status = "error"
        mock_health_response.message = "Connection error: Authentication failed"
        mock_health_response.connectivity.success = False
        mock_health_response.connectivity.error = "Connection timeout"
        mock_health_response.authentication.success = False
        mock_health_response.authentication.error = "Invalid credentials"
        mock_health_response.permissions.success = False
        mock_health_response.timestamp.isoformat.return_value = "2026-03-04T12:00:00"

        mock_service.health_check_tenant = AsyncMock(return_value=mock_health_response)
        mock_service_class.return_value = mock_service

        response = await async_client.post("/api/v1/tenants/test-tenant-id/health-check")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert "Authentication failed" in data["message"]


class TestTenantValidationAPI:
    """Tests for tenant validation endpoints."""

    @patch("src.api.tenants.TenantService")
    async def test_validate_tenant_success(self, mock_service_class, async_client: AsyncClient):
        """Test POST /api/v1/tenants/validate."""
        mock_service = MagicMock()
        mock_validation = MagicMock()
        mock_validation.valid = True
        mock_validation.tenant_id = "12345678-1234-1234-1234-123456789012"
        mock_validation.display_name = "Test Organization"
        mock_validation.domains = [{"name": "test.com", "isDefault": True}]

        mock_service.validate_tenant = AsyncMock(return_value=mock_validation)
        mock_service_class.return_value = mock_service

        validation_data = {
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "client_id": "87654321-4321-4321-4321-210987654321",
            "client_secret": "test-secret",
        }

        response = await async_client.post("/api/v1/tenants/validate", json=validation_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert data["display_name"] == "Test Organization"

    @patch("src.api.tenants.TenantService")
    async def test_validate_tenant_failure(self, mock_service_class, async_client: AsyncClient):
        """Test POST /api/v1/tenants/validate with invalid credentials."""
        mock_service = MagicMock()
        mock_validation = MagicMock()
        mock_validation.valid = False
        mock_validation.error = "Invalid client secret"
        mock_validation.error_code = "auth_error"

        mock_service.validate_tenant = AsyncMock(return_value=mock_validation)
        mock_service_class.return_value = mock_service

        validation_data = {
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "client_id": "87654321-4321-4321-4321-210987654321",
            "client_secret": "invalid-secret",
        }

        response = await async_client.post("/api/v1/tenants/validate", json=validation_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "Invalid client secret" in data["error"]


class TestTenantHardDeleteAPI:
    """Tests for hard deleting tenants."""

    async def test_hard_delete_tenant_success(self, async_client: AsyncClient, test_db):
        """Test DELETE /api/v1/tenants/{tenant_id}/hard."""
        tenant = TenantModel(
            id="test-tenant-id",
            name="Test Tenant",
            tenant_id="ms-tenant-id",
            client_id="client-id",
            client_secret="encrypted-secret",
            is_active=True,
        )
        test_db.add(tenant)
        await test_db.commit()

        response = await async_client.delete("/api/v1/tenants/test-tenant-id/hard")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify tenant is permanently deleted
        response = await async_client.get("/api/v1/tenants/test-tenant-id")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_hard_delete_tenant_not_found(self, async_client: AsyncClient):
        """Test DELETE /api/v1/tenants/{tenant_id}/hard with non-existent tenant."""
        response = await async_client.delete("/api/v1/tenants/non-existent-id/hard")

        assert response.status_code == status.HTTP_404_NOT_FOUND
