"""Unit tests for mailbox rules client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.mailbox_rules import MailboxRuleClient
from src.clients.ms_graph import MSGraphClient


class TestMailboxRuleClient:
    """Test cases for MailboxRuleClient."""

    @pytest.fixture
    def mock_graph_client(self):
        """Create a mock MS Graph client."""
        client = MagicMock(spec=MSGraphClient)
        client.get_access_token = AsyncMock(return_value="mock-token")
        client.tenant_id = "test-tenant-id"
        client.client_id = "test-client-id"
        return client

    @pytest.fixture
    def mailbox_client(self, mock_graph_client):
        """Create a MailboxRuleClient instance."""
        return MailboxRuleClient(mock_graph_client)

    @pytest.fixture
    def sample_user(self):
        """Return a sample user object."""
        return {
            "id": "user-123",
            "displayName": "Test User",
            "userPrincipalName": "testuser@example.com",
            "mail": "testuser@example.com",
            "accountEnabled": True,
        }

    @pytest.fixture
    def sample_mailbox_rule(self):
        """Return a sample mailbox rule."""
        return {
            "id": "rule-123",
            "displayName": "Test Rule",
            "isEnabled": True,
            "createdDateTime": "2024-01-15T10:30:00Z",
            "conditions": {},
            "actions": {
                "forwardTo": [
                    {"emailAddress": {"address": "external@gmail.com"}}
                ]
            },
        }

    @pytest.fixture
    def sample_redirect_rule(self):
        """Return a sample redirect rule."""
        return {
            "id": "rule-456",
            "displayName": "Redirect Rule",
            "isEnabled": True,
            "createdDateTime": "2024-01-15T14:00:00Z",
            "conditions": {},
            "actions": {
                "redirect": [
                    {"emailAddress": {"address": "attacker@evil.com"}}
                ]
            },
        }

    @pytest.fixture
    def sample_auto_reply_rule(self):
        """Return a sample auto-reply rule."""
        return {
            "id": "rule-789",
            "displayName": "Auto Reply",
            "isEnabled": True,
            "createdDateTime": "2024-01-15T09:00:00Z",
            "conditions": {},
            "actions": {
                "reply": "I am out of office. For urgent matters, please contact our bank."
            },
        }

    @pytest.fixture
    def sample_hidden_folder_rule(self):
        """Return a sample hidden folder redirect rule."""
        return {
            "id": "rule-hidden",
            "displayName": "Move to Deleted",
            "isEnabled": True,
            "createdDateTime": "2024-01-15T22:00:00Z",  # After hours
            "conditions": {},
            "actions": {
                "moveToFolder": {
                    "id": "deleteditems",
                    "displayName": "Deleted Items"
                }
            },
        }

    @pytest.mark.asyncio
    async def test_get_users_success(self, mailbox_client, mock_graph_client):
        """Test successful user retrieval."""
        mock_users = {
            "value": [
                {
                    "id": "user-1",
                    "displayName": "User One",
                    "userPrincipalName": "user1@example.com",
                    "mail": "user1@example.com",
                    "accountEnabled": True,
                },
                {
                    "id": "user-2",
                    "displayName": "User Two",
                    "userPrincipalName": "user2@example.com",
                    "mail": "user2@example.com",
                    "accountEnabled": True,
                },
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_users
            mock_get.return_value = mock_response

            users = await mailbox_client.get_users()

        assert len(users) == 2
        assert users[0]["displayName"] == "User One"
        assert users[1]["displayName"] == "User Two"

    @pytest.mark.asyncio
    async def test_get_users_with_pagination(self, mailbox_client, mock_graph_client):
        """Test user retrieval with pagination."""
        page1 = {
            "value": [{"id": "user-1", "displayName": "User One", "accountEnabled": True}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skip=1"
        }
        page2 = {
            "value": [{"id": "user-2", "displayName": "User Two", "accountEnabled": True}],
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response1 = MagicMock()
            mock_response1.status_code = 200
            mock_response1.json.return_value = page1

            mock_response2 = MagicMock()
            mock_response2.status_code = 200
            mock_response2.json.return_value = page2

            mock_get.side_effect = [mock_response1, mock_response2]

            users = await mailbox_client.get_users()

        assert len(users) == 2
        assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_mailbox_rules_success(self, mailbox_client, mock_graph_client):
        """Test successful mailbox rules retrieval."""
        mock_rules = {
            "value": [
                {"id": "rule-1", "displayName": "Rule 1", "isEnabled": True},
                {"id": "rule-2", "displayName": "Rule 2", "isEnabled": False},
            ]
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_rules
            mock_get.return_value = mock_response

            rules = await mailbox_client.get_mailbox_rules("testuser@example.com")

        assert len(rules) == 2
        assert rules[0]["_user_id"] == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_get_mailbox_rules_no_mailbox(self, mailbox_client, mock_graph_client):
        """Test mailbox rules retrieval for user without mailbox."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            rules = await mailbox_client.get_mailbox_rules("testuser@example.com")

        assert rules == []

    @pytest.mark.asyncio
    async def test_get_mailbox_rules_for_tenant(self, mailbox_client, mock_graph_client):
        """Test getting rules for entire tenant."""
        mock_users = [
            {"id": "user-1", "userPrincipalName": "user1@example.com", "mail": "user1@example.com"},
            {"id": "user-2", "userPrincipalName": "user2@example.com", "mail": "user2@example.com"},
        ]

        mock_rules_user1 = [{"id": "rule-1", "displayName": "Rule 1", "isEnabled": True}]
        mock_rules_user2 = [{"id": "rule-2", "displayName": "Rule 2", "isEnabled": True}]

        with patch.object(mailbox_client, "get_users", return_value=mock_users):
            with patch.object(mailbox_client, "get_mailbox_rules") as mock_get_rules:
                mock_get_rules.side_effect = [mock_rules_user1, mock_rules_user2]

                rules = await mailbox_client.get_mailbox_rules_for_tenant()

        assert len(rules) == 2
        assert rules[0]["_user_email"] == "user1@example.com"
        assert rules[1]["_user_email"] == "user2@example.com"

    def test_analyze_rule_forwarding_external(self, mailbox_client, sample_mailbox_rule):
        """Test analysis of external forwarding rule."""
        analysis = mailbox_client.analyze_rule(sample_mailbox_rule)

        assert analysis["is_forwarding"] is True
        assert analysis["forward_to"] == "external@gmail.com"
        assert analysis["forward_to_external"] is True
        assert analysis["external_domain"] == "gmail.com"
        assert "Forwarding to external email address" in analysis["detection_reasons"]
        # External forwarding alone = 3 points = HIGH severity
        assert analysis["severity"] == "HIGH"

    def test_analyze_rule_redirect(self, mailbox_client, sample_redirect_rule):
        """Test analysis of redirect rule."""
        analysis = mailbox_client.analyze_rule(sample_redirect_rule)

        assert analysis["is_redirect"] is True
        assert analysis["redirect_to"] == "attacker@evil.com"
        assert "Email redirect rule detected" in analysis["detection_reasons"]

    def test_analyze_rule_suspicious_auto_reply(self, mailbox_client, sample_auto_reply_rule):
        """Test analysis of suspicious auto-reply rule."""
        analysis = mailbox_client.analyze_rule(sample_auto_reply_rule)

        assert analysis["is_auto_reply"] is True
        assert "bank" in analysis["auto_reply_content"].lower()
        assert analysis["has_suspicious_patterns"] is True
        assert "Auto-reply contains suspicious keywords" in analysis["detection_reasons"]

    def test_analyze_rule_hidden_folder_redirect(self, mailbox_client, sample_hidden_folder_rule):
        """Test analysis of hidden folder redirect rule."""
        analysis = mailbox_client.analyze_rule(sample_hidden_folder_rule)

        assert analysis["is_hidden_folder_redirect"] is True
        assert "Moves emails to hidden/deleted folder" in analysis["detection_reasons"]
        assert analysis["created_outside_business_hours"] is True
        assert "Rule created outside business hours" in analysis["detection_reasons"]

    def test_analyze_rule_benign(self, mailbox_client):
        """Test analysis of benign rule."""
        benign_rule = {
            "id": "rule-benign",
            "displayName": "Organize Newsletters",
            "isEnabled": True,
            "createdDateTime": "2024-01-15T10:00:00Z",  # Business hours
            "conditions": {"subjectContains": ["newsletter"]},
            "actions": {"moveToFolder": {"id": "folder-123", "displayName": "Newsletters"}},
        }

        analysis = mailbox_client.analyze_rule(benign_rule)

        assert analysis["is_forwarding"] is False
        assert analysis["is_redirect"] is False
        assert analysis["is_hidden_folder_redirect"] is False
        assert analysis["severity"] == "LOW"
        assert analysis["status"] == "benign"
        assert len(analysis["detection_reasons"]) == 0

    def test_is_external_address(self, mailbox_client):
        """Test external email detection."""
        # External addresses
        assert mailbox_client._is_external_address("user@gmail.com") is True
        assert mailbox_client._is_external_address("user@yahoo.com") is True
        assert mailbox_client._is_external_address("user@hotmail.com") is True

        # Internal/corporate addresses
        assert mailbox_client._is_external_address("user@company.com") is False
        assert mailbox_client._is_external_address("user@example.org") is False

        # Suspicious domains
        assert mailbox_client._is_external_address("user@tempmail.com") is True

    def test_contains_suspicious_keywords(self, mailbox_client):
        """Test suspicious keyword detection."""
        assert mailbox_client._contains_suspicious_keywords("Contact the bank immediately") is True
        assert mailbox_client._contains_suspicious_keywords("Wire transfer required") is True
        assert mailbox_client._contains_suspicious_keywords("Verify your account") is True
        assert mailbox_client._contains_suspicious_keywords("Normal business communication") is False

    def test_is_outside_business_hours(self, mailbox_client):
        """Test business hours detection."""
        # Weekday business hours (9 AM - 6 PM)
        weekday_morning = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)  # Monday 10 AM
        assert mailbox_client._is_outside_business_hours(weekday_morning) is False

        # Weekday before hours
        weekday_early = datetime(2024, 1, 15, 7, 0, 0, tzinfo=UTC)  # Monday 7 AM
        assert mailbox_client._is_outside_business_hours(weekday_early) is True

        # Weekday after hours
        weekday_late = datetime(2024, 1, 15, 20, 0, 0, tzinfo=UTC)  # Monday 8 PM
        assert mailbox_client._is_outside_business_hours(weekday_late) is True

        # Weekend
        saturday = datetime(2024, 1, 13, 10, 0, 0, tzinfo=UTC)  # Saturday 10 AM
        assert mailbox_client._is_outside_business_hours(saturday) is True

        sunday = datetime(2024, 1, 14, 14, 0, 0, tzinfo=UTC)  # Sunday 2 PM
        assert mailbox_client._is_outside_business_hours(sunday) is True

    def test_calculate_severity_critical(self, mailbox_client):
        """Test critical severity calculation."""
        analysis = {
            "forward_to_external": True,
            "is_hidden_folder_redirect": True,
            "has_suspicious_patterns": True,
            "is_redirect": True,
            "created_outside_business_hours": False,
        }

        severity = mailbox_client._calculate_severity(analysis)
        assert severity == "CRITICAL"

    def test_calculate_severity_high(self, mailbox_client):
        """Test high severity calculation."""
        analysis = {
            "forward_to_external": True,  # 3 points
            "is_hidden_folder_redirect": False,
            "has_suspicious_patterns": False,
            "is_redirect": False,
            "created_outside_business_hours": False,  # Total = 3 = HIGH
        }

        severity = mailbox_client._calculate_severity(analysis)
        assert severity == "HIGH"

    def test_calculate_severity_critical_combined_flags(self, mailbox_client):
        """Test critical severity calculation with combined flags."""
        analysis = {
            "forward_to_external": True,  # 3 points
            "is_hidden_folder_redirect": True,  # 2 points
            "has_suspicious_patterns": False,
            "is_redirect": False,
            "created_outside_business_hours": False,  # Total = 5 = CRITICAL
        }

        severity = mailbox_client._calculate_severity(analysis)
        assert severity == "CRITICAL"

    def test_calculate_severity_medium(self, mailbox_client):
        """Test medium severity calculation."""
        analysis = {
            "forward_to_external": False,
            "is_hidden_folder_redirect": False,
            "has_suspicious_patterns": False,
            "is_redirect": False,
            "created_outside_business_hours": True,
        }

        severity = mailbox_client._calculate_severity(analysis)
        assert severity == "MEDIUM"

    def test_calculate_severity_low(self, mailbox_client):
        """Test low severity calculation."""
        analysis = {
            "forward_to_external": False,
            "is_hidden_folder_redirect": False,
            "has_suspicious_patterns": False,
            "is_redirect": False,
            "created_outside_business_hours": False,
        }

        severity = mailbox_client._calculate_severity(analysis)
        assert severity == "LOW"

    def test_calculate_status(self, mailbox_client):
        """Test status calculation."""
        assert mailbox_client._calculate_status({"severity": "CRITICAL"}) == "malicious"
        assert mailbox_client._calculate_status({"severity": "HIGH"}) == "suspicious"
        assert mailbox_client._calculate_status({"severity": "MEDIUM"}) == "suspicious"
        assert mailbox_client._calculate_status({"severity": "LOW"}) == "benign"

    @pytest.mark.asyncio
    async def test_disable_rule_success(self, mailbox_client, mock_graph_client):
        """Test successful rule disabling."""
        with patch("httpx.AsyncClient.patch") as mock_patch:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_patch.return_value = mock_response

            result = await mailbox_client.disable_rule("user@example.com", "rule-123")

        assert result is True
        mock_patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_disable_rule_failure(self, mailbox_client, mock_graph_client):
        """Test failed rule disabling."""
        with patch("httpx.AsyncClient.patch") as mock_patch:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_patch.return_value = mock_response

            result = await mailbox_client.disable_rule("user@example.com", "rule-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_rule_success(self, mailbox_client, mock_graph_client):
        """Test successful rule deletion."""
        with patch("httpx.AsyncClient.delete") as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_delete.return_value = mock_response

            result = await mailbox_client.delete_rule("user@example.com", "rule-123")

        assert result is True

    def test_suspicious_keywords_list(self, mailbox_client):
        """Test that suspicious keywords are defined."""
        assert len(mailbox_client.SUSPICIOUS_KEYWORDS) > 0
        assert "bank" in mailbox_client.SUSPICIOUS_KEYWORDS
        assert "wire transfer" in mailbox_client.SUSPICIOUS_KEYWORDS
        assert "password" in mailbox_client.SUSPICIOUS_KEYWORDS

    def test_suspicious_domains_list(self, mailbox_client):
        """Test that suspicious domains are defined."""
        assert len(mailbox_client.SUSPICIOUS_DOMAINS) > 0
        assert "tempmail" in mailbox_client.SUSPICIOUS_DOMAINS
        assert "mailinator" in mailbox_client.SUSPICIOUS_DOMAINS
