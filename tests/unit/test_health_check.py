"""Unit tests for tenant health check functionality."""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from src.clients.ms_graph import MSGraphClient, MSGraphAuthError, MSGraphAPIError
from src.models.tenant import (
    TenantHealthCheckResponse,
    TenantHealthCheckConnectivity,
    TenantHealthCheckAuth,
    TenantHealthCheckPermissions,
    TenantHealthCheckInfo,
)


class TestMSGraphClientHealthCheck:
    """Test cases for MSGraphClient health check functionality."""

    @pytest.fixture
    def mock_msal_app(self):
        """Create a mock MSAL application."""
        with patch("src.clients.ms_graph.msal.ConfidentialClientApplication") as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_msal_app):
        """Create a test client with mocked MSAL."""
        mock_app = MagicMock()
        mock_msal_app.return_value = mock_app
        
        return MSGraphClient(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-client-secret",
            timeout=30.0
        )

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_msal_app):
        """Test successful health check with all permissions granted."""
        # Mock token acquisition
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            # Mock organization endpoint
            org_response = MagicMock()
            org_response.status_code = 200
            org_response.json.return_value = {
                "value": [{
                    "displayName": "Test Organization",
                    "id": "test-tenant-id",
                    "verifiedDomains": [
                        {"name": "test.com", "isVerified": True, "isDefault": True}
                    ]
                }]
            }
            
            # Mock audit logs endpoint (permission check)
            audit_response = MagicMock()
            audit_response.status_code = 200
            audit_response.json.return_value = {"value": []}
            
            mock_get.side_effect = [org_response, audit_response]
            
            result = await client.health_check(required_permissions=["AuditLog.Read.All"])
            
            assert result["status"] == "healthy"
            assert result["connectivity"]["success"] is True
            assert result["authentication"]["success"] is True
            assert result["permissions"]["success"] is True
            assert "AuditLog.Read.All" in result["permissions"]["granted"]
            assert result["tenant_info"]["display_name"] == "Test Organization"
            assert "test.com" in result["tenant_info"]["verified_domains"]
            assert result["connectivity"]["latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_health_check_invalid_credentials(self, client, mock_msal_app):
        """Test health check with invalid credentials."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Client authentication failed. Check credentials."
        }
        
        result = await client.health_check(required_permissions=["AuditLog.Read.All"])
        
        assert result["status"] == "error"
        assert result["authentication"]["success"] is False
        assert "Client authentication failed" in result["authentication"]["error"]
        assert result["authentication"]["error_code"] == "invalid_client"
        assert result["connectivity"]["success"] is False

    @pytest.mark.asyncio
    async def test_health_check_insufficient_permissions(self, client, mock_msal_app):
        """Test health check with missing AuditLog.Read.All permission."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            # Mock organization endpoint (success)
            org_response = MagicMock()
            org_response.status_code = 200
            org_response.json.return_value = {
                "value": [{
                    "displayName": "Test Organization",
                    "id": "test-tenant-id",
                    "verifiedDomains": []
                }]
            }
            
            # Mock audit logs endpoint (403 - permission denied)
            audit_response = MagicMock()
            audit_response.status_code = 403
            audit_response.text = "Forbidden"
            
            mock_get.side_effect = [org_response, audit_response]
            
            result = await client.health_check(required_permissions=["AuditLog.Read.All"])
            
            assert result["status"] == "unhealthy"
            assert result["authentication"]["success"] is True
            assert result["permissions"]["success"] is False
            assert "AuditLog.Read.All" in result["permissions"]["missing"]
            assert "AuditLog.Read.All" not in result["permissions"]["granted"]

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, client, mock_msal_app):
        """Test health check timeout handling."""
        import asyncio
        
        # Mock token acquisition to timeout
        async def slow_token(*args, **kwargs):
            await asyncio.sleep(35)  # Longer than default 30s timeout
            return "token"
        
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent = Mock(return_value=None)
        mock_app.acquire_token_for_client = Mock(return_value={"access_token": "token"})
        
        # Use a short timeout for faster test
        client.timeout = 0.1
        
        with patch.object(client, "get_access_token", side_effect=asyncio.TimeoutError):
            result = await client.health_check(required_permissions=["AuditLog.Read.All"])
            
            assert result["status"] == "timeout"
            assert result["authentication"]["success"] is False
            assert "timed out" in result["authentication"]["error"].lower()

    @pytest.mark.asyncio
    async def test_health_check_no_permissions_required(self, client, mock_msal_app):
        """Test health check when no permissions are required to check."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            org_response = MagicMock()
            org_response.status_code = 200
            org_response.json.return_value = {
                "value": [{
                    "displayName": "Test Organization",
                    "id": "test-tenant-id",
                    "verifiedDomains": []
                }]
            }
            mock_get.return_value = org_response
            
            result = await client.health_check(required_permissions=None)
            
            assert result["status"] == "healthy"
            assert result["permissions"]["success"] is True  # No permissions to check = success
            assert result["permissions"]["granted"] == []
            assert result["permissions"]["missing"] == []

    @pytest.mark.asyncio
    async def test_health_check_throttled(self, client, mock_msal_app):
        """Test health check when MSAL request is throttled."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        # Simulate throttling with a generic exception containing throttle message
        mock_app.acquire_token_for_client.side_effect = Exception(
            "Request throttled - 429 Too Many Requests"
        )
        
        result = await client.health_check(required_permissions=["AuditLog.Read.All"])
        
        assert result["status"] == "error"
        assert result["authentication"]["success"] is False
        assert "throttled" in result["authentication"]["error"].lower()

    @pytest.mark.asyncio
    async def test_check_permissions_success(self, client, mock_msal_app):
        """Test permission check with all permissions granted."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            audit_response = MagicMock()
            audit_response.status_code = 200
            audit_response.json.return_value = {"value": []}
            mock_get.return_value = audit_response
            
            result = await client.check_permissions(["AuditLog.Read.All"])
            
            assert result["has_permissions"] is True
            assert "AuditLog.Read.All" in result["granted_permissions"]
            assert result["missing_permissions"] == []
            assert result["details"]["AuditLog.Read.All"]["granted"] is True

    @pytest.mark.asyncio
    async def test_check_permissions_forbidden(self, client, mock_msal_app):
        """Test permission check when permission is not granted."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            audit_response = MagicMock()
            audit_response.status_code = 403
            audit_response.text = "Forbidden"
            mock_get.return_value = audit_response
            
            result = await client.check_permissions(["AuditLog.Read.All"])
            
            assert result["has_permissions"] is False
            assert "AuditLog.Read.All" not in result["granted_permissions"]
            assert "AuditLog.Read.All" in result["missing_permissions"]
            assert result["details"]["AuditLog.Read.All"]["granted"] is False
            assert "Permission not granted" in result["details"]["AuditLog.Read.All"]["error"]

    @pytest.mark.asyncio
    async def test_check_permissions_unimplemented_permission(self, client, mock_msal_app):
        """Test permission check for unimplemented permission type."""
        mock_app = mock_msal_app.return_value
        mock_app.acquire_token_silent.return_value = None
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock):
            result = await client.check_permissions(["Some.Other.Permission"])
            
            assert result["has_permissions"] is True  # Unknown = not checked
            assert "Some.Other.Permission" not in result["granted_permissions"]
            assert "Some.Other.Permission" not in result["missing_permissions"]
            assert result["details"]["Some.Other.Permission"]["test_result"] == "not_implemented"


class TestTenantServiceHealthCheck:
    """Test cases for TenantService health check functionality."""

    @pytest.fixture
    async def service(self, mock_db):
        """Create a tenant service with mocked database."""
        from src.services.tenant import TenantService
        return TenantService(mock_db)

    @pytest.fixture
    def mock_tenant(self):
        """Create a mock tenant model."""
        tenant = MagicMock()
        tenant.id = "test-tenant-uuid"
        tenant.tenant_id = "test-tenant-id"
        tenant.client_id = "test-client-id"
        tenant.client_secret = "encrypted-secret"
        tenant.name = "Test Tenant"
        tenant.is_active = True
        tenant.connection_status = "unknown"
        tenant.connection_error = None
        tenant.last_health_check = None
        return tenant

    @pytest.mark.asyncio
    async def test_health_check_tenant_success(self, mock_db, mock_tenant):
        """Test successful health check through TenantService."""
        from src.services.tenant import TenantService
        
        # Setup mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        service = TenantService(mock_db)
        
        with patch.object(service, "get_decrypted_secret", return_value="decrypted-secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "healthy",
                    "connectivity": {"success": True, "latency_ms": 150.5, "error": None},
                    "authentication": {"success": True, "error": None},
                    "permissions": {
                        "success": True,
                        "granted": ["AuditLog.Read.All"],
                        "missing": [],
                        "details": {"AuditLog.Read.All": {"granted": True}}
                    },
                    "tenant_info": {
                        "display_name": "Test Organization",
                        "tenant_id": "test-tenant-id",
                        "verified_domains": ["test.com"]
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                result = await service.health_check_tenant("test-tenant-uuid")
                
                assert result.status == "healthy"
                assert result.connectivity.success is True
                assert result.connectivity.latency_ms == 150.5
                assert result.authentication.success is True
                assert result.permissions.success is True
                assert "AuditLog.Read.All" in result.permissions.granted
                assert result.tenant_info.display_name == "Test Organization"
                
                # Verify tenant status was updated
                assert mock_tenant.connection_status == "healthy"
                assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_health_check_tenant_not_found(self, mock_db):
        """Test health check when tenant doesn't exist."""
        from src.services.tenant import TenantService, TenantNotFoundError
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        service = TenantService(mock_db)
        
        with pytest.raises(TenantNotFoundError) as exc_info:
            await service.health_check_tenant("non-existent-uuid")
        
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_tenant_invalid_credentials(self, mock_db, mock_tenant):
        """Test health check with invalid credentials."""
        from src.services.tenant import TenantService
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        service = TenantService(mock_db)
        
        with patch.object(service, "get_decrypted_secret", return_value="decrypted-secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "error",
                    "connectivity": {"success": False, "latency_ms": 0, "error": None},
                    "authentication": {
                        "success": False,
                        "error": "Client authentication failed",
                        "error_code": "invalid_client"
                    },
                    "permissions": {"success": False, "granted": [], "missing": []},
                    "tenant_info": {},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                result = await service.health_check_tenant("test-tenant-uuid")
                
                assert result.status == "error"
                assert result.authentication.success is False
                assert "Client authentication failed" in result.authentication.error
                
                # Verify tenant status was updated
                assert mock_tenant.connection_status == "error"
                assert mock_tenant.connection_error is not None

    @pytest.mark.asyncio
    async def test_health_check_tenant_timeout(self, mock_db, mock_tenant):
        """Test health check timeout handling."""
        from src.services.tenant import TenantService
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        service = TenantService(mock_db)
        
        with patch.object(service, "get_decrypted_secret", return_value="decrypted-secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "timeout",
                    "connectivity": {
                        "success": False,
                        "latency_ms": 0,
                        "error": "Connection timed out after 30s"
                    },
                    "authentication": {
                        "success": False,
                        "error": "Authentication timed out after 30s"
                    },
                    "permissions": {"success": False, "granted": [], "missing": []},
                    "tenant_info": {},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                result = await service.health_check_tenant("test-tenant-uuid")
                
                assert result.status == "timeout"
                assert result.connectivity.success is False
                assert "timed out" in result.connectivity.error.lower()
                
                # Verify tenant status was updated
                assert mock_tenant.connection_status == "timeout"
                assert "timed out" in mock_tenant.connection_error.lower()

    @pytest.mark.asyncio
    async def test_health_check_tenant_insufficient_permissions(self, mock_db, mock_tenant):
        """Test health check with insufficient permissions."""
        from src.services.tenant import TenantService
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        service = TenantService(mock_db)
        
        with patch.object(service, "get_decrypted_secret", return_value="decrypted-secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "unhealthy",
                    "connectivity": {"success": True, "latency_ms": 200.0, "error": None},
                    "authentication": {"success": True, "error": None},
                    "permissions": {
                        "success": False,
                        "granted": [],
                        "missing": ["AuditLog.Read.All"],
                        "details": {
                            "AuditLog.Read.All": {
                                "granted": False,
                                "error": "Permission not granted or admin consent required"
                            }
                        },
                        "error": None
                    },
                    "tenant_info": {
                        "display_name": "Test Organization",
                        "tenant_id": "test-tenant-id",
                        "verified_domains": ["test.com"]
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                result = await service.health_check_tenant("test-tenant-uuid")
                
                assert result.status == "unhealthy"
                assert result.permissions.success is False
                assert "AuditLog.Read.All" in result.permissions.missing
                
                # Verify tenant status was updated
                assert mock_tenant.connection_status == "unhealthy"
                assert "Missing permissions" in mock_tenant.connection_error
                assert "AuditLog.Read.All" in mock_tenant.connection_error


class TestHealthCheckAPI:
    """Test cases for health check API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint_success(self, async_client, mock_db):
        """Test successful health check API call."""
        from datetime import datetime, timezone
        
        mock_tenant = MagicMock()
        mock_tenant.id = "test-tenant-uuid"
        mock_tenant.tenant_id = "ms-tenant-id"
        mock_tenant.client_id = "client-id"
        mock_tenant.client_secret = "encrypted"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        with patch("src.services.tenant.TenantService.get_decrypted_secret", return_value="secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "healthy",
                    "connectivity": {"success": True, "latency_ms": 100.0, "error": None},
                    "authentication": {"success": True, "error": None},
                    "permissions": {
                        "success": True,
                        "granted": ["AuditLog.Read.All"],
                        "missing": []
                    },
                    "tenant_info": {
                        "display_name": "Test Org",
                        "tenant_id": "ms-tenant-id",
                        "verified_domains": ["test.com"]
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                response = await async_client.post("/api/v1/tenants/test-tenant-uuid/health-check")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["connectivity"]["success"] is True
                assert data["permissions"]["success"] is True

    @pytest.mark.asyncio
    async def test_health_check_endpoint_not_found(self, async_client, mock_db):
        """Test health check API when tenant not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        response = await async_client.post("/api/v1/tenants/non-existent/health-check")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_health_check_all_tenants(self, async_client, mock_db):
        """Test bulk health check endpoint."""
        from datetime import datetime, timezone
        
        mock_tenant = MagicMock()
        mock_tenant.id = "tenant-uuid"
        mock_tenant.name = "Test Tenant"
        mock_tenant.tenant_id = "ms-tenant-id"
        mock_tenant.client_id = "client-id"
        mock_tenant.client_secret = "encrypted"
        mock_tenant.is_active = True
        mock_tenant.connection_status = "unknown"
        mock_tenant.connection_error = None
        mock_tenant.last_health_check = None
        mock_tenant.created_at = datetime.now(timezone.utc)
        mock_tenant.updated_at = datetime.now(timezone.utc)
        
        # Mock list query
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [mock_tenant]
        
        # Mock get query
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = mock_tenant
        
        mock_db.execute.side_effect = [mock_list_result, mock_get_result]
        
        with patch("src.services.tenant.TenantService.get_decrypted_secret", return_value="secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "healthy",
                    "connectivity": {"success": True, "latency_ms": 100.0, "error": None},
                    "authentication": {"success": True, "error": None},
                    "permissions": {
                        "success": True,
                        "granted": ["AuditLog.Read.All"],
                        "missing": []
                    },
                    "tenant_info": {
                        "display_name": "Test Org",
                        "tenant_id": "ms-tenant-id",
                        "verified_domains": ["test.com"]
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                response = await async_client.post("/api/v1/tenants/health-check/all")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_with_custom_permissions(self, async_client, mock_db):
        """Test health check with custom permissions parameter."""
        from datetime import datetime, timezone
        
        mock_tenant = MagicMock()
        mock_tenant.id = "test-tenant-uuid"
        mock_tenant.tenant_id = "ms-tenant-id"
        mock_tenant.client_id = "client-id"
        mock_tenant.client_secret = "encrypted"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        with patch("src.services.tenant.TenantService.get_decrypted_secret", return_value="secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "healthy",
                    "connectivity": {"success": True, "latency_ms": 100.0, "error": None},
                    "authentication": {"success": True, "error": None},
                    "permissions": {
                        "success": True,
                        "granted": ["Custom.Permission"],
                        "missing": []
                    },
                    "tenant_info": {"display_name": "Test Org"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                response = await async_client.post(
                    "/api/v1/tenants/test-tenant-uuid/health-check",
                    params={"permissions": ["Custom.Permission"], "timeout": 45.0}
                )
                
                assert response.status_code == 200
                # Verify the client was called with custom permissions
                mock_client.health_check.assert_called_once()
                call_args = mock_client.health_check.call_args
                assert call_args.kwargs["required_permissions"] == ["Custom.Permission"]

    @pytest.mark.asyncio
    async def test_health_check_with_custom_timeout(self, async_client, mock_db):
        """Test health check with custom timeout parameter."""
        from datetime import datetime, timezone
        
        mock_tenant = MagicMock()
        mock_tenant.id = "test-tenant-uuid"
        mock_tenant.tenant_id = "ms-tenant-id"
        mock_tenant.client_id = "client-id"
        mock_tenant.client_secret = "encrypted"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        with patch("src.services.tenant.TenantService.get_decrypted_secret", return_value="secret"):
            with patch("src.clients.ms_graph.MSGraphClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.health_check = AsyncMock(return_value={
                    "status": "healthy",
                    "connectivity": {"success": True, "latency_ms": 100.0, "error": None},
                    "authentication": {"success": True, "error": None},
                    "permissions": {"success": True, "granted": ["AuditLog.Read.All"], "missing": []},
                    "tenant_info": {"display_name": "Test Org"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                mock_client_class.return_value = mock_client
                
                response = await async_client.post(
                    "/api/v1/tenants/test-tenant-uuid/health-check",
                    params={"timeout": 60.0}
                )
                
                assert response.status_code == 200
                # Verify timeout was passed correctly
                mock_client_class.assert_called_once()
                assert mock_client_class.call_args.kwargs["timeout"] == 60.0