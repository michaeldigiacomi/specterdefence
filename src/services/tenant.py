"""Tenant service for business logic."""

from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db import TenantModel
from src.models.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantValidationResponse,
)
from src.services.encryption import encryption_service
from src.clients.ms_graph import validate_tenant_credentials, MSGraphAuthError


class TenantService:
    """Service for tenant management operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize tenant service.
        
        Args:
            db: Database session
        """
        self.db = db

    async def list_tenants(self, include_inactive: bool = False) -> List[TenantResponse]:
        """List all tenants.
        
        Args:
            include_inactive: Whether to include inactive tenants
            
        Returns:
            List of tenant responses
        """
        query = select(TenantModel)
        if not include_inactive:
            query = query.where(TenantModel.is_active.is_(True))
        
        result = await self.db.execute(query)
        tenants = result.scalars().all()
        
        return [self._to_response(tenant) for tenant in tenants]

    async def get_tenant(self, tenant_id: str) -> Optional[TenantModel]:
        """Get a tenant by internal ID.
        
        Args:
            tenant_id: Internal tenant UUID
            
        Returns:
            Tenant model or None if not found
        """
        result = await self.db.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_tenant_by_ms_id(self, ms_tenant_id: str) -> Optional[TenantModel]:
        """Get a tenant by Microsoft tenant ID.
        
        Args:
            ms_tenant_id: Microsoft Azure AD tenant ID
            
        Returns:
            Tenant model or None if not found
        """
        result = await self.db.execute(
            select(TenantModel).where(TenantModel.tenant_id == ms_tenant_id)
        )
        return result.scalar_one_or_none()

    async def validate_tenant(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str
    ) -> TenantValidationResponse:
        """Validate tenant credentials against Microsoft Graph.
        
        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application ID
            client_secret: Azure AD client secret
            
        Returns:
            Validation response
        """
        try:
            validation_result = await validate_tenant_credentials(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            return TenantValidationResponse(**validation_result)
        except MSGraphAuthError as e:
            return TenantValidationResponse(
                valid=False,
                error=str(e)
            )
        except Exception as e:
            return TenantValidationResponse(
                valid=False,
                error=f"Validation error: {str(e)}"
            )

    async def create_tenant(
        self,
        tenant_data: TenantCreate,
        validate: bool = True
    ) -> Dict[str, Any]:
        """Create a new tenant.
        
        Args:
            tenant_data: Tenant creation data
            validate: Whether to validate credentials against Microsoft Graph
            
        Returns:
            Dictionary with created tenant and validation result
        """
        # Check if tenant already exists
        existing = await self.get_tenant_by_ms_id(tenant_data.tenant_id)
        if existing:
            raise TenantAlreadyExistsError(
                f"Tenant with ID {tenant_data.tenant_id} already exists"
            )

        validation_result = None
        ms_tenant_name = None
        
        # Validate credentials if requested
        if validate:
            validation_result = await self.validate_tenant(
                tenant_id=tenant_data.tenant_id,
                client_id=tenant_data.client_id,
                client_secret=tenant_data.client_secret
            )
            
            if not validation_result.valid:
                raise TenantValidationError(
                    validation_result.error or "Invalid credentials"
                )
            
            ms_tenant_name = validation_result.display_name

        # Encrypt client secret
        encrypted_secret = encryption_service.encrypt(tenant_data.client_secret)

        # Create tenant model
        tenant = TenantModel(
            name=tenant_data.name,
            tenant_id=tenant_data.tenant_id,
            client_id=tenant_data.client_id,
            client_secret=encrypted_secret,
            is_active=True,
        )

        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)

        # Build response
        response = self._to_response(tenant)
        # Add MS tenant name from validation if available
        if ms_tenant_name:
            response.ms_tenant_name = ms_tenant_name

        return {
            "tenant": response,
            "validation": validation_result,
        }

    async def update_tenant(
        self,
        tenant_id: str,
        update_data: TenantUpdate
    ) -> Optional[TenantResponse]:
        """Update a tenant.
        
        Args:
            tenant_id: Internal tenant UUID
            update_data: Update data
            
        Returns:
            Updated tenant response or None if not found
        """
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return None

        if update_data.name is not None:
            tenant.name = update_data.name
        if update_data.is_active is not None:
            tenant.is_active = update_data.is_active

        await self.db.commit()
        await self.db.refresh(tenant)

        return self._to_response(tenant)

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete (soft-delete) a tenant.
        
        Args:
            tenant_id: Internal tenant UUID
            
        Returns:
            True if deleted, False if not found
        """
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return False

        # Soft delete by setting inactive
        tenant.is_active = False
        await self.db.commit()
        
        return True

    async def hard_delete_tenant(self, tenant_id: str) -> bool:
        """Permanently delete a tenant.
        
        Args:
            tenant_id: Internal tenant UUID
            
        Returns:
            True if deleted, False if not found
        """
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return False

        await self.db.delete(tenant)
        await self.db.commit()
        
        return True

    def _to_response(self, tenant: TenantModel) -> TenantResponse:
        """Convert tenant model to response.
        
        Args:
            tenant: Tenant database model
            
        Returns:
            Tenant response model
        """
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            tenant_id=tenant.tenant_id,
            client_id=tenant.client_id,
            is_active=tenant.is_active,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    def get_decrypted_secret(self, tenant: TenantModel) -> str:
        """Get decrypted client secret for a tenant.
        
        Args:
            tenant: Tenant model
            
        Returns:
            Decrypted client secret
        """
        return encryption_service.decrypt(tenant.client_secret)


class TenantAlreadyExistsError(Exception):
    """Raised when trying to create a tenant that already exists."""
    pass


class TenantValidationError(Exception):
    """Raised when tenant credentials validation fails."""
    pass


class TenantNotFoundError(Exception):
    """Raised when a tenant is not found."""
    pass
