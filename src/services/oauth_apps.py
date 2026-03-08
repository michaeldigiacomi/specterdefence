"""OAuth application monitoring service for SpecterDefence."""

import contextlib
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.engine import AlertEngine
from src.clients.ms_graph import MSGraphClient
from src.clients.oauth_apps import OAuthAppsClient
from src.models.alerts import EventType, SeverityLevel
from src.models.db import TenantModel
from src.models.oauth_apps import (
    AppStatus,
    OAuthAppAlertModel,
    OAuthAppConsentModel,
    OAuthAppModel,
    OAuthAppPermissionModel,
    PublisherType,
    RiskLevel,
)
from src.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class OAuthAppsService:
    """Service for monitoring and managing OAuth applications."""

    # Event types for OAuth app alerts
    EVENT_TYPE_NEW_APP = "oauth_new_app"
    EVENT_TYPE_HIGH_RISK_PERMISSIONS = "oauth_high_risk_permissions"
    EVENT_TYPE_UNVERIFIED_PUBLISHER = "oauth_unverified_publisher"
    EVENT_TYPE_MAIL_ACCESS = "oauth_mail_access"
    EVENT_TYPE_EXCESSIVE_PERMISSIONS = "oauth_excessive_permissions"
    EVENT_TYPE_SUSPICIOUS_CONSENT = "oauth_suspicious_consent"

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db_session: Async database session
        """
        self.db = db_session

    async def scan_tenant_oauth_apps(
        self, tenant_id: str, trigger_alerts: bool = True
    ) -> dict[str, Any]:
        """Scan all OAuth applications for a tenant.

        Args:
            tenant_id: Internal tenant UUID
            trigger_alerts: Whether to trigger alerts for suspicious apps

        Returns:
            Scan results summary
        """
        # Get tenant details
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Decrypt credentials
        client_secret = encryption_service.decrypt(tenant.client_secret)

        # Create Graph client
        graph_client = MSGraphClient(
            tenant_id=tenant.tenant_id, client_id=tenant.client_id, client_secret=client_secret
        )

        # Create OAuth apps client
        oauth_client = OAuthAppsClient(graph_client)

        # Fetch all service principals (enterprise apps)
        logger.info(f"Scanning OAuth apps for tenant {tenant.name}")
        service_principals = await oauth_client.get_service_principals()

        results = {
            "total_apps": len(service_principals),
            "new_apps": 0,
            "updated_apps": 0,
            "suspicious_apps": 0,
            "malicious_apps": 0,
            "alerts_triggered": 0,
        }

        # Process each app
        for sp in service_principals:
            try:
                # Get permissions for this app
                sp_id = sp.get("id")
                permissions = await oauth_client.get_app_permissions(sp_id)

                # Analyze permissions
                perm_analysis = oauth_client.analyze_permissions(permissions)

                # Get OAuth grants (consents)
                consents = await oauth_client.get_oauth_permission_grants(sp_id)

                app_result = await self._process_app(
                    tenant_id=tenant_id,
                    app_data=sp,
                    permissions=permissions,
                    consents=consents,
                    perm_analysis=perm_analysis,
                    oauth_client=oauth_client,
                    trigger_alerts=trigger_alerts,
                )

                if app_result.get("is_new"):
                    results["new_apps"] += 1
                elif app_result.get("is_updated"):
                    results["updated_apps"] += 1

                if app_result.get("status") == AppStatus.SUSPICIOUS:
                    results["suspicious_apps"] += 1
                elif app_result.get("status") == AppStatus.MALICIOUS:
                    results["malicious_apps"] += 1

                if app_result.get("alert_triggered"):
                    results["alerts_triggered"] += 1

            except Exception as e:
                logger.error(f"Error processing app {sp.get('id')}: {e}")
                continue

        return results

    async def _process_app(
        self,
        tenant_id: str,
        app_data: dict[str, Any],
        permissions: list[dict[str, Any]],
        consents: list[dict[str, Any]],
        perm_analysis: dict[str, Any],
        oauth_client: OAuthAppsClient,
        trigger_alerts: bool,
    ) -> dict[str, Any]:
        """Process a single OAuth application.

        Args:
            tenant_id: Internal tenant UUID
            app_data: App data from Graph API
            permissions: App permissions
            consents: OAuth consents for this app
            perm_analysis: Permission analysis results
            oauth_client: OAuthAppsClient instance
            trigger_alerts: Whether to trigger alerts

        Returns:
            Processing results
        """
        app_id = app_data.get("appId", "")
        app_data.get("displayName", "Unknown App")

        # Analyze app for risk
        app_analysis = oauth_client.analyze_app(app_data, perm_analysis)

        # Check if app already exists
        existing_app = await self._get_existing_app(tenant_id, app_id)

        is_new = False
        is_updated = False
        alert_triggered = False

        if existing_app:
            # Update existing app
            await self._update_app(
                existing_app, app_data, permissions, consents, perm_analysis, app_analysis
            )
            is_updated = True
            app_model = existing_app
        else:
            # Create new app
            app_model = await self._create_app(
                tenant_id, app_data, permissions, consents, perm_analysis, app_analysis
            )
            is_new = True
            app_analysis["is_new_app"] = True

        # Store detailed permissions
        await self._store_permissions(app_model.id, tenant_id, permissions)

        # Store consents
        await self._store_consents(app_model.id, tenant_id, consents)

        # Trigger alerts if needed
        if trigger_alerts and app_model.status in [AppStatus.SUSPICIOUS, AppStatus.MALICIOUS]:
            await self._trigger_alert(app_model)
            alert_triggered = True

        # Trigger alert for new apps with high-risk permissions
        if (
            trigger_alerts
            and is_new
            and app_model.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ):
            await self._trigger_alert(app_model, alert_type=self.EVENT_TYPE_NEW_APP)
            alert_triggered = True

        return {
            "is_new": is_new,
            "is_updated": is_updated,
            "status": app_model.status,
            "alert_triggered": alert_triggered,
        }

    async def _get_existing_app(self, tenant_id: str, app_id: str) -> OAuthAppModel | None:
        """Get existing app from database.

        Args:
            tenant_id: Internal tenant UUID
            app_id: Microsoft Graph app ID

        Returns:
            Existing app or None
        """
        result = await self.db.execute(
            select(OAuthAppModel).where(
                and_(OAuthAppModel.tenant_id == tenant_id, OAuthAppModel.app_id == app_id)
            )
        )
        return result.scalar_one_or_none()

    async def _create_app(
        self,
        tenant_id: str,
        app_data: dict[str, Any],
        permissions: list[dict[str, Any]],
        consents: list[dict[str, Any]],
        perm_analysis: dict[str, Any],
        app_analysis: dict[str, Any],
    ) -> OAuthAppModel:
        """Create a new OAuth app record.

        Args:
            tenant_id: Internal tenant UUID
            app_data: App data from Graph API
            permissions: App permissions
            consents: OAuth consents
            perm_analysis: Permission analysis results
            app_analysis: App analysis results

        Returns:
            Created app model
        """
        verified_publisher = app_data.get("verifiedPublisher", {})
        publisher_name = app_data.get("publisherName", "")

        # Parse creation date
        app_created_at = None
        if app_data.get("createdDateTime"):
            with contextlib.suppress(ValueError, AttributeError):
                app_created_at = datetime.fromisoformat(
                    app_data["createdDateTime"].replace("Z", "+00:00")
                )

        # Count consents
        consent_count = len(consents)
        admin_consented = any(consent.get("consentType") == "AllPrincipals" for consent in consents)

        app = OAuthAppModel(
            tenant_id=tenant_id,
            app_id=app_data.get("appId", ""),
            display_name=app_data.get("displayName", "Unknown App"),
            description=app_data.get("description"),
            publisher_name=publisher_name or verified_publisher.get("displayName"),
            publisher_id=verified_publisher.get("verifiedPublisherId"),
            publisher_type=PublisherType(app_analysis.get("publisher_type", "unknown")),
            is_microsoft_publisher=app_analysis.get("is_microsoft_publisher", False),
            is_verified_publisher=app_analysis.get("is_verified_publisher", False),
            risk_level=RiskLevel(app_analysis.get("risk_level", "LOW")),
            status=AppStatus(app_analysis.get("status", "pending_review")),
            risk_score=app_analysis.get("risk_score", 0),
            permission_count=perm_analysis.get("total_permissions", 0),
            high_risk_permissions=[
                p["value"] for p in perm_analysis.get("high_risk_permissions", [])
            ],
            has_mail_permissions=perm_analysis.get("has_mail_permissions", False),
            has_user_read_all=perm_analysis.get("has_user_read_all", False),
            has_group_read_all=perm_analysis.get("has_group_read_all", False),
            has_files_read_all=perm_analysis.get("has_files_read_all", False),
            has_calendar_access=perm_analysis.get("has_calendar_access", False),
            has_admin_consent=admin_consented,
            consent_count=consent_count,
            admin_consented=admin_consented,
            is_new_app=True,
            audience=app_analysis.get("audience"),
            is_internal=app_analysis.get("is_internal", False),
            detection_reasons=app_analysis.get("detection_reasons", []),
            app_created_at=app_created_at,
            app_data=app_data,
            permissions_data={"permissions": permissions},
        )

        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)

        return app

    async def _update_app(
        self,
        app: OAuthAppModel,
        app_data: dict[str, Any],
        permissions: list[dict[str, Any]],
        consents: list[dict[str, Any]],
        perm_analysis: dict[str, Any],
        app_analysis: dict[str, Any],
    ) -> None:
        """Update an existing OAuth app record.

        Args:
            app: Existing app model
            app_data: Updated app data from Graph API
            permissions: Updated permissions
            consents: Updated consents
            perm_analysis: Updated permission analysis
            app_analysis: Updated app analysis
        """
        verified_publisher = app_data.get("verifiedPublisher", {})
        publisher_name = app_data.get("publisherName", "")

        # Count consents
        consent_count = len(consents)
        admin_consented = any(consent.get("consentType") == "AllPrincipals" for consent in consents)

        app.display_name = app_data.get("displayName", app.display_name)
        app.description = app_data.get("description") or app.description
        app.publisher_name = (
            publisher_name or verified_publisher.get("displayName") or app.publisher_name
        )
        app.publisher_id = verified_publisher.get("verifiedPublisherId") or app.publisher_id
        app.publisher_type = PublisherType(
            app_analysis.get("publisher_type", app.publisher_type.value)
        )
        app.is_microsoft_publisher = app_analysis.get(
            "is_microsoft_publisher", app.is_microsoft_publisher
        )
        app.is_verified_publisher = app_analysis.get(
            "is_verified_publisher", app.is_verified_publisher
        )
        app.risk_level = RiskLevel(app_analysis.get("risk_level", app.risk_level.value))
        app.status = AppStatus(app_analysis.get("status", app.status.value))
        app.risk_score = app_analysis.get("risk_score", app.risk_score)
        app.permission_count = perm_analysis.get("total_permissions", app.permission_count)
        app.high_risk_permissions = [
            p["value"] for p in perm_analysis.get("high_risk_permissions", [])
        ]
        app.has_mail_permissions = perm_analysis.get(
            "has_mail_permissions", app.has_mail_permissions
        )
        app.has_user_read_all = perm_analysis.get("has_user_read_all", app.has_user_read_all)
        app.has_group_read_all = perm_analysis.get("has_group_read_all", app.has_group_read_all)
        app.has_files_read_all = perm_analysis.get("has_files_read_all", app.has_files_read_all)
        app.has_calendar_access = perm_analysis.get("has_calendar_access", app.has_calendar_access)
        app.has_admin_consent = admin_consented
        app.consent_count = consent_count
        app.admin_consented = admin_consented
        app.is_new_app = False
        app.audience = app_analysis.get("audience") or app.audience
        app.is_internal = app_analysis.get("is_internal", app.is_internal)
        app.detection_reasons = app_analysis.get("detection_reasons", app.detection_reasons)
        app.app_data = app_data
        app.permissions_data = {"permissions": permissions}
        app.last_scan_at = datetime.utcnow()

        await self.db.commit()

    async def _store_permissions(
        self, app_internal_id: Any, tenant_id: str, permissions: list[dict[str, Any]]
    ) -> None:
        """Store detailed permission records.

        Args:
            app_internal_id: Internal app UUID
            tenant_id: Internal tenant UUID
            permissions: List of permission objects
        """
        for perm in permissions:
            perm_value = perm.get("value") or perm.get("appRoleId", "")

            # Check if permission already exists
            result = await self.db.execute(
                select(OAuthAppPermissionModel).where(
                    and_(
                        OAuthAppPermissionModel.app_id == app_internal_id,
                        OAuthAppPermissionModel.permission_value == perm_value,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.consent_state = perm.get("consentState", existing.consent_state)
                existing.updated_at = datetime.utcnow()
            else:
                # Check if high-risk
                from src.clients.oauth_apps import OAuthAppsClient

                is_high_risk = perm_value in OAuthAppsClient.HIGH_RISK_PERMISSIONS
                risk_category = None
                if is_high_risk:
                    risk_category = OAuthAppsClient.HIGH_RISK_PERMISSIONS[perm_value].get(
                        "category"
                    )

                new_perm = OAuthAppPermissionModel(
                    app_id=app_internal_id,
                    tenant_id=tenant_id,
                    permission_id=perm.get("id", ""),
                    permission_type=perm.get("permissionType", "Application"),
                    permission_value=perm_value,
                    display_name=perm.get("principalDisplayName"),
                    description=perm.get("description"),
                    is_high_risk=is_high_risk,
                    risk_category=risk_category,
                    is_admin_consent_required=perm.get("isAdminConsentRequired", False),
                    consent_state=perm.get("consentState", "NotConsented"),
                )
                self.db.add(new_perm)

        await self.db.commit()

    async def _store_consents(
        self, app_internal_id: Any, tenant_id: str, consents: list[dict[str, Any]]
    ) -> None:
        """Store consent records.

        Args:
            app_internal_id: Internal app UUID
            tenant_id: Internal tenant UUID
            consents: List of consent objects
        """
        for consent in consents:
            user_id = consent.get("principalId", "")

            # Skip if no user ID (admin consents don't always have principalId)
            if not user_id:
                continue

            # Check if consent already exists
            result = await self.db.execute(
                select(OAuthAppConsentModel).where(
                    and_(
                        OAuthAppConsentModel.app_id == app_internal_id,
                        OAuthAppConsentModel.user_id == user_id,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            # Parse dates
            consented_at = None
            expires_at = None

            if consent.get("startTime"):
                with contextlib.suppress(ValueError, AttributeError):
                    consented_at = datetime.fromisoformat(
                        consent["startTime"].replace("Z", "+00:00")
                    )

            if consent.get("expiryTime"):
                with contextlib.suppress(ValueError, AttributeError):
                    expires_at = datetime.fromisoformat(
                        consent["expiryTime"].replace("Z", "+00:00")
                    )

            if existing:
                # Update existing
                existing.scope = consent.get("scope", existing.scope)
                existing.consent_state = consent.get("consentState", existing.consent_state)
                existing.consent_type = consent.get("consentType", existing.consent_type)
                existing.updated_at = datetime.utcnow()
            else:
                new_consent = OAuthAppConsentModel(
                    app_id=app_internal_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_email=consent.get("principalDisplayName", ""),
                    user_display_name=consent.get("principalDisplayName"),
                    consent_type=consent.get("consentType", "Principal"),
                    scope=consent.get("scope", ""),
                    consent_state=consent.get("consentState", "Consented"),
                    consented_at=consented_at,
                    expires_at=expires_at,
                    consent_data=consent,
                )
                self.db.add(new_consent)

        await self.db.commit()

    async def _trigger_alert(self, app: OAuthAppModel, alert_type: str = None) -> None:
        """Trigger an alert for a suspicious/malicious app.

        Args:
            app: OAuth app that triggered the alert
            alert_type: Specific alert type (optional)
        """
        try:
            if not alert_type:
                alert_type = self._get_alert_type(app)

            # Create alert record
            alert = OAuthAppAlertModel(
                app_id=app.id,
                tenant_id=app.tenant_id,
                alert_type=alert_type,
                severity=app.risk_level,
                title=app.generate_alert_title(),
                description=app.generate_alert_description(),
                alert_metadata={
                    "app_id": app.app_id,
                    "display_name": app.display_name,
                    "publisher_name": app.publisher_name,
                    "high_risk_permissions": app.high_risk_permissions,
                    "consent_count": app.consent_count,
                    "detection_reasons": app.detection_reasons,
                },
            )

            self.db.add(alert)
            await self.db.commit()

            # Also trigger through alert engine for webhook notifications
            engine = AlertEngine(self.db)
            try:
                event_type = self._map_to_event_type(app)
                severity = self._map_to_severity_level(app.risk_level)

                await engine.process_event(
                    event_type=event_type,
                    severity=severity,
                    title=alert.title,
                    description=alert.description,
                    tenant_id=app.tenant_id,
                    metadata=alert.alert_metadata,
                )
            finally:
                await engine.close()

        except Exception as e:
            logger.error(f"Error triggering alert for app {app.id}: {e}")

    def _get_alert_type(self, app: OAuthAppModel) -> str:
        """Determine alert type based on app characteristics.

        Args:
            app: OAuth app model

        Returns:
            Alert type string
        """
        if app.has_mail_permissions and not app.is_microsoft_publisher:
            return self.EVENT_TYPE_MAIL_ACCESS
        elif app.high_risk_permissions and len(app.high_risk_permissions) > 2:
            return self.EVENT_TYPE_EXCESSIVE_PERMISSIONS
        elif not app.is_microsoft_publisher and not app.is_verified_publisher:
            return self.EVENT_TYPE_UNVERIFIED_PUBLISHER
        elif app.is_new_app:
            return self.EVENT_TYPE_NEW_APP
        return self.EVENT_TYPE_HIGH_RISK_PERMISSIONS

    def _map_to_event_type(self, app: OAuthAppModel) -> EventType:
        """Map app to event type for alert engine.

        Args:
            app: OAuth app model

        Returns:
            EventType enum value
        """
        # OAuth apps map to ADMIN_ACTION for now
        # Could extend EventType enum in the future
        return EventType.ADMIN_ACTION

    def _map_to_severity_level(self, risk_level: RiskLevel) -> SeverityLevel:
        """Map app risk level to alert severity level.

        Args:
            risk_level: App risk level

        Returns:
            SeverityLevel enum value
        """
        mapping = {
            RiskLevel.LOW: SeverityLevel.LOW,
            RiskLevel.MEDIUM: SeverityLevel.MEDIUM,
            RiskLevel.HIGH: SeverityLevel.HIGH,
            RiskLevel.CRITICAL: SeverityLevel.CRITICAL,
        }
        return mapping.get(risk_level, SeverityLevel.MEDIUM)

    async def _get_tenant(self, tenant_id: str) -> TenantModel | None:
        """Get tenant by internal ID.

        Args:
            tenant_id: Internal tenant UUID

        Returns:
            Tenant model or None
        """
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_apps(
        self,
        tenant_id: str | None = None,
        status: AppStatus | None = None,
        risk_level: RiskLevel | None = None,
        publisher_type: PublisherType | None = None,
        is_internal: bool | None = None,
        exclude_microsoft: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get OAuth apps with filtering.

        Args:
            tenant_id: Filter by tenant
            status: Filter by status
            risk_level: Filter by risk level
            publisher_type: Filter by publisher type
            is_internal: Filter by internal status
            exclude_microsoft: Whether to exclude Microsoft-owned apps
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with items and total count
        """
        query = select(OAuthAppModel)

        # Apply filters
        if tenant_id:
            query = query.where(OAuthAppModel.tenant_id == tenant_id)
        if status:
            query = query.where(OAuthAppModel.status == status)
        if risk_level:
            query = query.where(OAuthAppModel.risk_level == risk_level)
        if publisher_type:
            query = query.where(OAuthAppModel.publisher_type == publisher_type)
        if is_internal is not None:
            query = query.where(OAuthAppModel.is_internal == is_internal)
        if exclude_microsoft:
            query = query.where(OAuthAppModel.is_microsoft_publisher == False)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Apply pagination and ordering
        query = query.order_by(desc(OAuthAppModel.risk_score), desc(OAuthAppModel.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_app_by_id(self, app_id: str) -> OAuthAppModel | None:
        """Get a specific OAuth app by internal ID.

        Args:
            app_id: App UUID

        Returns:
            App model or None
        """
        result = await self.db.execute(select(OAuthAppModel).where(OAuthAppModel.id == app_id))
        return result.scalar_one_or_none()

    async def get_app_by_app_id(self, tenant_id: str, app_id: str) -> OAuthAppModel | None:
        """Get an OAuth app by Microsoft app ID.

        Args:
            tenant_id: Internal tenant UUID
            app_id: Microsoft Graph app ID

        Returns:
            App model or None
        """
        result = await self.db.execute(
            select(OAuthAppModel).where(
                and_(OAuthAppModel.tenant_id == tenant_id, OAuthAppModel.app_id == app_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_suspicious_apps(
        self, tenant_id: str | None = None, limit: int = 100
    ) -> list[OAuthAppModel]:
        """Get suspicious and malicious apps.

        Args:
            tenant_id: Optional tenant filter
            limit: Maximum results

        Returns:
            List of suspicious/malicious apps
        """
        query = select(OAuthAppModel).where(
            OAuthAppModel.status.in_([AppStatus.SUSPICIOUS, AppStatus.MALICIOUS])
        )

        if tenant_id:
            query = query.where(OAuthAppModel.tenant_id == tenant_id)

        query = query.order_by(desc(OAuthAppModel.risk_score))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_high_risk_apps(
        self, tenant_id: str | None = None, limit: int = 100
    ) -> list[OAuthAppModel]:
        """Get high-risk and critical apps.

        Args:
            tenant_id: Optional tenant filter
            limit: Maximum results

        Returns:
            List of high-risk apps
        """
        query = select(OAuthAppModel).where(
            OAuthAppModel.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
        )

        if tenant_id:
            query = query.where(OAuthAppModel.tenant_id == tenant_id)

        query = query.order_by(desc(OAuthAppModel.risk_score))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_app_permissions_detail(self, app_id: str) -> list[OAuthAppPermissionModel]:
        """Get detailed permissions for an app.

        Args:
            app_id: Internal app UUID

        Returns:
            List of permission models
        """
        result = await self.db.execute(
            select(OAuthAppPermissionModel)
            .where(OAuthAppPermissionModel.app_id == app_id)
            .order_by(desc(OAuthAppPermissionModel.is_high_risk))
        )
        return list(result.scalars().all())

    async def get_app_consents(self, app_id: str) -> list[OAuthAppConsentModel]:
        """Get consents for an app.

        Args:
            app_id: Internal app UUID

        Returns:
            List of consent models
        """
        result = await self.db.execute(
            select(OAuthAppConsentModel)
            .where(OAuthAppConsentModel.app_id == app_id)
            .order_by(desc(OAuthAppConsentModel.consented_at))
        )
        return list(result.scalars().all())

    async def revoke_app(self, app_id: str, revoke_type: str = "disable") -> dict[str, Any]:
        """Revoke/suspend an OAuth application.

        Args:
            app_id: Internal app UUID
            revoke_type: Type of revocation (disable, delete)

        Returns:
            Result dictionary
        """
        # Get the app
        app = await self.get_app_by_id(app_id)
        if not app:
            return {"success": False, "error": "App not found"}

        # Get tenant credentials
        tenant = await self._get_tenant(app.tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        try:
            # Decrypt credentials
            client_secret = encryption_service.decrypt(tenant.client_secret)

            # Create Graph client
            graph_client = MSGraphClient(
                tenant_id=tenant.tenant_id, client_id=tenant.client_id, client_secret=client_secret
            )

            # Create OAuth apps client
            oauth_client = OAuthAppsClient(graph_client)

            # Find service principal ID
            # We need to query by appId
            token = await graph_client.get_access_token()
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.microsoft.com/v1.0/servicePrincipals(appId='{app.app_id}')",
                    headers={"Authorization": f"Bearer {token}"},
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Failed to find service principal: {response.status_code}",
                    }

                sp_data = response.json()
                sp_id = sp_data.get("id")

                # Perform revocation
                if revoke_type == "delete":
                    success = await oauth_client.delete_service_principal(sp_id)
                else:
                    success = await oauth_client.disable_service_principal(sp_id)

                if success:
                    app.status = AppStatus.REVOKED
                    await self.db.commit()
                    return {"success": True, "message": f"App {revoke_type}d successfully"}
                else:
                    return {"success": False, "error": f"Failed to {revoke_type} app"}

        except Exception as e:
            logger.error(f"Error revoking app {app_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_alerts(
        self,
        tenant_id: str | None = None,
        acknowledged: bool | None = None,
        severity: RiskLevel | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get OAuth app alerts.

        Args:
            tenant_id: Filter by tenant
            acknowledged: Filter by acknowledgment status
            severity: Filter by severity
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with items and total count
        """
        query = select(OAuthAppAlertModel)

        if tenant_id:
            query = query.where(OAuthAppAlertModel.tenant_id == tenant_id)
        if acknowledged is not None:
            query = query.where(OAuthAppAlertModel.is_acknowledged == acknowledged)
        if severity:
            query = query.where(OAuthAppAlertModel.severity == severity)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Apply pagination and ordering
        query = query.order_by(desc(OAuthAppAlertModel.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def acknowledge_alert(
        self, alert_id: str, acknowledged_by: str
    ) -> OAuthAppAlertModel | None:
        """Acknowledge an OAuth app alert.

        Args:
            alert_id: Alert UUID
            acknowledged_by: User acknowledging the alert

        Returns:
            Updated alert or None if not found
        """
        result = await self.db.execute(
            select(OAuthAppAlertModel).where(OAuthAppAlertModel.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.is_acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def get_apps_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get summary of OAuth apps for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Summary statistics
        """
        # Get counts by risk level
        risk_counts = {}
        for risk in RiskLevel:
            count_result = await self.db.execute(
                select(func.count(OAuthAppModel.id)).where(
                    and_(OAuthAppModel.tenant_id == tenant_id, OAuthAppModel.risk_level == risk)
                )
            )
            risk_counts[risk.value] = count_result.scalar()

        # Get counts by status
        status_counts = {}
        for status in AppStatus:
            count_result = await self.db.execute(
                select(func.count(OAuthAppModel.id)).where(
                    and_(OAuthAppModel.tenant_id == tenant_id, OAuthAppModel.status == status)
                )
            )
            status_counts[status.value] = count_result.scalar()

        # Get high-risk apps with mail access
        mail_apps_result = await self.db.execute(
            select(func.count(OAuthAppModel.id)).where(
                and_(
                    OAuthAppModel.tenant_id == tenant_id,
                    OAuthAppModel.is_microsoft_publisher == False,
                    OAuthAppModel.publisher_type != PublisherType.VERIFIED,
                )
            )
        )
        mail_apps_count = mail_apps_result.scalar()

        # Get unverified publisher apps
        unverified_result = await self.db.execute(
            select(func.count(OAuthAppModel.id)).where(
                and_(
                    OAuthAppModel.tenant_id == tenant_id,
                    OAuthAppModel.publisher_type == PublisherType.UNVERIFIED,
                )
            )
        )
        unverified_count = unverified_result.scalar()

        # Get recent alerts count
        alerts_result = await self.db.execute(
            select(func.count(OAuthAppAlertModel.id)).where(
                OAuthAppAlertModel.tenant_id == tenant_id
            )
        )
        alerts_count = alerts_result.scalar()

        # Get unacknowledged alerts count
        unack_result = await self.db.execute(
            select(func.count(OAuthAppAlertModel.id)).where(
                and_(
                    OAuthAppAlertModel.tenant_id == tenant_id,
                    OAuthAppAlertModel.is_acknowledged == False,
                )
            )
        )
        unack_count = unack_result.scalar()

        return {
            "total_apps": sum(risk_counts.values()),
            "by_risk_level": risk_counts,
            "by_status": status_counts,
            "mail_access_apps": mail_apps_count,
            "unverified_publisher_apps": unverified_count,
            "total_alerts": alerts_count,
            "unacknowledged_alerts": unack_count,
        }
