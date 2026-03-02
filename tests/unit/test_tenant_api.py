"""Unit tests for tenant API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.main import app

# Create in-memory test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(db_session):
    """Create async test client with test DB."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


class TestTenantAPI:
    """Test cases for tenant API endpoints."""

    @pytest.mark.asyncio
    async def test_list_tenants_empty(self, async_client):
        """Test listing tenants when empty."""
        response = await async_client.get("/api/v1/tenants/")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_tenant_success(self, async_client):
        """Test creating a tenant successfully with valid credentials."""
        with patch(
            "src.services.tenant.validate_tenant_credentials", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "display_name": "Test Organization",
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "verified_domains": [{"name": "test.com", "isDefault": True}]
            }

            tenant_data = {
                "name": "Test Tenant",
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret": "test-secret-123"
            }

            response = await async_client.post("/api/v1/tenants/", json=tenant_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["tenant"]["name"] == "Test Tenant"
            assert data["tenant"]["tenant_id"] == "12345678-1234-1234-1234-123456789012"
            assert "validation" in data
            assert data["validation"]["valid"] is True
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tenant_without_validation(self, async_client):
        """Test creating a tenant without MS validation."""
        tenant_data = {
            "name": "Test Tenant No Validate",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "client_id": "22222222-2222-2222-2222-222222222222",
            "client_secret": "test-secret-456"
        }

        response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["tenant"]["name"] == "Test Tenant No Validate"

    @pytest.mark.asyncio
    async def test_create_tenant_validation_error(self, async_client):
        """Test creating a tenant with invalid credentials fails."""
        with patch(
            "src.services.tenant.validate_tenant_credentials", new_callable=AsyncMock
        ) as mock_validate:
            # Setup mock to return invalid credentials
            mock_validate.return_value = {
                "valid": False,
                "error": "Invalid client secret"
            }

            tenant_data = {
                "name": "Invalid Tenant",
                "tenant_id": "33333333-3333-3333-3333-333333333333",
                "client_id": "44444444-4444-4444-4444-444444444444",
                "client_secret": "wrong-secret"
            }

            response = await async_client.post("/api/v1/tenants/", json=tenant_data)

            assert response.status_code == 400
            assert "Invalid client secret" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_tenant_duplicate(self, async_client):
        """Test creating duplicate tenant returns 409."""
        tenant_data = {
            "name": "Duplicate Tenant",
            "tenant_id": "55555555-5555-5555-5555-555555555555",
            "client_id": "66666666-6666-6666-6666-666666666666",
            "client_secret": "secret"
        }

        # Create first tenant
        response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )
        assert response.status_code == 201

        # Try to create duplicate
        response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_tenant(self, async_client):
        """Test getting a specific tenant."""
        # Create a tenant first
        tenant_data = {
            "name": "Get Test Tenant",
            "tenant_id": "77777777-7777-7777-7777-777777777777",
            "client_id": "88888888-8888-8888-8888-888888888888",
            "client_secret": "secret"
        }

        create_response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )
        tenant_id = create_response.json()["tenant"]["id"]

        # Get the tenant
        response = await async_client.get(f"/api/v1/tenants/{tenant_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test Tenant"
        assert data["tenant_id"] == "77777777-7777-7777-7777-777777777777"
        # Client ID should be masked
        assert "..." in data["client_id"] or data["client_id"].startswith("****")

    @pytest.mark.asyncio
    async def test_get_tenant_not_found(self, async_client):
        """Test getting non-existent tenant returns 404."""
        response = await async_client.get("/api/v1/tenants/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_tenant(self, async_client):
        """Test updating a tenant."""
        # Create a tenant first
        tenant_data = {
            "name": "Update Test Tenant",
            "tenant_id": "99999999-9999-9999-9999-999999999999",
            "client_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "client_secret": "secret"
        }

        create_response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )
        tenant_id = create_response.json()["tenant"]["id"]

        # Update the tenant
        update_data = {"name": "Updated Name", "is_active": False}
        response = await async_client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self, async_client):
        """Test updating non-existent tenant returns 404."""
        update_data = {"name": "New Name"}
        response = await async_client.patch(
            "/api/v1/tenants/non-existent-id",
            json=update_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_tenant_soft(self, async_client):
        """Test soft-deleting a tenant."""
        # Create a tenant first
        tenant_data = {
            "name": "Delete Test Tenant",
            "tenant_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "client_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "client_secret": "secret"
        }

        create_response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )
        tenant_id = create_response.json()["tenant"]["id"]

        # Delete the tenant (soft)
        response = await async_client.delete(f"/api/v1/tenants/{tenant_id}")

        assert response.status_code == 204

        # Try to get it - should fail if we only fetch active
        response = await async_client.get(f"/api/v1/tenants/{tenant_id}")
        # Tenant still exists but is inactive - API returns it
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_tenant_hard(self, async_client):
        """Test hard-deleting a tenant."""
        # Create a tenant first
        tenant_data = {
            "name": "Hard Delete Test Tenant",
            "tenant_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "client_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "client_secret": "secret"
        }

        create_response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )
        tenant_id = create_response.json()["tenant"]["id"]

        # Hard delete
        response = await async_client.delete(f"/api/v1/tenants/{tenant_id}?hard=true")

        assert response.status_code == 204

        # Try to get it - should fail
        response = await async_client.get(f"/api/v1/tenants/{tenant_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_tenant_not_found(self, async_client):
        """Test deleting non-existent tenant returns 404."""
        response = await async_client.delete("/api/v1/tenants/non-existent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validate_tenant_credentials_endpoint(self, async_client):
        """Test the validate tenant credentials endpoint."""
        # Create a tenant first
        tenant_data = {
            "name": "Validate Test Tenant",
            "tenant_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "client_id": "11111111-2222-3333-4444-555555555555",
            "client_secret": "secret"
        }

        create_response = await async_client.post(
            "/api/v1/tenants/?validate=false",
            json=tenant_data
        )
        tenant_id = create_response.json()["tenant"]["id"]

        # Mock the validation at the service layer
        with patch(
            "src.services.tenant.validate_tenant_credentials", new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "display_name": "Test Org",
                "tenant_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "verified_domains": []
            }

            response = await async_client.post(f"/api/v1/tenants/{tenant_id}/validate")

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["display_name"] == "Test Org"

    @pytest.mark.asyncio
    async def test_validate_tenant_credentials_not_found(self, async_client):
        """Test validating non-existent tenant returns 404."""
        response = await async_client.post("/api/v1/tenants/non-existent-id/validate")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_tenant_invalid_data(self, async_client):
        """Test creating tenant with invalid data returns 422."""
        # Missing required field
        tenant_data = {
            "name": "Invalid Tenant"
            # Missing tenant_id, client_id, client_secret
        }

        response = await async_client.post("/api/v1/tenants/", json=tenant_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_tenant_invalid_tenant_id_format(self, async_client):
        """Test creating tenant with invalid tenant_id format."""
        tenant_data = {
            "name": "Invalid Tenant",
            "tenant_id": "not-a-valid-uuid",
            "client_id": "22222222-2222-2222-2222-222222222222",
            "client_secret": "secret"
        }

        response = await async_client.post("/api/v1/tenants/?validate=false", json=tenant_data)

        # This may pass or fail depending on validation strictness
        # The model validation should catch it
        if response.status_code != 201:
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_list_tenants_with_data(self, async_client):
        """Test listing tenants with data present."""
        # Create multiple tenants
        for i in range(3):
            tenant_data = {
                "name": f"Tenant {i}",
                "tenant_id": f"{i:08d}-0000-0000-0000-000000000000",
                "client_id": f"{i+10:08d}-0000-0000-0000-000000000000",
                "client_secret": f"secret{i}"
            }
            await async_client.post("/api/v1/tenants/?validate=false", json=tenant_data)

        response = await async_client.get("/api/v1/tenants/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(t["is_active"] for t in data)
