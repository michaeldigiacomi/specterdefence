"""Unit tests for Conditional Access policies service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from uuid import uuid4

from src.services.ca_policies import CAPoliciesService
from src.models.ca_policies import (
    CAPolicyModel,
    CAPolicyChangeModel,
    CAPolicyAlertModel,
    CABaselineConfigModel,
    PolicyState,
    ChangeType,
    AlertSeverity,
)
from src.models.alerts import SeverityLevel, EventType


class TestCAPoliciesService:
    """Test cases for CAPoliciesService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def service(self, mock_db_session):
        """Create a CAPoliciesService instance."""
        return CAPoliciesService(mock_db_session)
    
    @pytest.fixture
    def sample_tenant(self):
        """Return a sample tenant."""
        tenant = MagicMock()
        tenant.id = str(uuid4())
        tenant.tenant_id = "ms-tenant-123"
        tenant.name = "Test Tenant"
        tenant.client_id = "client-123"
        tenant.client_secret = "encrypted-secret"
        return tenant
    
    @pytest.fixture
    def sample_policy_data(self):
        """Return sample policy data from Graph API."""
        return {
            "id": "policy-123",
            "displayName": "Require MFA for Admins",
            "description": "Require MFA for all admin accounts",
            "state": "enabled",
            "createdDateTime": "2024-01-15T10:30:00Z",
            "modifiedDateTime": "2024-01-20T14:45:00Z",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {
                "operator": "OR",
                "builtInControls": ["mfa"],
            },
        }
    
    @pytest.fixture
    def sample_analysis(self):
        """Return sample policy analysis."""
        return {
            "state": "enabled",
            "is_enabled": True,
            "is_disabled": False,
            "is_report_only": False,
            "grant_controls": ["mfa"],
            "grant_controls_operator": "OR",
            "is_mfa_required": True,
            "requires_compliant_device": False,
            "requires_hybrid_joined_device": False,
            "has_session_controls": False,
            "sign_in_frequency": None,
            "applies_to_all_users": True,
            "includes_guests_or_external": False,
            "includes_vip_users": False,
            "applies_to_all_apps": True,
            "excluded_users_count": 0,
            "excluded_groups_count": 0,
            "requires_high_risk_level": False,
            "requires_medium_risk_level": False,
            "requires_low_risk_level": False,
            "has_risk_conditions": False,
            "has_location_conditions": False,
            "trusted_locations_only": False,
            "has_device_conditions": False,
            "includes_mobile_platforms": False,
            "security_score": 50,
        }
    
    def test_service_initialization(self, mock_db_session):
        """Test service initialization."""
        service = CAPoliciesService(mock_db_session)
        assert service.db == mock_db_session
    
    def test_severity_mapping(self, service):
        """Test severity level mapping."""
        assert service.SEVERITY_MAPPING["critical"] == AlertSeverity.CRITICAL
        assert service.SEVERITY_MAPPING["high"] == AlertSeverity.HIGH
        assert service.SEVERITY_MAPPING["medium"] == AlertSeverity.MEDIUM
        assert service.SEVERITY_MAPPING["low"] == AlertSeverity.LOW
        assert service.SEVERITY_MAPPING["none"] == AlertSeverity.LOW
    
    @pytest.mark.asyncio
    async def test_scan_tenant_policies_tenant_not_found(self, service):
        """Test scan with non-existent tenant."""
        with patch.object(service, "_get_tenant", return_value=None):
            with pytest.raises(ValueError, match="Tenant.*not found"):
                await service.scan_tenant_policies("nonexistent-tenant-id")
    
    @pytest.mark.asyncio
    async def test_set_baseline_config_create_new(self, service):
        """Test creating new baseline configuration."""
        config_data = {
            "require_mfa_for_admins": True,
            "require_mfa_for_all_users": False,
            "block_legacy_auth": True,
            "require_compliant_or_hybrid_joined": False,
            "block_high_risk_signins": True,
            "block_unknown_locations": False,
            "require_mfa_for_guests": True,
            "custom_requirements": {},
        }
        
        # Mock _get_baseline_config to return None (no existing config)
        with patch.object(service, "_get_baseline_config", return_value=None):
            result = await service.set_baseline_config(
                tenant_id="tenant-1",
                config_data=config_data,
                created_by="test-user"
            )
        
        assert result.require_mfa_for_admins is True
        assert result.require_mfa_for_all_users is False
        assert result.created_by == "test-user"
    
    @pytest.mark.asyncio
    async def test_set_baseline_config_update_existing(self, service):
        """Test updating existing baseline configuration."""
        # Create existing config mock
        existing = MagicMock(spec=CABaselineConfigModel)
        existing.tenant_id = "tenant-1"
        existing.require_mfa_for_admins = True
        existing.require_mfa_for_all_users = False
        
        # Update config
        config_data = {
            "require_mfa_for_admins": False,
            "require_mfa_for_all_users": True,
        }
        
        with patch.object(service, "_get_baseline_config", return_value=existing):
            result = await service.set_baseline_config(
                tenant_id="tenant-1",
                config_data=config_data
            )
        
        assert result.require_mfa_for_admins is False
        assert result.require_mfa_for_all_users is True
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, service):
        """Test acknowledging an alert."""
        # Create mock alert
        alert = MagicMock(spec=CAPolicyAlertModel)
        alert.id = uuid4()
        alert.is_acknowledged = False
        alert.acknowledged_by = None
        alert.acknowledged_at = None
        
        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=alert)
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.acknowledge_alert(
            alert_id=str(alert.id),
            acknowledged_by="test-user"
        )
        
        assert result is not None
        assert result.is_acknowledged is True
        assert result.acknowledged_by == "test-user"
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, service):
        """Test acknowledging a non-existent alert."""
        # Mock the query result to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.acknowledge_alert(
            alert_id="nonexistent-id",
            acknowledged_by="test-user"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_policy_by_id(self, service):
        """Test getting a policy by ID."""
        # Create mock policy
        policy = MagicMock(spec=CAPolicyModel)
        policy.id = uuid4()
        policy.display_name = "Test Policy"
        
        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=policy)
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_policy_by_id(str(policy.id))
        
        assert result is not None
        assert result.display_name == "Test Policy"
    
    @pytest.mark.asyncio
    async def test_get_policy_by_id_not_found(self, service):
        """Test getting a non-existent policy."""
        # Mock the query result to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_policy_by_id("nonexistent-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_record_change(self, service):
        """Test recording a policy change."""
        policy_id = uuid4()
        
        result = await service._record_change(
            policy_id=policy_id,
            tenant_id="tenant-1",
            change_type=ChangeType.UPDATED,
            changes_summary=["Test change"],
            security_impact="medium",
            mfa_removed=False,
        )
        
        assert result is not None
        assert result.change_type == ChangeType.UPDATED
        assert result.security_impact == "medium"
