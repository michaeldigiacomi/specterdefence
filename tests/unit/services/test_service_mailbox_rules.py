"""Unit tests for mailbox rules service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.alerts import EventType, SeverityLevel
from src.models.mailbox_rules import (
    MailboxRuleAlertModel,
    MailboxRuleModel,
    RuleSeverity,
    RuleStatus,
    RuleType,
)
from src.services.mailbox_rules import MailboxRuleService


class TestMailboxRuleService:
    """Test cases for MailboxRuleService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        """Create a MailboxRuleService instance."""
        return MailboxRuleService(mock_db_session)

    @pytest.fixture
    def sample_tenant(self):
        """Return a sample tenant model."""
        tenant = MagicMock()
        tenant.id = str(uuid4())
        tenant.name = "Test Tenant"
        tenant.tenant_id = "ms-tenant-123"
        tenant.client_id = "client-123"
        tenant.client_secret = "encrypted-secret"
        return tenant

    @pytest.fixture
    def sample_rule_data(self):
        """Return sample rule data from Graph API."""
        return {
            "id": "rule-123",
            "displayName": "Forward to External",
            "isEnabled": True,
            "createdDateTime": "2024-01-15T10:30:00Z",
            "actions": {"forwardTo": [{"emailAddress": {"address": "external@gmail.com"}}]},
            "_user_email": "user@example.com",
        }

    @pytest.fixture
    def sample_analysis(self):
        """Return sample rule analysis."""
        return {
            "rule_type": "forwarding",
            "is_forwarding": True,
            "forward_to": "external@gmail.com",
            "forward_to_external": True,
            "external_domain": "gmail.com",
            "is_redirect": False,
            "is_auto_reply": False,
            "is_hidden_folder_redirect": False,
            "has_suspicious_patterns": False,
            "created_outside_business_hours": False,
            "detection_reasons": ["Forwarding to external email address"],
            "severity": "MEDIUM",
            "status": "suspicious",
        }

    @pytest.fixture
    def sample_mailbox_rule(self):
        """Return a sample mailbox rule model."""
        rule = MagicMock(spec=MailboxRuleModel)
        rule.id = uuid4()
        rule.tenant_id = str(uuid4())
        rule.user_email = "user@example.com"
        rule.rule_id = "rule-123"
        rule.rule_name = "Test Rule"
        rule.rule_type = RuleType.FORWARDING
        rule.status = RuleStatus.SUSPICIOUS
        rule.severity = RuleSeverity.MEDIUM
        rule.forward_to = "external@gmail.com"
        rule.forward_to_external = True
        rule.is_hidden_folder_redirect = False
        rule.has_suspicious_patterns = False
        rule.created_outside_business_hours = False
        rule.created_by_non_owner = False
        rule.detection_reasons = ["Forwarding to external email address"]
        rule.generate_alert_title.return_value = "Suspicious Mailbox Rule Detected: Test Rule"
        rule.generate_alert_description.return_value = "Forwards emails to external address"
        return rule

    @pytest.mark.asyncio
    async def test_scan_tenant_mailbox_rules_success(self, service, sample_tenant):
        """Test successful tenant mailbox rule scan."""
        # Mock tenant retrieval
        with patch.object(service, "_get_tenant", return_value=sample_tenant):
            with patch("src.services.mailbox_rules.MSGraphClient"):
                with patch(
                    "src.services.mailbox_rules.MailboxRuleClient"
                ) as mock_rule_client_class:
                    with patch(
                        "src.services.mailbox_rules.encryption_service.decrypt",
                        return_value="secret",
                    ):
                        mock_rule_client = MagicMock()
                        mock_rule_client.get_mailbox_rules_for_tenant = AsyncMock(return_value=[])
                        mock_rule_client_class.return_value = mock_rule_client

                        results = await service.scan_tenant_mailbox_rules(sample_tenant.id)

        assert results["total_rules"] == 0
        assert results["new_rules"] == 0

    @pytest.mark.asyncio
    async def test_scan_tenant_mailbox_rules_tenant_not_found(self, service):
        """Test scan with non-existent tenant."""
        with patch.object(service, "_get_tenant", return_value=None):
            with pytest.raises(ValueError, match="Tenant .* not found"):
                await service.scan_tenant_mailbox_rules("non-existent-id")

    @pytest.mark.asyncio
    async def test_process_rule_new_rule(self, service, sample_rule_data, sample_analysis):
        """Test processing a new rule."""
        tenant_id = str(uuid4())

        with patch.object(service, "_get_existing_rule", return_value=None):
            with patch.object(service, "_create_rule") as mock_create:
                mock_rule = MagicMock(spec=MailboxRuleModel)
                mock_rule.status = RuleStatus.SUSPICIOUS
                mock_create.return_value = mock_rule

                with patch.object(service, "_trigger_alert"):
                    mock_rule_client = MagicMock()
                    mock_rule_client.analyze_rule.return_value = sample_analysis

                    result = await service._process_rule(
                        tenant_id=tenant_id,
                        rule_data=sample_rule_data,
                        rule_client=mock_rule_client,
                        trigger_alerts=True,
                    )

        assert result["is_new"] is True
        assert result["is_updated"] is False
        assert result["alert_triggered"] is True

    @pytest.mark.asyncio
    async def test_process_rule_existing_rule(self, service, sample_rule_data, sample_analysis):
        """Test processing an existing rule."""
        tenant_id = str(uuid4())
        existing_rule = MagicMock(spec=MailboxRuleModel)
        existing_rule.status = RuleStatus.BENIGN

        with patch.object(service, "_get_existing_rule", return_value=existing_rule):
            with patch.object(service, "_update_rule") as mock_update:
                mock_rule_client = MagicMock()
                mock_rule_client.analyze_rule.return_value = sample_analysis

                result = await service._process_rule(
                    tenant_id=tenant_id,
                    rule_data=sample_rule_data,
                    rule_client=mock_rule_client,
                    trigger_alerts=False,
                )

        assert result["is_new"] is False
        assert result["is_updated"] is True
        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_rule(self, service, sample_rule_data, sample_analysis):
        """Test creating a mailbox rule record."""
        tenant_id = str(uuid4())
        user_email = "user@example.com"

        result = await service._create_rule(
            tenant_id, user_email, sample_rule_data, sample_analysis
        )

        assert result.tenant_id == tenant_id
        assert result.user_email == user_email
        assert result.rule_id == "rule-123"
        assert result.rule_type == RuleType.FORWARDING
        assert result.forward_to_external is True
        assert result.external_domain == "gmail.com"
        service.db.add.assert_called_once_with(result)
        service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_rule(
        self, service, sample_mailbox_rule, sample_rule_data, sample_analysis
    ):
        """Test updating a mailbox rule record."""
        await service._update_rule(sample_mailbox_rule, sample_rule_data, sample_analysis)

        service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_alert(self, service, sample_mailbox_rule):
        """Test triggering an alert."""
        with patch("src.services.mailbox_rules.AlertEngine") as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine
            mock_engine.process_event = AsyncMock()

            await service._trigger_alert(sample_mailbox_rule)

        service.db.add.assert_called()
        service.db.commit.assert_called()

    def test_get_alert_type_forwarding_external(self, service, sample_mailbox_rule):
        """Test getting alert type for external forwarding."""
        sample_mailbox_rule.forward_to_external = True
        sample_mailbox_rule.is_hidden_folder_redirect = False

        alert_type = service._get_alert_type(sample_mailbox_rule)

        assert alert_type == service.EVENT_TYPE_FORWARDING_EXTERNAL

    def test_get_alert_type_hidden_redirect(self, service, sample_mailbox_rule):
        """Test getting alert type for hidden folder redirect."""
        sample_mailbox_rule.forward_to_external = False
        sample_mailbox_rule.is_hidden_folder_redirect = True
        sample_mailbox_rule.auto_reply_content = None

        alert_type = service._get_alert_type(sample_mailbox_rule)

        assert alert_type == service.EVENT_TYPE_REDIRECT_HIDDEN

    def test_get_alert_type_suspicious_auto_reply(self, service, sample_mailbox_rule):
        """Test getting alert type for suspicious auto-reply."""
        sample_mailbox_rule.forward_to_external = False
        sample_mailbox_rule.is_hidden_folder_redirect = False
        sample_mailbox_rule.auto_reply_content = "Contact the bank"
        sample_mailbox_rule.has_suspicious_patterns = True

        alert_type = service._get_alert_type(sample_mailbox_rule)

        assert alert_type == service.EVENT_TYPE_SUSPICIOUS_AUTO_REPLY

    def test_get_alert_type_non_owner(self, service, sample_mailbox_rule):
        """Test getting alert type for rule created by non-owner."""
        sample_mailbox_rule.forward_to_external = False
        sample_mailbox_rule.is_hidden_folder_redirect = False
        sample_mailbox_rule.auto_reply_content = None
        sample_mailbox_rule.has_suspicious_patterns = False
        sample_mailbox_rule.created_by_non_owner = True

        alert_type = service._get_alert_type(sample_mailbox_rule)

        assert alert_type == service.EVENT_TYPE_RULE_CREATED_NON_OWNER

    def test_get_alert_type_outside_hours(self, service, sample_mailbox_rule):
        """Test getting alert type for rule created outside hours."""
        sample_mailbox_rule.forward_to_external = False
        sample_mailbox_rule.is_hidden_folder_redirect = False
        sample_mailbox_rule.auto_reply_content = None
        sample_mailbox_rule.has_suspicious_patterns = False
        sample_mailbox_rule.created_by_non_owner = False
        sample_mailbox_rule.created_outside_business_hours = True

        alert_type = service._get_alert_type(sample_mailbox_rule)

        assert alert_type == service.EVENT_TYPE_RULE_OUTSIDE_HOURS

    def test_map_to_severity_level(self, service):
        """Test mapping rule severity to alert severity level."""
        assert service._map_to_severity_level(RuleSeverity.LOW) == SeverityLevel.LOW
        assert service._map_to_severity_level(RuleSeverity.MEDIUM) == SeverityLevel.MEDIUM
        assert service._map_to_severity_level(RuleSeverity.HIGH) == SeverityLevel.HIGH
        assert service._map_to_severity_level(RuleSeverity.CRITICAL) == SeverityLevel.CRITICAL

    def test_map_to_event_type(self, service):
        """Test mapping rule to event type."""
        rule = MagicMock(spec=MailboxRuleModel)
        event_type = service._map_to_event_type(rule)

        assert event_type == EventType.ADMIN_ACTION

    @pytest.mark.asyncio
    async def test_get_suspicious_rules(self, service):
        """Test getting suspicious rules."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute.return_value = mock_result

        rules = await service.get_suspicious_rules(tenant_id="tenant-123")

        assert rules == []
        service.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_alerts(self, service):
        """Test getting alerts."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute.return_value = mock_result

        result = await service.get_alerts(tenant_id="tenant-123")

        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_acknowledge_alert_success(self, service):
        """Test successfully acknowledging an alert."""
        alert_id = str(uuid4())
        acknowledged_by = "admin@example.com"

        mock_alert = MagicMock(spec=MailboxRuleAlertModel)
        mock_alert.id = alert_id
        mock_alert.is_acknowledged = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alert
        service.db.execute.return_value = mock_result

        result = await service.acknowledge_alert(alert_id, acknowledged_by)

        assert result == mock_alert
        assert mock_alert.is_acknowledged is True
        assert mock_alert.acknowledged_by == acknowledged_by
        service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, service):
        """Test acknowledging a non-existent alert."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute.return_value = mock_result

        result = await service.acknowledge_alert("non-existent", "admin@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_rules_with_filters(self, service):
        """Test getting rules with filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute.return_value = mock_result

        result = await service.get_rules(
            tenant_id="tenant-123",
            status=RuleStatus.SUSPICIOUS,
            severity=RuleSeverity.HIGH,
            rule_type=RuleType.FORWARDING,
            limit=50,
            offset=10,
        )

        assert result["items"] == []
        assert result["limit"] == 50
        assert result["offset"] == 10
