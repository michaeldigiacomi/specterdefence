"""Microsoft Graph client for mailbox rules operations."""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.clients.ms_graph import MSGraphAPIError, MSGraphClient

logger = logging.getLogger(__name__)


class MailboxRuleClient:
    """Client for fetching and managing mailbox rules via Microsoft Graph API."""

    # Suspicious keywords in auto-reply messages
    SUSPICIOUS_KEYWORDS = [
        "bank", "wire transfer", "payment", "invoice", "urgent",
        "confidential", "secret", "password", "credential", "login",
        "verify", "verification", "security update", "account suspended",
        "immediate action", "click here", "verify account"
    ]

    # Known malicious domains (simplified list - expand as needed)
    SUSPICIOUS_DOMAINS = [
        "tempmail", "guerrillamail", "10minutemail", "throwaway",
        "mailinator", "yopmail", "fakeinbox"
    ]

    def __init__(self, graph_client: MSGraphClient) -> None:
        """Initialize with existing MS Graph client.

        Args:
            graph_client: Authenticated MSGraphClient instance
        """
        self.graph_client = graph_client

    async def get_users(self, filter_active: bool = True) -> list[dict[str, Any]]:
        """Get list of users in the tenant.

        Args:
            filter_active: Only return active users

        Returns:
            List of user objects with id, displayName, userPrincipalName, mail
        """
        token = await self.graph_client.get_access_token()

        url = "https://graph.microsoft.com/v1.0/users"
        params = {
            "$select": "id,displayName,userPrincipalName,mail,accountEnabled",
            "$top": "999",
        }

        if filter_active:
            params["$filter"] = "accountEnabled eq true"

        users = []
        async with httpx.AsyncClient() as client:
            while url:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if url == "https://graph.microsoft.com/v1.0/users" else None
                )

                if response.status_code != 200:
                    raise MSGraphAPIError(f"Failed to fetch users: {response.status_code}")

                data = response.json()
                users.extend(data.get("value", []))

                # Handle pagination
                url = data.get("@odata.nextLink")
                params = None

        return users

    async def get_mailbox_rules(self, user_id: str) -> list[dict[str, Any]]:
        """Get mailbox rules for a specific user.

        Args:
            user_id: The user's ID or UPN

        Returns:
            List of mailbox rule objects
        """
        token = await self.graph_client.get_access_token()

        # Use beta endpoint for more complete rule data
        url = f"https://graph.microsoft.com/beta/users/{user_id}/mailFolders/inbox/messageRules"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 404:
                # User might not have a mailbox
                return []

            if response.status_code != 200:
                error_text = response.text
                logger.warning(f"Failed to fetch rules for {user_id}: {response.status_code} - {error_text}")
                return []

            data = response.json()
            rules = data.get("value", [])

            # Add user context to each rule
            for rule in rules:
                rule["_user_id"] = user_id

            return rules

    async def get_mailbox_rules_for_tenant(self) -> list[dict[str, Any]]:
        """Get mailbox rules for all users in the tenant.

        Returns:
            List of mailbox rule objects with user context
        """
        users = await self.get_users()
        all_rules = []

        for user in users:
            user_id = user.get("userPrincipalName") or user.get("id")
            user_email = user.get("mail") or user.get("userPrincipalName", "")

            try:
                rules = await self.get_mailbox_rules(user_id)
                for rule in rules:
                    rule["_user_email"] = user_email
                    rule["_user_id"] = user_id
                all_rules.extend(rules)
            except Exception as e:
                logger.warning(f"Error fetching rules for {user_id}: {e}")
                continue

        return all_rules

    def analyze_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        """Analyze a mailbox rule for suspicious characteristics.

        Args:
            rule: Mailbox rule object from Graph API

        Returns:
            Analysis results with detection flags and severity
        """
        analysis = {
            "rule_type": "custom",
            "is_forwarding": False,
            "is_redirect": False,
            "is_auto_reply": False,
            "forward_to": None,
            "forward_to_external": False,
            "external_domain": None,
            "redirect_to": None,
            "auto_reply_content": None,
            "is_hidden_folder_redirect": False,
            "has_suspicious_patterns": False,
            "created_outside_business_hours": False,
            "detection_reasons": [],
            "severity": "LOW",
            "status": "benign"
        }

        # Get actions
        actions = rule.get("actions", {})

        # Check for forwarding
        if actions.get("forwardTo"):
            analysis["is_forwarding"] = True
            analysis["rule_type"] = "forwarding"
            forward_recipients = actions.get("forwardTo", [])
            if forward_recipients:
                analysis["forward_to"] = forward_recipients[0].get("emailAddress", {}).get("address", "")
                analysis["forward_to_external"] = self._is_external_address(analysis["forward_to"])
                if analysis["forward_to_external"]:
                    analysis["external_domain"] = analysis["forward_to"].split("@")[-1] if "@" in analysis["forward_to"] else None
                    analysis["detection_reasons"].append("Forwarding to external email address")

        # Check for redirect
        if actions.get("redirect"):
            analysis["is_redirect"] = True
            analysis["rule_type"] = "redirect"
            redirect_recipients = actions.get("redirect", [])
            if redirect_recipients:
                analysis["redirect_to"] = redirect_recipients[0].get("emailAddress", {}).get("address", "")
                analysis["detection_reasons"].append("Email redirect rule detected")

        # Check for auto-reply
        if actions.get("reply"):
            analysis["is_auto_reply"] = True
            analysis["rule_type"] = "auto_reply"
            analysis["auto_reply_content"] = actions.get("reply", "")

            # Check for suspicious keywords in auto-reply
            if self._contains_suspicious_keywords(analysis["auto_reply_content"]):
                analysis["has_suspicious_patterns"] = True
                analysis["detection_reasons"].append("Auto-reply contains suspicious keywords")

        # Check for move to hidden folder (delete, junk, etc.)
        if actions.get("moveToFolder"):
            folder_id = actions.get("moveToFolder", {}).get("id", "").lower()
            folder_name = actions.get("moveToFolder", {}).get("displayName", "").lower()

            if any(x in folder_id or x in folder_name for x in ["deleted", "junk", "spam", "archive"]):
                analysis["is_hidden_folder_redirect"] = True
                analysis["detection_reasons"].append("Moves emails to hidden/deleted folder")

        # Check for delete action
        if actions.get("delete"):
            analysis["detection_reasons"].append("Rule deletes emails")

        # Analyze creation time if available
        created_date_time = rule.get("createdDateTime")
        if created_date_time:
            try:
                created_dt = datetime.fromisoformat(created_date_time.replace("Z", "+00:00"))
                analysis["created_outside_business_hours"] = self._is_outside_business_hours(created_dt)
                if analysis["created_outside_business_hours"]:
                    analysis["detection_reasons"].append("Rule created outside business hours")
            except (ValueError, AttributeError):
                pass

        # Determine severity and status
        analysis["severity"] = self._calculate_severity(analysis)
        analysis["status"] = self._calculate_status(analysis)

        return analysis

    def _is_external_address(self, email: str) -> bool:
        """Check if an email address is external (non-corporate).

        Args:
            email: Email address to check

        Returns:
            True if external
        """
        if not email or "@" not in email:
            return False

        domain = email.split("@")[-1].lower()

        # Common consumer email providers
        consumer_domains = [
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
            "aol.com", "icloud.com", "mail.com", "protonmail.com",
            "yandex.com", "qq.com", "163.com", "126.com"
        ]

        if domain in consumer_domains:
            return True

        # Check suspicious domains
        return bool(any(susp in domain for susp in self.SUSPICIOUS_DOMAINS))

    def _contains_suspicious_keywords(self, text: str) -> bool:
        """Check if text contains suspicious keywords.

        Args:
            text: Text to check

        Returns:
            True if suspicious keywords found
        """
        if not text:
            return False

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.SUSPICIOUS_KEYWORDS)

    def _is_outside_business_hours(self, dt: datetime) -> bool:
        """Check if datetime is outside business hours (9 AM - 6 PM, Mon-Fri).

        Args:
            dt: Datetime to check

        Returns:
            True if outside business hours
        """
        # Weekend
        if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return True

        # Before 9 AM or after 6 PM
        return bool(dt.hour < 9 or dt.hour >= 18)

    def _calculate_severity(self, analysis: dict[str, Any]) -> str:
        """Calculate severity based on analysis flags.

        Args:
            analysis: Analysis results dictionary

        Returns:
            Severity level string
        """
        score = 0

        if analysis["forward_to_external"]:
            score += 3
        if analysis["is_hidden_folder_redirect"]:
            score += 2
        if analysis["has_suspicious_patterns"]:
            score += 2
        if analysis["is_redirect"]:
            score += 2
        if analysis["created_outside_business_hours"]:
            score += 1

        if score >= 5:
            return "CRITICAL"
        elif score >= 3:
            return "HIGH"
        elif score >= 1:
            return "MEDIUM"
        return "LOW"

    def _calculate_status(self, analysis: dict[str, Any]) -> str:
        """Calculate status based on analysis flags.

        Args:
            analysis: Analysis results dictionary

        Returns:
            Status string
        """
        severity = analysis["severity"]

        if severity == "CRITICAL":
            return "malicious"
        elif severity in ["HIGH", "MEDIUM"]:
            return "suspicious"
        return "benign"

    async def disable_rule(self, user_id: str, rule_id: str) -> bool:
        """Disable a mailbox rule.

        Args:
            user_id: User ID or UPN
            rule_id: Rule ID to disable

        Returns:
            True if successful
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/beta/users/{user_id}/mailFolders/inbox/messageRules/{rule_id}"

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"isEnabled": False}
            )

            return response.status_code == 200

    async def delete_rule(self, user_id: str, rule_id: str) -> bool:
        """Delete a mailbox rule.

        Args:
            user_id: User ID or UPN
            rule_id: Rule ID to delete

        Returns:
            True if successful
        """
        token = await self.graph_client.get_access_token()

        url = f"https://graph.microsoft.com/beta/users/{user_id}/mailFolders/inbox/messageRules/{rule_id}"

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            return response.status_code == 204
