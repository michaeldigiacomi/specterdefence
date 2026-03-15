"""Tenant service for business logic."""

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ms_graph import MSGraphAPIError, MSGraphAuthError, MSGraphClient
from src.models.db import TenantModel
from src.models.tenant import (
    TenantCreate,
    TenantHealthCheckAuth,
    TenantHealthCheckConnectivity,
    TenantHealthCheckInfo,
    TenantHealthCheckPermissions,
    TenantHealthCheckResponse,
    TenantResponse,
    TenantUpdate,
    TenantValidationResponse,
)
from src.services.encryption import encryption_service

# Audit logger for credential access
audit_logger = logging.getLogger("specterdefence.audit")
if not audit_logger.handlers:
    audit_handler = logging.StreamHandler()
    audit_handler.setFormatter(logging.Formatter("%(asctime)s - AUDIT - %(message)s"))
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.WARNING)


class TenantService:
    """Service for tenant management operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize tenant service.

        Args:
            db: Database session
        """
        self.db = db

    async def list_tenants(self, include_inactive: bool = False) -> list[TenantResponse]:
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

    async def get_tenant(self, tenant_id: str) -> TenantModel | None:
        """Get a tenant by internal ID.

        Args:
            tenant_id: Internal tenant UUID

        Returns:
            Tenant model or None if not found
        """
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_tenant_by_ms_id(self, ms_tenant_id: str) -> TenantModel | None:
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
        self, tenant_id: str, client_id: str, client_secret: str, timeout: float = 30.0
    ) -> TenantValidationResponse:
        """Validate tenant credentials against Microsoft Graph.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application ID
            client_secret: Azure AD client secret
            timeout: Request timeout in seconds

        Returns:
            Validation response
        """
        # Use standalone function for testability
        result = await validate_tenant_credentials(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret, timeout=timeout
        )

        if result.get("valid"):
            return TenantValidationResponse(
                valid=True,
                tenant_id=result.get("tenant_id"),
                display_name=result.get("display_name"),
                domains=result.get("domains"),
            )
        else:
            return TenantValidationResponse(
                valid=False,
                error=result.get("error"),
                error_code=result.get("error_type", "unknown_error"),
            )

    async def health_check_tenant(
        self,
        tenant_id: str,
        required_permissions: list[str] | None = None,
        timeout: float = 30.0,
        update_status: bool = True,
    ) -> TenantHealthCheckResponse:
        """Perform health check on a tenant.

        Args:
            tenant_id: Internal tenant UUID
            required_permissions: List of permissions to verify (default: ["AuditLog.Read.All"])
            timeout: Request timeout in seconds
            update_status: Whether to update the tenant's connection status in database

        Returns:
            Health check response

        Raises:
            TenantNotFoundError: If tenant is not found
        """
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant with ID {tenant_id} not found")

        # Default required permissions
        if required_permissions is None:
            required_permissions = ["AuditLog.Read.All"]

        # Get decrypted secret with audit logging
        client_secret = self.get_decrypted_secret(tenant, user_id="health_check")

        # Perform health check
        try:
            async with MSGraphClient(
                tenant_id=tenant.tenant_id,
                client_id=tenant.client_id,
                client_secret=client_secret,
                timeout=timeout,
            ) as client:
                health_result = await client.health_check(required_permissions=required_permissions)

            # Build response
            response = TenantHealthCheckResponse(
                tenant_id=tenant_id,
                status=health_result["status"],
                connectivity=TenantHealthCheckConnectivity(
                    success=health_result["connectivity"]["success"],
                    latency_ms=health_result["connectivity"]["latency_ms"],
                    error=health_result["connectivity"].get("error"),
                ),
                authentication=TenantHealthCheckAuth(
                    success=health_result["authentication"]["success"],
                    error=health_result["authentication"].get("error"),
                    error_code=health_result["authentication"].get("error_code"),
                ),
                permissions=TenantHealthCheckPermissions(
                    success=health_result["permissions"]["success"],
                    granted=health_result["permissions"]["granted"],
                    missing=health_result["permissions"]["missing"],
                    details=health_result["permissions"].get("details"),
                    error=health_result["permissions"].get("error"),
                ),
                tenant_info=TenantHealthCheckInfo(
                    display_name=health_result["tenant_info"].get("display_name"),
                    tenant_id=health_result["tenant_info"].get("tenant_id"),
                    verified_domains=health_result["tenant_info"].get("verified_domains", []),
                )
                if health_result.get("tenant_info")
                else TenantHealthCheckInfo(),
                timestamp=datetime.fromisoformat(health_result["timestamp"]),
                message=self._get_health_check_message(health_result),
            )

            # Update tenant status in database if requested
            if update_status:
                await self._update_connection_status(tenant, response)

            return response

        except Exception as e:
            # Handle unexpected errors
            error_response = TenantHealthCheckResponse(
                tenant_id=tenant_id,
                status="error",
                connectivity=TenantHealthCheckConnectivity(success=False, error=str(e)),
                authentication=TenantHealthCheckAuth(success=False, error=str(e)),
                permissions=TenantHealthCheckPermissions(success=False),
                tenant_info=TenantHealthCheckInfo(),
                timestamp=datetime.now(UTC),
                message=f"Health check failed: {str(e)}",
            )

            if update_status:
                await self._update_connection_status(tenant, error_response)

            return error_response

    async def _update_connection_status(
        self, tenant: TenantModel, health_check: TenantHealthCheckResponse
    ) -> None:
        """Update tenant's connection status based on health check results.

        Args:
            tenant: Tenant model
            health_check: Health check response
        """
        tenant.connection_status = health_check.status
        tenant.last_health_check = health_check.timestamp

        # Set connection error message based on status
        if health_check.status == "healthy":
            tenant.connection_error = None
        elif health_check.status == "timeout":
            tenant.connection_error = (
                "Connection timed out. Check network or Microsoft Graph API availability."
            )
        elif not health_check.authentication.success:
            tenant.connection_error = health_check.authentication.error or "Authentication failed"
        elif not health_check.permissions.success:
            missing = (
                ", ".join(health_check.permissions.missing)
                if health_check.permissions.missing
                else "Required permissions"
            )
            tenant.connection_error = (
                f"Missing permissions: {missing}. Ensure admin consent is granted."
            )
        else:
            tenant.connection_error = health_check.message

        await self.db.commit()

    def _get_health_check_message(self, health_result: dict[str, Any]) -> str:
        """Generate a human-readable message from health check results.

        Args:
            health_result: Raw health check result dictionary

        Returns:
            Human-readable status message
        """
        status = health_result.get("status")

        if status == "healthy":
            latency = health_result["connectivity"]["latency_ms"]
            return f"Connection healthy (latency: {latency}ms)"
        elif status == "timeout":
            return (
                "Connection timed out. Check network connectivity and Microsoft Graph API status."
            )
        elif status == "error":
            auth_error = health_result["authentication"].get("error")
            return f"Connection error: {auth_error or 'Unknown error'}"
        elif status == "unhealthy":
            missing = health_result["permissions"].get("missing", [])
            if missing:
                return f"Missing required permissions: {', '.join(missing)}"
            return "Connection unhealthy - check credentials and permissions"
        else:
            return f"Unknown status: {status}"

    async def create_tenant(
        self, tenant_data: TenantCreate, validate: bool = True
    ) -> dict[str, Any]:
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
            raise TenantAlreadyExistsError(f"Tenant with ID {tenant_data.tenant_id} already exists")

        validation_result = None
        ms_tenant_name = None
        initial_status = "unknown"
        connection_error = None

        # Validate credentials if requested
        if validate:
            validation_result = await self.validate_tenant(
                tenant_id=tenant_data.tenant_id,
                client_id=tenant_data.client_id,
                client_secret=tenant_data.client_secret,
            )

            if not validation_result.valid:
                raise TenantValidationError(validation_result.error or "Invalid credentials")

            ms_tenant_name = validation_result.display_name
            initial_status = "connected"

        # Encrypt client secret
        encrypted_secret = encryption_service.encrypt(tenant_data.client_secret)

        # Create tenant model
        tenant = TenantModel(
            name=tenant_data.name,
            tenant_id=tenant_data.tenant_id,
            client_id=tenant_data.client_id,
            client_secret=encrypted_secret,
            is_active=True,
            connection_status=initial_status,
            connection_error=connection_error,
            last_health_check=datetime.now(UTC) if validate else None,
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
        self, tenant_id: str, update_data: TenantUpdate
    ) -> TenantResponse | None:
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
        if update_data.client_secret is not None:
            # Encrypt and store the new client secret
            encrypted_secret = encryption_service.encrypt(update_data.client_secret)
            tenant.client_secret = encrypted_secret
            # Reset connection status since the secret changed
            tenant.connection_status = "unknown"
            tenant.connection_error = None
        if update_data.approved_countries is not None:
            tenant.approved_countries = update_data.approved_countries

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
            connection_status=tenant.connection_status,
            connection_error=tenant.connection_error,
            last_health_check=tenant.last_health_check,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    def get_decrypted_secret(self, tenant: TenantModel, user_id: str = "system") -> str:
        """Get decrypted client secret for a tenant.

        Args:
            tenant: Tenant model
            user_id: Identifier of user/system accessing the credential

        Returns:
            Decrypted client secret
        """
        # Hash the tenant ID for audit log (privacy-preserving)
        tenant_id_hash = hashlib.sha256(tenant.id.encode()).hexdigest()[:16]

        # Log credential access for security auditing
        audit_logger.warning(
            f"CREDENTIAL_ACCESS: user={user_id} tenant_hash={tenant_id_hash} "
            f"tenant_name={tenant.name} action=decrypt_client_secret "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

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


# Standalone function for backward compatibility with tests
async def validate_tenant_credentials(
    tenant_id: str, client_id: str, client_secret: str, timeout: float = 30.0
) -> dict[str, Any]:
    """Validate tenant credentials against Microsoft Graph.

    This is a standalone wrapper for backward compatibility with tests.
    In production, use TenantService.validate_tenant() instead.

    Args:
        tenant_id: Azure AD tenant ID
        client_id: Azure AD application ID
        client_secret: Azure AD client secret
        timeout: Request timeout in seconds

    Returns:
        Dictionary with validation results
    """
    client = MSGraphClient(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    try:
        # Try to get an access token
        await client.get_access_token()

        # Try to get organization info
        org_info = await client.get_tenant_info()

        return {
            "valid": True,
            "tenant_id": tenant_id,
            "display_name": org_info.get("displayName", "Unknown"),
            "domains": org_info.get("verifiedDomains", []),
        }
    except MSGraphAuthError as e:
        return {
            "valid": False,
            "error": f"Authentication failed: {str(e)}",
            "error_type": "auth_error",
        }
    except MSGraphAPIError as e:
        return {
            "valid": False,
            "error": f"API error: {str(e)}",
            "error_type": "api_error",
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Validation failed: {str(e)}",
            "error_type": "unknown_error",
        }
