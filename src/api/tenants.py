"""Tenant API endpoints."""

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.tenant import (
    TenantCreate,
    TenantCreateResponse,
    TenantHealthCheckResponse,
    TenantResponse,
    TenantUpdate,
)
from src.services.tenant import (
    TenantAlreadyExistsError,
    TenantNotFoundError,
    TenantService,
    TenantValidationError,
)

router = APIRouter()


async def get_tenant_service(db: AsyncSession = Depends(get_db)) -> TenantService:
    """Dependency to get tenant service."""
    return TenantService(db)


@router.get(
    "/",
    response_model=list[TenantResponse],
    summary="List all tenants",
    description="Retrieve a list of all registered tenants. Optionally include inactive tenants.",
)
async def list_tenants(
    include_inactive: bool = False, service: TenantService = Depends(get_tenant_service)
) -> list[TenantResponse]:
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
    description="Register a new Office 365 tenant. Validates credentials against Microsoft Graph.",
)
async def create_tenant(
    tenant: TenantCreate,
    validate: bool = True,
    service: TenantService = Depends(get_tenant_service),
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
            message="Tenant created successfully",
        )
    except TenantAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except TenantValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}",
        )


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant by ID",
    description="Retrieve details of a specific tenant by its internal ID.",
)
async def get_tenant(
    tenant_id: str, service: TenantService = Depends(get_tenant_service)
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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant with ID {tenant_id} not found"
        )
    return service._to_response(tenant)


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant",
    description="Update tenant information (name, active status).",
)
async def update_tenant(
    tenant_id: str, update: TenantUpdate, service: TenantService = Depends(get_tenant_service)
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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant with ID {tenant_id} not found"
        )
    return updated


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant",
    description="Soft-delete a tenant (sets is_active to False). Use hard delete for permanent removal.",
)
async def delete_tenant(
    tenant_id: str, hard: bool = False, service: TenantService = Depends(get_tenant_service)
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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant with ID {tenant_id} not found"
        )


@router.post(
    "/{tenant_id}/validate",
    summary="Validate tenant credentials",
    description="Re-validate tenant credentials against Microsoft Graph.",
)
async def validate_tenant_credentials(
    tenant_id: str, service: TenantService = Depends(get_tenant_service)
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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant with ID {tenant_id} not found"
        )

    # Get decrypted secret with audit logging
    client_secret = service.get_decrypted_secret(tenant, user_id="api_validate_endpoint")

    # Validate credentials
    validation = await service.validate_tenant(
        tenant_id=tenant.tenant_id, client_id=tenant.client_id, client_secret=client_secret
    )

    return validation


@router.post(
    "/{tenant_id}/health-check",
    response_model=TenantHealthCheckResponse,
    summary="Test tenant connection health",
    description="""
    Perform a comprehensive health check on the tenant connection.

    Tests:
    - Microsoft Graph API connectivity
    - Authentication with tenant credentials
    - Required permissions (AuditLog.Read.All by default)
    - Response latency

    Updates the tenant's connection_status field with the result.
    """,
)
async def health_check_tenant(
    tenant_id: str,
    permissions: list[str]
    | None = Query(
        None, description="Optional list of permissions to verify (default: AuditLog.Read.All)"
    ),
    timeout: float = Query(
        30.0, ge=5.0, le=120.0, description="Request timeout in seconds (5-120)"
    ),
    update_status: bool = Query(
        True, description="Whether to update the tenant's connection status in database"
    ),
    service: TenantService = Depends(get_tenant_service),
) -> TenantHealthCheckResponse:
    """Perform health check on a tenant connection.

    Args:
        tenant_id: Internal tenant UUID
        permissions: List of permissions to verify (default: ["AuditLog.Read.All"])
        timeout: Request timeout in seconds
        update_status: Whether to update connection status in database
        service: Tenant service instance

    Returns:
        Health check response with connectivity, authentication, and permission status

    Raises:
        HTTPException: If tenant not found
    """
    try:
        result = await service.health_check_tenant(
            tenant_id=tenant_id,
            required_permissions=permissions,
            timeout=timeout,
            update_status=update_status,
        )
        return result
    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant with ID {tenant_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )


@router.post(
    "/health-check/all",
    response_model=list[TenantHealthCheckResponse],
    summary="Test all tenant connections",
    description="Perform health checks on all active tenants.",
)
async def health_check_all_tenants(
    permissions: list[str]
    | None = Query(
        None, description="Optional list of permissions to verify (default: AuditLog.Read.All)"
    ),
    timeout: float = Query(
        30.0, ge=5.0, le=120.0, description="Request timeout in seconds (5-120)"
    ),
    service: TenantService = Depends(get_tenant_service),
) -> list[TenantHealthCheckResponse]:
    """Perform health checks on all active tenants.

    Args:
        permissions: List of permissions to verify (default: ["AuditLog.Read.All"])
        timeout: Request timeout in seconds
        service: Tenant service instance

    Returns:
        List of health check responses for all active tenants
    """
    tenants = await service.list_tenants(include_inactive=False)
    results = []

    for tenant_response in tenants:
        try:
            result = await service.health_check_tenant(
                tenant_id=tenant_response.id,
                required_permissions=permissions,
                timeout=timeout,
                update_status=True,
            )
            results.append(result)
        except Exception as e:
            # Include error result for this tenant
            from datetime import datetime

            from src.models.tenant import (
                TenantHealthCheckAuth,
                TenantHealthCheckConnectivity,
                TenantHealthCheckInfo,
                TenantHealthCheckPermissions,
            )

            results.append(
                TenantHealthCheckResponse(
                    tenant_id=tenant_response.id,
                    status="error",
                    connectivity=TenantHealthCheckConnectivity(success=False, error=str(e)),
                    authentication=TenantHealthCheckAuth(success=False, error=str(e)),
                    permissions=TenantHealthCheckPermissions(success=False),
                    tenant_info=TenantHealthCheckInfo(),
                    timestamp=datetime.now(UTC),
                    message=f"Health check failed: {str(e)}",
                )
            )

    return results
