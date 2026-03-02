"""Unit tests for mailbox rules API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.mailbox_rules import (
    AcknowledgeAlertRequest,
    ScanRequest,
    acknowledge_alert,
    get_mailbox_rule,
    get_rules_summary,
    get_suspicious_rules,
    get_tenant_mailbox_rules,
    list_mailbox_rule_alerts,
    list_mailbox_rules,
    scan_mailbox_rules,
)
from src.models.mailbox_rules import (
    MailboxRuleAlertModel,
    MailboxRuleModel,
    RuleSeverity,
    RuleStatus,
    RuleType,
)


class TestMailboxRulesEndpoints:
    """Test cases for mailbox rules API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock mailbox rule service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def sample_rule(self):
        """Return a sample mailbox rule."""
        rule = MagicMock(spec=MailboxRuleModel)
        rule.id = uuid4()
        rule.tenant_id = str(uuid4())
        rule.user_email = "user@example.com"
        rule.rule_id = "rule-123"
        rule.rule_name = "Test Rule"
        rule.rule_type = RuleType.FORWARDING
        rule.is_enabled = True
        rule.status = RuleStatus.SUSPICIOUS
        rule.severity = RuleSeverity.MEDIUM
        rule.forward_to = "external@gmail.com"
        rule.forward_to_external = True
        rule.external_domain = "gmail.com"
        rule.redirect_to = None
        rule.is_hidden_folder_redirect = False
        rule.has_suspicious_patterns = False
        rule.created_outside_business_hours = False
        rule.created_by_non_owner = False
        rule.created_by = None
        rule.detection_reasons = ["Forwarding to external email address"]
        rule.rule_created_at = datetime.utcnow()
        rule.rule_modified_at = datetime.utcnow()
        rule.last_scan_at = datetime.utcnow()
        rule.created_at = datetime.utcnow()
        rule.updated_at = datetime.utcnow()
        return rule

    @pytest.fixture
    def sample_alert(self):
        """Return a sample mailbox rule alert."""
        alert = MagicMock(spec=MailboxRuleAlertModel)
        alert.id = uuid4()
        alert.rule_id = uuid4()
        alert.tenant_id = str(uuid4())
        alert.user_email = "user@example.com"
        alert.alert_type = "mailbox_forwarding_external"
        alert.severity = RuleSeverity.HIGH
        alert.title = "Suspicious Mailbox Rule Detected"
        alert.description = "Forwards emails to external address"
        alert.is_acknowledged = False
        alert.acknowledged_by = None
        alert.acknowledged_at = None
        alert.created_at = datetime.utcnow()
        return alert

    @pytest.mark.asyncio
    async def test_list_mailbox_rules_success(self, mock_service, sample_rule):
        """Test successful listing of mailbox rules."""
        mock_service.get_rules.return_value = {
            "items": [sample_rule],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await list_mailbox_rules(
            tenant_id=None,
            user_email=None,
            status=None,
            severity=None,
            rule_type=None,
            limit=100,
            offset=0,
            service=mock_service,
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].rule_name == "Test Rule"
        mock_service.get_rules.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_mailbox_rules_with_filters(self, mock_service, sample_rule):
        """Test listing mailbox rules with filters."""
        mock_service.get_rules.return_value = {
            "items": [sample_rule],
            "total": 1,
            "limit": 50,
            "offset": 10,
        }

        result = await list_mailbox_rules(
            tenant_id="tenant-123",
            user_email="user@example.com",
            status="suspicious",
            severity="HIGH",
            rule_type="forwarding",
            limit=50,
            offset=10,
            service=mock_service,
        )

        assert result.limit == 50
        assert result.offset == 10
        mock_service.get_rules.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_mailbox_rules_invalid_status(self, mock_service):
        """Test listing with invalid status filter."""
        with pytest.raises(HTTPException) as exc_info:
            await list_mailbox_rules(
                tenant_id=None,
                user_email=None,
                status="invalid_status",
                severity=None,
                rule_type=None,
                limit=100,
                offset=0,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid status" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_mailbox_rules_invalid_severity(self, mock_service):
        """Test listing with invalid severity filter."""
        with pytest.raises(HTTPException) as exc_info:
            await list_mailbox_rules(
                tenant_id=None,
                user_email=None,
                status=None,
                severity="invalid",
                rule_type=None,
                limit=100,
                offset=0,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_mailbox_rule_success(self, mock_service, sample_rule):
        """Test getting a specific mailbox rule."""
        mock_service.get_rule_by_id.return_value = sample_rule

        result = await get_mailbox_rule(
            rule_id=str(sample_rule.id),
            service=mock_service,
        )

        assert result.rule_name == "Test Rule"
        assert result.id == str(sample_rule.id)

    @pytest.mark.asyncio
    async def test_get_mailbox_rule_not_found(self, mock_service):
        """Test getting a non-existent mailbox rule."""
        mock_service.get_rule_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_mailbox_rule(
                rule_id="non-existent",
                service=mock_service,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tenant_mailbox_rules_success(self, mock_service, sample_rule):
        """Test getting tenant mailbox rules."""
        mock_service.get_rules.return_value = {
            "items": [sample_rule],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await get_tenant_mailbox_rules(
            tenant_id="tenant-123",
            status=None,
            severity=None,
            limit=100,
            offset=0,
            service=mock_service,
        )

        assert result.total == 1
        mock_service.get_rules.assert_called_once_with(
            tenant_id="tenant-123",
            status=None,
            severity=None,
            limit=100,
            offset=0
        )

    @pytest.mark.asyncio
    async def test_get_suspicious_rules_success(self, mock_service, sample_rule):
        """Test getting suspicious rules."""
        mock_service.get_suspicious_rules.return_value = [sample_rule]

        result = await get_suspicious_rules(
            tenant_id="tenant-123",
            limit=100,
            service=mock_service,
        )

        assert len(result) == 1
        assert result[0].rule_name == "Test Rule"

    @pytest.mark.asyncio
    async def test_scan_mailbox_rules_success(self, mock_service):
        """Test successful mailbox rule scan."""
        mock_service.scan_tenant_mailbox_rules.return_value = {
            "total_rules": 10,
            "new_rules": 5,
            "updated_rules": 3,
            "suspicious_rules": 2,
            "malicious_rules": 0,
            "alerts_triggered": 2,
        }

        request = ScanRequest(tenant_id="tenant-123", trigger_alerts=True)

        result = await scan_mailbox_rules(
            request=request,
            service=mock_service,
        )

        assert result.success is True
        assert result.results["total_rules"] == 10
        assert result.results["suspicious_rules"] == 2

    @pytest.mark.asyncio
    async def test_scan_mailbox_rules_missing_tenant(self, mock_service):
        """Test scan without tenant ID."""
        request = ScanRequest(tenant_id=None, trigger_alerts=True)

        with pytest.raises(HTTPException) as exc_info:
            await scan_mailbox_rules(
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400
        assert "tenant_id is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_scan_mailbox_rules_tenant_not_found(self, mock_service):
        """Test scan with non-existent tenant."""
        mock_service.scan_tenant_mailbox_rules.side_effect = ValueError("Tenant not-found-id not found")

        request = ScanRequest(tenant_id="not-found-id", trigger_alerts=True)

        with pytest.raises(HTTPException) as exc_info:
            await scan_mailbox_rules(
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_scan_mailbox_rules_error(self, mock_service):
        """Test scan with unexpected error."""
        mock_service.scan_tenant_mailbox_rules.side_effect = Exception("Database error")

        request = ScanRequest(tenant_id="tenant-123", trigger_alerts=True)

        with pytest.raises(HTTPException) as exc_info:
            await scan_mailbox_rules(
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 500
        assert "Scan failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_mailbox_rule_alerts_success(self, mock_service, sample_alert):
        """Test listing mailbox rule alerts."""
        mock_service.get_alerts.return_value = {
            "items": [sample_alert],
            "total": 1,
            "limit": 100,
            "offset": 0,
        }

        result = await list_mailbox_rule_alerts(
            tenant_id="tenant-123",
            acknowledged=False,
            severity=None,
            limit=100,
            offset=0,
            service=mock_service,
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].title == "Suspicious Mailbox Rule Detected"

    @pytest.mark.asyncio
    async def test_list_mailbox_rule_alerts_invalid_severity(self, mock_service):
        """Test listing alerts with invalid severity."""
        with pytest.raises(HTTPException) as exc_info:
            await list_mailbox_rule_alerts(
                tenant_id=None,
                acknowledged=None,
                severity="INVALID",
                limit=100,
                offset=0,
                service=mock_service,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_acknowledge_alert_success(self, mock_service, sample_alert):
        """Test successfully acknowledging an alert."""
        sample_alert.is_acknowledged = True
        sample_alert.acknowledged_by = "admin@example.com"
        mock_service.acknowledge_alert.return_value = sample_alert

        request = AcknowledgeAlertRequest(acknowledged_by="admin@example.com")

        result = await acknowledge_alert(
            alert_id=str(sample_alert.id),
            request=request,
            service=mock_service,
        )

        assert result.success is True
        assert result.alert.is_acknowledged is True
        assert result.alert.acknowledged_by == "admin@example.com"

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, mock_service):
        """Test acknowledging a non-existent alert."""
        mock_service.acknowledge_alert.return_value = None

        request = AcknowledgeAlertRequest(acknowledged_by="admin@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await acknowledge_alert(
                alert_id="non-existent",
                request=request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_rules_summary(self, mock_service, sample_rule):
        """Test getting rules summary."""
        mock_service.get_suspicious_rules.return_value = [sample_rule]
        mock_service.get_alerts.return_value = {"total": 5, "items": []}

        result = await get_rules_summary(
            tenant_id="tenant-123",
            service=mock_service,
        )

        assert result.total_suspicious + result.total_malicious >= 0
        assert "by_severity" in result.model_dump()
        assert "by_type" in result.model_dump()
