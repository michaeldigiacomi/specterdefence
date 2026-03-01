"""Tenant API endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.tenant import (
    TenantService,
    TenantAlreadyExistsError,
    TenantValidationError,
)
from src.models.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantCreateResponse,
)

router = APIRouter()


async def get_tenant_service(db: AsyncSession = Depends(get_db)) -> TenantService:
    """Dependency to get tenant service."""
    return TenantService(db)


@router.get(
    "/",
    response_model=List[TenantResponse],
    summary="List all tenants",
    description="Retrieve a list of all registered tenants. Optionally include inactive tenants."
)
async def list_tenants(
    include_inactive: bool = False,
    service: TenantService = Depends(get_tenant_service)
) -> List[TenantResponse]:
    """List all registered tenants.
    
    Args:
        include_inactive: If True, include inactive tenants in results
        service: Tenant service instance
        
    Returns:
        List of tenant responses
    """
    return await service.list_tenants(include_inactive=include_inactive)


@router.post(
    "/",
    response_model=TenantCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
    description="Register a new Office 365 tenant. Validates credentials against Microsoft Graph."
)
async def create_tenant(
    tenant: TenantCreate,
    validate: bool = True,
    service: TenantService = Depends(get_tenant_service)
) -> TenantCreateResponse:
    """Create a new tenant registration.
    
    Args:
        tenant: Tenant creation data
        validate: Whether to validate credentials against Microsoft Graph (default: True)
        service: Tenant service instance
        
    Returns:
        Created tenant with validation results
        
    Raises:
        HTTPException: If tenant already exists or validation fails
    """
    try:
        result = await service.create_tenant(tenant, validate=validate)
        
        return TenantCreateResponse(
            success=True,
            tenant=result["tenant"],
            validation=result["validation"],
            message="Tenant created successfully"
        )
    except TenantAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except TenantValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant by ID",
    description="Retrieve details of a specific tenant by its internal ID."
)
async def get_tenant(
    tenant_id: str,
    service: TenantService = Depends(get_tenant_service)
) -> TenantResponse:
    """Get a specific tenant by ID.
    
    Args:
        tenant_id: Internal tenant UUID
        service: Tenant service instance
        
    Returns:
        Tenant details
        
    Raises:
        HTTPException: If tenant not found
    """
    tenant = await service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )
    return service._to_response(tenant)


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant",
    description="Update tenant information (name, active status)."
)
async def update_tenant(
    tenant_id: str,
    update: TenantUpdate,
    service: TenantService = Depends(get_tenant_service)
) -> TenantResponse:
    """Update a tenant.
    
    Args:
        tenant_id: Internal tenant UUID
        update: Update data
        service: Tenant service instance
        
    Returns:
        Updated tenant details
        
    Raises:
        HTTPException: If tenant not found
    """
    updated = await service.update_tenant(tenant_id, update)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )
    return updated


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant",
    description="Soft-delete a tenant (sets is_active to False). Use hard delete for permanent removal."
)
async def delete_tenant(
    tenant_id: str,
    hard: bool = False,
    service: TenantService = Depends(get_tenant_service)
) -> None:
    """Delete a tenant registration.
    
    Args:
        tenant_id: Internal tenant UUID
        hard: If True, permanently delete the tenant
        service: Tenant service instance
        
    Raises:
        HTTPException: If tenant not found
    """
    if hard:
        deleted = await service.hard_delete_tenant(tenant_id)
    else:
        deleted = await service.delete_tenant(tenant_id)
        
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )


@router.post(
    "/{tenant_id}/validate",
    summary="Validate tenant credentials",
    description="Re-validate tenant credentials against Microsoft Graph."
)
async def validate_tenant_credentials(
    tenant_id: str,
    service: TenantService = Depends(get_tenant_service)
):
    """Validate tenant credentials.
    
    Args:
        tenant_id: Internal tenant UUID
        service: Tenant service instance
        
    Returns:
        Validation result
        
    Raises:
        HTTPException: If tenant not found
    """
    tenant = await service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )
    
    # Get decrypted secret
    client_secret = service.get_decrypted_secret(tenant)
    
    # Validate credentials
    validation = await service.validate_tenant(
        tenant_id=tenant.tenant_id,
        client_id=tenant.client_id,
        client_secret=client_secret
    )
    
    return validation
