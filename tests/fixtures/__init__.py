"""Mock data fixtures for SpecterDefence tests."""

from datetime import UTC, datetime
from typing import Any

# =============================================================================
# Microsoft Graph API Mock Responses
# =============================================================================

class MSGraphFixtures:
    """Microsoft Graph API mock response fixtures."""

    @staticmethod
    def organization(tenant_id: str = "12345678-1234-1234-1234-123456789012") -> dict[str, Any]:
        """Return a mock organization response."""
        return {
            "value": [{
                "id": tenant_id,
                "displayName": "Test Organization",
                "verifiedDomains": [
                    {
                        "name": "test.com",
                        "isDefault": True,
                        "isInitial": False,
                        "type": "Managed"
                    },
                    {
                        "name": "test.onmicrosoft.com",
                        "isDefault": False,
                        "isInitial": True,
                        "type": "Managed"
                    },
                ],
                "createdDateTime": "2020-01-01T00:00:00Z",
                "tenantType": "AAD",
                "country": "US",
                "countryLetterCode": "US",
                "state": None,
                "city": None,
                "postalCode": None,
                "preferredLanguage": "en",
            }]
        }

    @staticmethod
    def users(count: int = 2) -> dict[str, Any]:
        """Return mock users response."""
        users = []
        for i in range(count):
            users.append({
                "id": f"user-{i+1}-id",
                "displayName": f"Test User {i+1}",
                "userPrincipalName": f"user{i+1}@test.com",
                "mail": f"user{i+1}@test.com",
                "accountEnabled": True,
                "createdDateTime": "2020-01-01T00:00:00Z",
                "lastSignInDateTime": "2026-03-01T00:00:00Z",
                "jobTitle": "Test Engineer",
                "department": "Engineering",
                "officeLocation": "New York",
            })

        return {"value": users}

    @staticmethod
    def sign_in_logs(count: int = 2) -> dict[str, Any]:
        """Return mock sign-in logs response."""
        locations = [
            {
                "city": "New York",
                "state": "NY",
                "countryOrRegion": "US",
                "geoCoordinates": {"latitude": 40.7128, "longitude": -74.0060},
            },
            {
                "city": "Tokyo",
                "countryOrRegion": "JP",
                "geoCoordinates": {"latitude": 35.6762, "longitude": 139.6503},
            },
        ]

        signins = []
        base_time = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

        for i in range(count):
            signins.append({
                "id": f"signin-{i+1}",
                "createdDateTime": base_time.isoformat().replace("+00:00", "Z"),
                "userPrincipalName": "user@example.com",
                "userId": "user-1-id",
                "appDisplayName": "Office 365 Exchange Online",
                "appId": "00000002-0000-0ff1-ce00-000000000000",
                "ipAddress": f"192.168.1.{i+1}",
                "location": locations[i % len(locations)],
                "status": {"errorCode": 0, "failureReason": None},
                "clientAppUsed": "Browser",
                "userAgent": "Mozilla/5.0",
                "correlationId": f"corr-{i+1}",
                "conditionalAccessStatus": "success",
                "isInteractive": True,
                "riskDetail": "none",
                "riskLevelAggregated": "low",
                "riskLevelDuringSignIn": "low",
                "riskState": "none",
            })

        return {"value": signins}

    @staticmethod
    def audit_logs(count: int = 2) -> dict[str, Any]:
        """Return mock audit logs response."""
        logs = []
        base_time = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

        operations = [
            {
                "activityDisplayName": "Add user",
                "category": "UserManagement",
                "result": "success",
            },
            {
                "activityDisplayName": "Update application",
                "category": "ApplicationManagement",
                "result": "success",
            },
        ]

        for i in range(count):
            op = operations[i % len(operations)]
            logs.append({
                "id": f"audit-{i+1}",
                "createdDateTime": base_time.isoformat().replace("+00:00", "Z"),
                "userPrincipalName": "admin@example.com",
                "activityDisplayName": op["activityDisplayName"],
                "category": op["category"],
                "result": op["result"],
                "resultReason": None,
                "correlationId": f"corr-{i+1}",
                "initiatedBy": {
                    "user": {
                        "id": "admin-id",
                        "displayName": "Admin User",
                        "userPrincipalName": "admin@example.com",
                        "ipAddress": "192.168.1.100",
                    }
                },
                "targetResources": [
                    {
                        "id": f"target-{i+1}",
                        "displayName": f"Target {i+1}",
                        "type": "User",
                        "modifiedProperties": [],
                    }
                ],
            })

        return {"value": logs}

    @staticmethod
    def token_response(access_token: str = "mock-token") -> dict[str, Any]:
        """Return a mock token response."""
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "ext_expires_in": 3600,
        }

    @staticmethod
    def error_response(error_code: str = "invalid_client", description: str = "Invalid credentials") -> dict[str, Any]:
        """Return a mock error response."""
        return {
            "error": error_code,
            "error_description": description,
            "error_codes": [50034],
            "timestamp": datetime.now(UTC).isoformat(),
            "trace_id": "test-trace-id",
            "correlation_id": "test-correlation-id",
        }


# =============================================================================
# Tenant Mock Data
# =============================================================================

class TenantFixtures:
    """Tenant mock data fixtures."""

    @staticmethod
    def create_payload(
        name: str = "Test Tenant",
        tenant_id: str = "12345678-1234-1234-1234-123456789012",
        client_id: str = "87654321-4321-4321-4321-210987654321",
        client_secret: str = "test-secret-12345",
    ) -> dict[str, str]:
        """Return a tenant creation payload."""
        return {
            "name": name,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "client_secret": client_secret,
        }

    @staticmethod
    def update_payload(
        name: str = "Updated Tenant Name",
        is_active: bool = True,
    ) -> dict[str, Any]:
        """Return a tenant update payload."""
        return {
            "name": name,
            "is_active": is_active,
        }

    @staticmethod
    def response_payload(
        id: str = "test-tenant-uuid",
        name: str = "Test Tenant",
        tenant_id: str = "12345678-1234-1234-1234-123456789012",
        client_id: str = "87654321-4321-4321-4321-210987654321",
        is_active: bool = True,
    ) -> dict[str, Any]:
        """Return a tenant response payload."""
        return {
            "id": id,
            "name": name,
            "tenant_id": tenant_id,
            "client_id": f"{client_id[:8]}...{client_id[-4:]}",  # Masked
            "is_active": is_active,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "ms_tenant_name": None,
        }

    @staticmethod
    def validation_response(
        valid: bool = True,
        display_name: str = "Test Organization",
        tenant_id: str = "12345678-1234-1234-1234-123456789012",
    ) -> dict[str, Any]:
        """Return a tenant validation response."""
        if valid:
            return {
                "valid": True,
                "display_name": display_name,
                "tenant_id": tenant_id,
                "verified_domains": [{"name": "test.com", "isDefault": True}],
                "error": None,
            }
        return {
            "valid": False,
            "display_name": None,
            "tenant_id": None,
            "verified_domains": None,
            "error": "Invalid credentials",
        }


# =============================================================================
# Discord Webhook Mock Data
# =============================================================================

class DiscordFixtures:
    """Discord webhook mock data fixtures."""

    @staticmethod
    def webhook_url() -> str:
        """Return a mock Discord webhook URL."""
        return "https://discord.com/api/webhooks/123456789/test-webhook-token"

    @staticmethod
    def embed_payload(
        title: str = "Test Alert",
        description: str = "Test description",
        color: int = 15158332,
    ) -> dict[str, Any]:
        """Return a Discord embed payload."""
        return {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(UTC).isoformat(),
            "fields": [
                {"name": "Test Field", "value": "Test Value", "inline": True},
            ],
            "footer": {"text": "SpecterDefence"},
        }

    @staticmethod
    def alert_payload(
        content: str = "",
        embeds: list | None = None,
    ) -> dict[str, Any]:
        """Return a full Discord webhook payload."""
        if embeds is None:
            embeds = [DiscordFixtures.embed_payload()]

        return {
            "content": content,
            "embeds": embeds,
            "username": "SpecterDefence",
            "avatar_url": None,
        }

    @staticmethod
    def success_response() -> dict[str, Any]:
        """Return a successful webhook response."""
        return {"id": "123456789", "type": 1}

    @staticmethod
    def error_response(message: str = "Invalid Webhook Token") -> dict[str, Any]:
        """Return an error webhook response."""
        return {
            "message": message,
            "code": 50027,
        }


# =============================================================================
# Security Event Mock Data
# =============================================================================

class SecurityEventFixtures:
    """Security event mock data fixtures."""

    @staticmethod
    def impossible_travel(
        user_email: str = "user@example.com",
        previous_city: str = "New York",
        previous_country: str = "US",
        current_city: str = "Tokyo",
        current_country: str = "JP",
    ) -> dict[str, Any]:
        """Return an impossible travel event."""
        return {
            "event_type": "impossible_travel",
            "user_email": user_email,
            "severity": "HIGH",
            "title": "Impossible Travel Detected",
            "description": f"User logged in from {current_city}, {current_country} shortly after logging in from {previous_city}, {previous_country}",
            "metadata": {
                "previous_location": {
                    "city": previous_city,
                    "country": previous_country,
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                },
                "current_location": {
                    "city": current_city,
                    "country": current_country,
                    "latitude": 35.6762,
                    "longitude": 139.6503,
                },
                "distance_km": 10847,
                "time_diff_minutes": 30,
                "min_travel_time_minutes": 800,
                "risk_score": 95,
            },
        }

    @staticmethod
    def new_country_login(
        user_email: str = "user@example.com",
        country_code: str = "FR",
        country_name: str = "France",
    ) -> dict[str, Any]:
        """Return a new country login event."""
        return {
            "event_type": "new_country",
            "user_email": user_email,
            "severity": "MEDIUM",
            "title": "New Country Login",
            "description": f"User logged in from {country_name} for the first time",
            "metadata": {
                "country_code": country_code,
                "country_name": country_name,
                "city": "Paris",
                "known_countries": ["US", "GB", "DE"],
                "is_first_login": False,
                "ip_address": "203.0.113.50",
            },
        }

    @staticmethod
    def brute_force_attempt(
        user_email: str = "admin@example.com",
        failure_count: int = 10,
    ) -> dict[str, Any]:
        """Return a brute force attack event."""
        return {
            "event_type": "brute_force",
            "user_email": user_email,
            "severity": "CRITICAL",
            "title": "Brute Force Attack Detected",
            "description": f"{failure_count} failed login attempts detected",
            "metadata": {
                "recent_failures": failure_count,
                "failure_reason": "Invalid password",
                "ip_address": "198.51.100.1",
                "time_window_minutes": 15,
            },
        }

    @staticmethod
    def admin_action(
        admin_email: str = "admin@example.com",
        action: str = "User deletion",
        target: str = "user@example.com",
    ) -> dict[str, Any]:
        """Return an admin action event."""
        return {
            "event_type": "admin_action",
            "user_email": admin_email,
            "severity": "MEDIUM",
            "title": "Admin Action: " + action,
            "description": f"Admin {admin_email} performed {action} on {target}",
            "metadata": {
                "action": action,
                "target": target,
                "ip_address": "192.168.1.100",
            },
        }


# =============================================================================
# Convenience Exports
# =============================================================================

ms_graph = MSGraphFixtures()
tenant = TenantFixtures()
discord = DiscordFixtures()
security_event = SecurityEventFixtures()
