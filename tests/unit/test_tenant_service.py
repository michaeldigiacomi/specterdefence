"""Unit tests for tenant service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from src.services.tenant import TenantService, TenantAlreadyExistsError, TenantValidationError
from src.services.encryption import EncryptionService
from src.models.tenant import TenantCreate, TenantUpdate
from src.models.db import TenantModel
from src.database import Base


# Create in-memory test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def tenant_service(db_session):
    """Create a tenant service with test database."""
    return TenantService(db_session)


class TestTenantService:
    """Test cases for TenantService."""

    @pytest.mark.asyncio
    async def test_create_tenant_success(self, tenant_service):
        """Test successful tenant creation."""
        # Mock the validation
        with patch(
            "src.services.tenant.validate_tenant_credentials",
            new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "display_name": "Test Org",
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "verified_domains": [{"name": "test.com"}]
            }
            
            tenant_data = TenantCreate(
                name="Test Tenant",
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="87654321-4321-4321-4321-210987654321",
                client_secret="test-secret-123"
            )
            
            result = await tenant_service.create_tenant(tenant_data)
            
            assert result["tenant"] is not None
            assert result["validation"] is not None
            assert result["tenant"].name == "Test Tenant"
            assert result["tenant"].tenant_id == "12345678-1234-1234-1234-123456789012"
            assert result["tenant"].is_active is True
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tenant_without_validation(self, tenant_service):
        """Test tenant creation without MS validation."""
        tenant_data = TenantCreate(
            name="Test Tenant No Validate",
            tenant_id="11111111-1111-1111-1111-111111111111",
            client_id="22222222-2222-2222-2222-222222222222",
            client_secret="test-secret-456"
        )
        
        result = await tenant_service.create_tenant(tenant_data, validate=False)
        
        assert result["tenant"] is not None
        assert result["validation"] is None
        assert result["tenant"].name == "Test Tenant No Validate"

    @pytest.mark.asyncio
    async def test_create_tenant_already_exists(self, tenant_service):
        """Test that creating duplicate tenant raises error."""
        tenant_data = TenantCreate(
            name="Duplicate Tenant",
            tenant_id="33333333-3333-3333-3333-333333333333",
            client_id="44444444-4444-4444-4444-444444444444",
            client_secret="test-secret-789"
        )
        
        # Create first tenant
        await tenant_service.create_tenant(tenant_data, validate=False)
        
        # Try to create second with same tenant_id
        with pytest.raises(TenantAlreadyExistsError):
            await tenant_service.create_tenant(tenant_data, validate=False)

    @pytest.mark.asyncio
    async def test_create_tenant_validation_failure(self, tenant_service):
        """Test that validation failure raises error."""
        with patch(
            "src.services.tenant.validate_tenant_credentials",
            new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "error": "Invalid credentials"
            }
            
            tenant_data = TenantCreate(
                name="Invalid Tenant",
                tenant_id="55555555-5555-5555-5555-555555555555",
                client_id="66666666-6666-6666-6666-666666666666",
                client_secret="invalid-secret"
            )
            
            with pytest.raises(TenantValidationError):
                await tenant_service.create_tenant(tenant_data, validate=True)

    @pytest.mark.asyncio
    async def test_list_tenants(self, tenant_service):
        """Test listing tenants."""
        # Create test tenants
        tenant1 = TenantCreate(
            name="Tenant 1",
            tenant_id="77777777-7777-7777-7777-777777777777",
            client_id="88888888-8888-8888-8888-888888888888",
            client_secret="secret1"
        )
        tenant2 = TenantCreate(
            name="Tenant 2",
            tenant_id="99999999-9999-9999-9999-999999999999",
            client_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            client_secret="secret2"
        )
        
        await tenant_service.create_tenant(tenant1, validate=False)
        await tenant_service.create_tenant(tenant2, validate=False)
        
        tenants = await tenant_service.list_tenants()
        
        assert len(tenants) == 2
        assert all(t.is_active for t in tenants)

    @pytest.mark.asyncio
    async def test_list_tenants_include_inactive(self, tenant_service):
        """Test listing tenants including inactive."""
        # Create and deactivate a tenant
        tenant_data = TenantCreate(
            name="Inactive Tenant",
            tenant_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            client_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            client_secret="secret"
        )
        
        result = await tenant_service.create_tenant(tenant_data, validate=False)
        await tenant_service.delete_tenant(result["tenant"].id)
        
        # Without include_inactive
        active_only = await tenant_service.list_tenants(include_inactive=False)
        assert len(active_only) == 0
        
        # With include_inactive
        all_tenants = await tenant_service.list_tenants(include_inactive=True)
        assert len(all_tenants) == 1
        assert not all_tenants[0].is_active

    @pytest.mark.asyncio
    async def test_get_tenant(self, tenant_service):
        """Test getting a single tenant."""
        tenant_data = TenantCreate(
            name="Get Test Tenant",
            tenant_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            client_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            client_secret="secret"
        )
        
        created = await tenant_service.create_tenant(tenant_data, validate=False)
        
        # Get by internal ID
        fetched = await tenant_service.get_tenant(created["tenant"].id)
        assert fetched is not None
        assert fetched.name == "Get Test Tenant"
        
        # Get by MS tenant ID
        fetched_by_ms_id = await tenant_service.get_tenant_by_ms_id(tenant_data.tenant_id)
        assert fetched_by_ms_id is not None
        assert fetched_by_ms_id.tenant_id == tenant_data.tenant_id

    @pytest.mark.asyncio
    async def test_get_tenant_not_found(self, tenant_service):
        """Test getting non-existent tenant returns None."""
        fetched = await tenant_service.get_tenant("non-existent-id")
        assert fetched is None
        
        fetched_by_ms_id = await tenant_service.get_tenant_by_ms_id("non-existent-tenant-id")
        assert fetched_by_ms_id is None

    @pytest.mark.asyncio
    async def test_update_tenant(self, tenant_service):
        """Test updating a tenant."""
        tenant_data = TenantCreate(
            name="Update Test Tenant",
            tenant_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
            client_id="11111111-2222-3333-4444-555555555555",
            client_secret="secret"
        )
        
        created = await tenant_service.create_tenant(tenant_data, validate=False)
        
        # Update name
        update = TenantUpdate(name="Updated Name")
        updated = await tenant_service.update_tenant(created["tenant"].id, update)
        
        assert updated is not None
        assert updated.name == "Updated Name"
        
        # Update active status
        update = TenantUpdate(is_active=False)
        updated = await tenant_service.update_tenant(created["tenant"].id, update)
        
        assert updated is not None
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self, tenant_service):
        """Test updating non-existent tenant returns None."""
        update = TenantUpdate(name="New Name")
        result = await tenant_service.update_tenant("non-existent-id", update)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_tenant_soft(self, tenant_service):
        """Test soft-deleting a tenant."""
        tenant_data = TenantCreate(
            name="Delete Test Tenant",
            tenant_id="22222222-3333-4444-5555-666666666666",
            client_id="77777777-8888-9999-aaaa-bbbbbbbbbbbb",
            client_secret="secret"
        )
        
        created = await tenant_service.create_tenant(tenant_data, validate=False)
        
        # Soft delete
        deleted = await tenant_service.delete_tenant(created["tenant"].id)
        assert deleted is True
        
        # Verify tenant is marked inactive
        tenant = await tenant_service.get_tenant(created["tenant"].id)
        assert tenant is not None
        assert tenant.is_active is False

    @pytest.mark.asyncio
    async def test_delete_tenant_hard(self, tenant_service):
        """Test hard-deleting a tenant."""
        tenant_data = TenantCreate(
            name="Hard Delete Test Tenant",
            tenant_id="33333333-4444-5555-6666-777777777777",
            client_id="88888888-9999-aaaa-bbbb-cccccccccccc",
            client_secret="secret"
        )
        
        created = await tenant_service.create_tenant(tenant_data, validate=False)
        
        # Hard delete
        deleted = await tenant_service.hard_delete_tenant(created["tenant"].id)
        assert deleted is True
        
        # Verify tenant is gone
        tenant = await tenant_service.get_tenant(created["tenant"].id)
        assert tenant is None

    @pytest.mark.asyncio
    async def test_delete_tenant_not_found(self, tenant_service):
        """Test deleting non-existent tenant returns False."""
        result = await tenant_service.delete_tenant("non-existent-id")
        assert result is False
        
        result = await tenant_service.hard_delete_tenant("non-existent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_client_secret_encryption(self, tenant_service):
        """Test that client secrets are properly encrypted/decrypted."""
        secret = "my-super-secret-key"
        tenant_data = TenantCreate(
            name="Encryption Test Tenant",
            tenant_id="44444444-5555-6666-7777-888888888888",
            client_id="99999999-aaaa-bbbb-cccc-dddddddddddd",
            client_secret=secret
        )
        
        created = await tenant_service.create_tenant(tenant_data, validate=False)
        
        # Get raw tenant from DB
        tenant = await tenant_service.get_tenant(created["tenant"].id)
        
        # Verify secret is encrypted in DB (not plaintext)
        assert tenant.client_secret != secret
        # Base64 encoded Fernet token - should be valid base64
        import base64
        try:
            base64.urlsafe_b64decode(tenant.client_secret)
        except Exception:
            pytest.fail("client_secret should be valid base64")
        
        # Verify we can decrypt it
        decrypted = tenant_service.get_decrypted_secret(tenant)
        assert decrypted == secret

    @pytest.mark.asyncio
    async def test_validate_tenant(self, tenant_service):
        """Test tenant credential validation."""
        with patch(
            "src.services.tenant.validate_tenant_credentials",
            new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "display_name": "Validated Org",
                "tenant_id": "55555555-6666-7777-8888-999999999999",
                "verified_domains": []
            }
            
            result = await tenant_service.validate_tenant(
                tenant_id="55555555-6666-7777-8888-999999999999",
                client_id="test-client-id",
                client_secret="test-secret"
            )
            
            assert result.valid is True
            assert result.display_name == "Validated Org"

    @pytest.mark.asyncio
    async def test_validate_tenant_failure(self, tenant_service):
        """Test tenant credential validation failure."""
        with patch(
            "src.services.tenant.validate_tenant_credentials",
            new_callable=AsyncMock
        ) as mock_validate:
            from src.clients.ms_graph import MSGraphAuthError
            mock_validate.side_effect = MSGraphAuthError("Invalid credentials")
            
            result = await tenant_service.validate_tenant(
                tenant_id="test-tenant-id",
                client_id="test-client-id",
                client_secret="test-secret"
            )
            
            assert result.valid is False
            assert "Invalid credentials" in result.error
