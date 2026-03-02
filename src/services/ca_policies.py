"""Conditional Access policy monitoring service for SpecterDefence."""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.engine import AlertEngine
from src.clients.ca_policies import CAPoliciesClient
from src.clients.ms_graph import MSGraphClient
from src.models.alerts import EventType, SeverityLevel
from src.models.ca_policies import (
    AlertSeverity,
    CABaselineConfigModel,
    CAPolicyAlertModel,
    CAPolicyChangeModel,
    CAPolicyModel,
    ChangeType,
    PolicyState,
)
from src.models.db import TenantModel
from src.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class CAPoliciesService:
    """Service for monitoring and managing Conditional Access policies."""

    # Alert severity mapping
    SEVERITY_MAPPING = {
        "critical": AlertSeverity.CRITICAL,
        "high": AlertSeverity.HIGH,
        "medium": AlertSeverity.MEDIUM,
        "low": AlertSeverity.LOW,
        "none": AlertSeverity.LOW,
        "positive": AlertSeverity.LOW,
    }

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service.
        
        Args:
            db_session: Async database session
        """
        self.db = db_session

    async def scan_tenant_policies(
        self,
        tenant_id: str,
        trigger_alerts: bool = True,
        compare_baseline: bool = True
    ) -> dict[str, Any]:
        """Scan all Conditional Access policies for a tenant.
        
        Args:
            tenant_id: Internal tenant UUID
            trigger_alerts: Whether to trigger alerts for policy changes
            compare_baseline: Whether to compare against security baseline
            
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
            tenant_id=tenant.tenant_id,
            client_id=tenant.client_id,
            client_secret=client_secret
        )

        # Create CA policies client
        ca_client = CAPoliciesClient(graph_client)

        # Fetch all policies
        logger.info(f"Scanning CA policies for tenant {tenant.name}")
        policies = await ca_client.get_policies()

        # Get baseline config if comparison is enabled
        baseline_config = None
        if compare_baseline:
            baseline_config = await self._get_baseline_config(tenant_id)

        results = {
            "policies_found": len(policies),
            "new_policies": 0,
            "updated_policies": 0,
            "changes_detected": 0,
            "alerts_triggered": 0,
            "baseline_violations": 0,
            "disabled_policies": 0,
            "mfa_policies": 0,
        }

        # Track current policy IDs for deletion detection
        current_policy_ids = set()

        # Process each policy
        for policy_data in policies:
            try:
                policy_id = policy_data.get("id")
                current_policy_ids.add(policy_id)

                # Analyze policy
                analysis = ca_client.analyze_policy(policy_data)

                # Check if policy already exists
                existing_policy = await self._get_existing_policy(tenant_id, policy_id)

                if existing_policy:
                    # Compare for changes
                    policy_result = await self._process_existing_policy(
                        tenant_id=tenant_id,
                        existing_policy=existing_policy,
                        policy_data=policy_data,
                        analysis=analysis,
                        ca_client=ca_client,
                        trigger_alerts=trigger_alerts
                    )

                    if policy_result.get("is_updated"):
                        results["updated_policies"] += 1
                    if policy_result.get("changes_detected"):
                        results["changes_detected"] += 1
                    if policy_result.get("alert_triggered"):
                        results["alerts_triggered"] += 1
                else:
                    # Create new policy
                    policy_result = await self._create_policy(
                        tenant_id=tenant_id,
                        policy_data=policy_data,
                        analysis=analysis
                    )
                    results["new_policies"] += 1

                    # Trigger alert for new policy
                    if trigger_alerts:
                        await self._trigger_alert(
                            policy=policy_result,
                            change_type=ChangeType.CREATED,
                            changes_summary=["New Conditional Access policy detected"]
                        )
                        results["alerts_triggered"] += 1

                # Check baseline compliance
                if compare_baseline and baseline_config:
                    compliance = ca_client.check_baseline_compliance(
                        policy_data, baseline_config.__dict__
                    )
                    if not compliance["is_compliant"]:
                        results["baseline_violations"] += 1
                        # Update policy baseline status
                        await self._update_baseline_status(
                            tenant_id, policy_id, False, compliance["violations"]
                        )

                # Track statistics
                if analysis["is_disabled"]:
                    results["disabled_policies"] += 1
                if analysis["is_mfa_required"]:
                    results["mfa_policies"] += 1

            except Exception as e:
                logger.error(f"Error processing policy {policy_data.get('id')}: {e}")
                continue

        # Check for deleted policies
        deleted_count = await self._detect_deleted_policies(tenant_id, current_policy_ids)
        if deleted_count > 0 and trigger_alerts:
            results["alerts_triggered"] += deleted_count

        return results

    async def _process_existing_policy(
        self,
        tenant_id: str,
        existing_policy: CAPolicyModel,
        policy_data: dict[str, Any],
        analysis: dict[str, Any],
        ca_client: CAPoliciesClient,
        trigger_alerts: bool
    ) -> dict[str, Any]:
        """Process an existing policy, detecting changes.
        
        Args:
            tenant_id: Internal tenant UUID
            existing_policy: Existing policy model
            policy_data: New policy data from Graph API
            analysis: Policy analysis results
            ca_client: CAPoliciesClient instance
            trigger_alerts: Whether to trigger alerts
            
        Returns:
            Processing results
        """
        is_updated = False
        changes_detected = False
        alert_triggered = False

        # Check for state changes
        old_state = existing_policy.state.value
        new_state = analysis["state"]

        if old_state != new_state:
            is_updated = True
            changes_detected = True

            # Record state change
            change_type = ChangeType.DISABLED if new_state == "disabled" else ChangeType.ENABLED
            if new_state == "reportOnly":
                change_type = ChangeType.UPDATED

            # Create change record
            change_record = await self._record_change(
                policy_id=existing_policy.id,
                tenant_id=tenant_id,
                change_type=change_type,
                changes_summary=[f"State changed from {old_state} to {new_state}"],
                security_impact="high" if new_state == "disabled" else "low",
                mfa_removed=(new_state == "disabled" and existing_policy.is_mfa_required),
                previous_state={"state": old_state},
                new_state={"state": new_state}
            )

            # Trigger alert for policy disable
            if trigger_alerts and change_type == ChangeType.DISABLED:
                await self._trigger_alert(
                    policy=existing_policy,
                    change_type=ChangeType.DISABLED,
                    changes_summary=["Policy has been disabled"],
                    change_id=change_record.id if change_record else None
                )
                alert_triggered = True

        # Check for changes in policy configuration
        old_analysis = {
            "grant_controls": existing_policy.grant_controls,
            "is_mfa_required": existing_policy.is_mfa_required,
            "applies_to_all_users": existing_policy.applies_to_all_users,
            "applies_to_all_apps": existing_policy.applies_to_all_apps,
            "has_location_conditions": existing_policy.has_location_conditions,
            "requires_compliant_device": existing_policy.requires_compliant_device,
        }

        comparison = ca_client.compare_policies(old_analysis, analysis)

        if comparison["has_changes"] and not changes_detected:
            is_updated = True
            changes_detected = True

            # Determine change type
            if comparison["mfa_removed"] or comparison["broadened_scope"]:
                change_type = ChangeType.UPDATED
            else:
                change_type = ChangeType.UPDATED

            # Create change record
            change_record = await self._record_change(
                policy_id=existing_policy.id,
                tenant_id=tenant_id,
                change_type=change_type,
                changes_summary=comparison["changes_summary"],
                security_impact=comparison["security_impact"],
                mfa_removed=comparison["mfa_removed"],
                broadened_scope=comparison["broadened_scope"],
                narrowed_scope=comparison["narrowed_scope"],
                previous_state=old_analysis,
                new_state=analysis
            )

            # Trigger alert for significant changes
            if trigger_alerts and comparison["security_impact"] in ["high", "critical"]:
                await self._trigger_alert(
                    policy=existing_policy,
                    change_type=change_type,
                    changes_summary=comparison["changes_summary"],
                    change_id=change_record.id if change_record else None,
                    severity=self.SEVERITY_MAPPING.get(comparison["security_impact"], AlertSeverity.MEDIUM)
                )
                alert_triggered = True

        # Update policy record
        await self._update_policy(existing_policy, policy_data, analysis)

        return {
            "is_updated": is_updated,
            "changes_detected": changes_detected,
            "alert_triggered": alert_triggered,
        }

    async def _create_policy(
        self,
        tenant_id: str,
        policy_data: dict[str, Any],
        analysis: dict[str, Any]
    ) -> CAPolicyModel:
        """Create a new CA policy record.
        
        Args:
            tenant_id: Internal tenant UUID
            policy_data: Policy data from Graph API
            analysis: Policy analysis results
            
        Returns:
            Created policy model
        """
        # Parse timestamps
        policy_created_at = None
        policy_modified_at = None

        if policy_data.get("createdDateTime"):
            try:
                policy_created_at = datetime.fromisoformat(
                    policy_data["createdDateTime"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        if policy_data.get("modifiedDateTime"):
            try:
                policy_modified_at = datetime.fromisoformat(
                    policy_data["modifiedDateTime"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        policy = CAPolicyModel(
            tenant_id=tenant_id,
            policy_id=policy_data.get("id", ""),
            display_name=policy_data.get("displayName", "Unnamed Policy"),
            description=policy_data.get("description"),
            state=PolicyState(analysis["state"]),
            grant_controls=analysis["grant_controls"],
            grant_controls_operator=analysis["grant_controls_operator"],
            is_mfa_required=analysis["is_mfa_required"],
            requires_compliant_device=analysis["requires_compliant_device"],
            requires_hybrid_joined_device=analysis["requires_hybrid_joined_device"],
            sign_in_frequency=analysis["sign_in_frequency"],
            sign_in_frequency_authentication_type=analysis["sign_in_frequency_authentication_type"],
            applies_to_all_users=analysis["applies_to_all_users"],
            applies_to_all_apps=analysis["applies_to_all_apps"],
            includes_guests_or_external=analysis["includes_guests_or_external"],
            includes_vip_users=analysis["includes_vip_users"],
            requires_high_risk_level=analysis["requires_high_risk_level"],
            requires_medium_risk_level=analysis["requires_medium_risk_level"],
            requires_low_risk_level=analysis["requires_low_risk_level"],
            has_location_conditions=analysis["has_location_conditions"],
            trusted_locations_only=analysis["trusted_locations_only"],
            has_device_conditions=analysis["has_device_conditions"],
            includes_mobile_platforms=analysis["includes_mobile_platforms"],
            security_score=analysis["security_score"],
            policy_data=policy_data,
            policy_created_at=policy_created_at,
            policy_modified_at=policy_modified_at,
        )

        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)

        return policy

    async def _update_policy(
        self,
        policy: CAPolicyModel,
        policy_data: dict[str, Any],
        analysis: dict[str, Any]
    ) -> None:
        """Update an existing CA policy record.
        
        Args:
            policy: Existing policy model
            policy_data: Updated policy data from Graph API
            analysis: Updated policy analysis results
        """
        policy.display_name = policy_data.get("displayName", policy.display_name)
        policy.description = policy_data.get("description") or policy.description
        policy.state = PolicyState(analysis["state"])
        policy.grant_controls = analysis["grant_controls"]
        policy.grant_controls_operator = analysis["grant_controls_operator"]
        policy.is_mfa_required = analysis["is_mfa_required"]
        policy.requires_compliant_device = analysis["requires_compliant_device"]
        policy.requires_hybrid_joined_device = analysis["requires_hybrid_joined_device"]
        policy.sign_in_frequency = analysis["sign_in_frequency"]
        policy.sign_in_frequency_authentication_type = analysis["sign_in_frequency_authentication_type"]
        policy.applies_to_all_users = analysis["applies_to_all_users"]
        policy.applies_to_all_apps = analysis["applies_to_all_apps"]
        policy.includes_guests_or_external = analysis["includes_guests_or_external"]
        policy.includes_vip_users = analysis["includes_vip_users"]
        policy.requires_high_risk_level = analysis["requires_high_risk_level"]
        policy.requires_medium_risk_level = analysis["requires_medium_risk_level"]
        policy.requires_low_risk_level = analysis["requires_low_risk_level"]
        policy.has_location_conditions = analysis["has_location_conditions"]
        policy.trusted_locations_only = analysis["trusted_locations_only"]
        policy.has_device_conditions = analysis["has_device_conditions"]
        policy.includes_mobile_platforms = analysis["includes_mobile_platforms"]
        policy.security_score = analysis["security_score"]
        policy.policy_data = policy_data
        policy.last_scan_at = datetime.utcnow()

        if policy_data.get("modifiedDateTime"):
            try:
                policy.policy_modified_at = datetime.fromisoformat(
                    policy_data["modifiedDateTime"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        await self.db.commit()

    async def _detect_deleted_policies(
        self,
        tenant_id: str,
        current_policy_ids: set
    ) -> int:
        """Detect policies that have been deleted.
        
        Args:
            tenant_id: Internal tenant UUID
            current_policy_ids: Set of current policy IDs from Graph API
            
        Returns:
            Number of deleted policies detected
        """
        result = await self.db.execute(
            select(CAPolicyModel).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.state != PolicyState.DISABLED  # Already marked disabled
                )
            )
        )
        stored_policies = result.scalars().all()

        deleted_count = 0
        for policy in stored_policies:
            if policy.policy_id not in current_policy_ids:
                # Policy was deleted
                policy.state = PolicyState.DISABLED
                await self.db.commit()

                # Record deletion
                await self._record_change(
                    policy_id=policy.id,
                    tenant_id=tenant_id,
                    change_type=ChangeType.DELETED,
                    changes_summary=["Policy has been deleted from Azure AD"],
                    security_impact="high",
                    previous_state=policy.policy_data,
                    new_state={}
                )

                # Trigger alert
                await self._trigger_alert(
                    policy=policy,
                    change_type=ChangeType.DELETED,
                    changes_summary=["Policy has been permanently deleted"],
                    severity=AlertSeverity.HIGH
                )

                deleted_count += 1

        return deleted_count

    async def _record_change(
        self,
        policy_id: Any,
        tenant_id: str,
        change_type: ChangeType,
        changes_summary: list[str],
        security_impact: str = "none",
        mfa_removed: bool = False,
        broadened_scope: bool = False,
        narrowed_scope: bool = False,
        previous_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        changed_by: str | None = None
    ) -> CAPolicyChangeModel | None:
        """Record a policy change.
        
        Args:
            policy_id: Internal policy UUID
            tenant_id: Internal tenant UUID
            change_type: Type of change
            changes_summary: Summary of changes
            security_impact: Security impact level
            mfa_removed: Whether MFA was removed
            broadened_scope: Whether scope was broadened
            narrowed_scope: Whether scope was narrowed
            previous_state: Previous policy state
            new_state: New policy state
            changed_by: User who made the change
            
        Returns:
            Created change record or None
        """
        try:
            change = CAPolicyChangeModel(
                policy_id=policy_id,
                tenant_id=tenant_id,
                change_type=change_type,
                changed_by=changed_by,
                changes_summary=changes_summary,
                security_impact=security_impact,
                mfa_removed=mfa_removed,
                broadened_scope=broadened_scope,
                narrowed_scope=narrowed_scope,
                previous_state=previous_state,
                new_state=new_state or {},
            )

            self.db.add(change)
            await self.db.commit()
            await self.db.refresh(change)

            return change
        except Exception as e:
            logger.error(f"Error recording change: {e}")
            return None

    async def _trigger_alert(
        self,
        policy: CAPolicyModel,
        change_type: ChangeType,
        changes_summary: list[str],
        change_id: Any | None = None,
        severity: AlertSeverity | None = None
    ) -> None:
        """Trigger an alert for a policy change.
        
        Args:
            policy: Policy that triggered the alert
            change_type: Type of change
            changes_summary: Summary of changes
            change_id: Optional change record ID
            severity: Alert severity
        """
        try:
            if severity is None:
                # Determine severity based on change type
                if change_type == ChangeType.DISABLED:
                    severity = AlertSeverity.HIGH
                    if policy.is_mfa_required:
                        severity = AlertSeverity.CRITICAL
                elif change_type == ChangeType.DELETED:
                    severity = AlertSeverity.HIGH
                elif change_type == ChangeType.BASELINE_DRIFT:
                    severity = AlertSeverity.MEDIUM
                else:
                    severity = AlertSeverity.LOW

            # Create alert record
            alert = CAPolicyAlertModel(
                policy_id=policy.id,
                change_id=change_id,
                tenant_id=policy.tenant_id,
                alert_type=change_type,
                severity=severity,
                title=policy.generate_alert_title(change_type),
                description=policy.generate_alert_description(change_type, {"changes": changes_summary}),
                detection_reasons=changes_summary,
                alert_metadata={
                    "policy_id": policy.policy_id,
                    "display_name": policy.display_name,
                    "state": policy.state.value,
                    "is_mfa_required": policy.is_mfa_required,
                    "applies_to_all_users": policy.applies_to_all_users,
                    "applies_to_all_apps": policy.applies_to_all_apps,
                    "changes": changes_summary,
                }
            )

            self.db.add(alert)
            await self.db.commit()

            # Also trigger through alert engine for webhook notifications
            engine = AlertEngine(self.db)
            try:
                await engine.process_event(
                    event_type=EventType.ADMIN_ACTION,
                    severity=SeverityLevel(severity.value),
                    title=alert.title,
                    description=alert.description,
                    tenant_id=policy.tenant_id,
                    metadata=alert.alert_metadata,
                )
            finally:
                await engine.close()

        except Exception as e:
            logger.error(f"Error triggering alert for policy {policy.id}: {e}")

    async def _update_baseline_status(
        self,
        tenant_id: str,
        policy_id: str,
        compliant: bool,
        violations: list[str]
    ) -> None:
        """Update policy baseline compliance status.
        
        Args:
            tenant_id: Internal tenant UUID
            policy_id: Microsoft Graph policy ID
            compliant: Whether policy is compliant
            violations: List of violations
        """
        policy = await self._get_existing_policy(tenant_id, policy_id)
        if policy:
            policy.baseline_compliant = compliant
            await self.db.commit()

    async def _get_existing_policy(
        self,
        tenant_id: str,
        policy_id: str
    ) -> CAPolicyModel | None:
        """Get existing policy from database.
        
        Args:
            tenant_id: Internal tenant UUID
            policy_id: Microsoft Graph policy ID
            
        Returns:
            Existing policy or None
        """
        result = await self.db.execute(
            select(CAPolicyModel).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.policy_id == policy_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_tenant(self, tenant_id: str) -> TenantModel | None:
        """Get tenant by internal ID.
        
        Args:
            tenant_id: Internal tenant UUID
            
        Returns:
            Tenant model or None
        """
        result = await self.db.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def _get_baseline_config(self, tenant_id: str) -> CABaselineConfigModel | None:
        """Get baseline configuration for a tenant.
        
        Args:
            tenant_id: Internal tenant UUID
            
        Returns:
            Baseline config or None
        """
        result = await self.db.execute(
            select(CABaselineConfigModel).where(
                CABaselineConfigModel.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def set_baseline_config(
        self,
        tenant_id: str,
        config_data: dict[str, Any],
        created_by: str | None = None
    ) -> CABaselineConfigModel:
        """Set or update security baseline configuration.
        
        Args:
            tenant_id: Internal tenant UUID
            config_data: Baseline configuration data
            created_by: User who created the baseline
            
        Returns:
            Created or updated baseline config
        """
        existing = await self._get_baseline_config(tenant_id)

        if existing:
            # Update existing config
            existing.require_mfa_for_admins = config_data.get("require_mfa_for_admins", True)
            existing.require_mfa_for_all_users = config_data.get("require_mfa_for_all_users", False)
            existing.block_legacy_auth = config_data.get("block_legacy_auth", True)
            existing.require_compliant_or_hybrid_joined = config_data.get("require_compliant_or_hybrid_joined", False)
            existing.block_high_risk_signins = config_data.get("block_high_risk_signins", True)
            existing.block_unknown_locations = config_data.get("block_unknown_locations", False)
            existing.require_mfa_for_guests = config_data.get("require_mfa_for_guests", True)
            existing.custom_requirements = config_data.get("custom_requirements", {})
            await self.db.commit()
            return existing
        else:
            # Create new config
            config = CABaselineConfigModel(
                tenant_id=tenant_id,
                require_mfa_for_admins=config_data.get("require_mfa_for_admins", True),
                require_mfa_for_all_users=config_data.get("require_mfa_for_all_users", False),
                block_legacy_auth=config_data.get("block_legacy_auth", True),
                require_compliant_or_hybrid_joined=config_data.get("require_compliant_or_hybrid_joined", False),
                block_high_risk_signins=config_data.get("block_high_risk_signins", True),
                block_unknown_locations=config_data.get("block_unknown_locations", False),
                require_mfa_for_guests=config_data.get("require_mfa_for_guests", True),
                custom_requirements=config_data.get("custom_requirements", {}),
                created_by=created_by,
            )
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)
            return config

    # Public API methods

    async def get_policies(
        self,
        tenant_id: str | None = None,
        state: PolicyState | None = None,
        is_baseline_policy: bool | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """Get CA policies with filtering.
        
        Args:
            tenant_id: Filter by tenant
            state: Filter by state
            is_baseline_policy: Filter by baseline status
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            Dictionary with items and total count
        """
        query = select(CAPolicyModel)

        if tenant_id:
            query = query.where(CAPolicyModel.tenant_id == tenant_id)
        if state:
            query = query.where(CAPolicyModel.state == state)
        if is_baseline_policy is not None:
            query = query.where(CAPolicyModel.is_baseline_policy == is_baseline_policy)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(CAPolicyModel.id)).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(desc(CAPolicyModel.security_score), desc(CAPolicyModel.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_policy_by_id(self, policy_id: str) -> CAPolicyModel | None:
        """Get a specific CA policy by internal ID.
        
        Args:
            policy_id: Policy UUID
            
        Returns:
            Policy model or None
        """
        result = await self.db.execute(
            select(CAPolicyModel).where(CAPolicyModel.id == policy_id)
        )
        return result.scalar_one_or_none()

    async def get_policy_changes(
        self,
        policy_id: str | None = None,
        tenant_id: str | None = None,
        change_type: ChangeType | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """Get policy change history.
        
        Args:
            policy_id: Filter by policy
            tenant_id: Filter by tenant
            change_type: Filter by change type
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            Dictionary with items and total count
        """
        query = select(CAPolicyChangeModel)

        if policy_id:
            query = query.where(CAPolicyChangeModel.policy_id == policy_id)
        if tenant_id:
            query = query.where(CAPolicyChangeModel.tenant_id == tenant_id)
        if change_type:
            query = query.where(CAPolicyChangeModel.change_type == change_type)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(CAPolicyChangeModel.id)).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(desc(CAPolicyChangeModel.detected_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_alerts(
        self,
        tenant_id: str | None = None,
        acknowledged: bool | None = None,
        severity: AlertSeverity | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """Get CA policy alerts.
        
        Args:
            tenant_id: Filter by tenant
            acknowledged: Filter by acknowledgment status
            severity: Filter by severity
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            Dictionary with items and total count
        """
        query = select(CAPolicyAlertModel)

        if tenant_id:
            query = query.where(CAPolicyAlertModel.tenant_id == tenant_id)
        if acknowledged is not None:
            query = query.where(CAPolicyAlertModel.is_acknowledged == acknowledged)
        if severity:
            query = query.where(CAPolicyAlertModel.severity == severity)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(CAPolicyAlertModel.id)).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(desc(CAPolicyAlertModel.created_at))
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
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> CAPolicyAlertModel | None:
        """Acknowledge a CA policy alert.
        
        Args:
            alert_id: Alert UUID
            acknowledged_by: User acknowledging the alert
            
        Returns:
            Updated alert or None if not found
        """
        result = await self.db.execute(
            select(CAPolicyAlertModel).where(CAPolicyAlertModel.id == alert_id)
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

    async def get_disabled_policies(
        self,
        tenant_id: str | None = None,
        limit: int = 100
    ) -> list[CAPolicyModel]:
        """Get disabled CA policies.
        
        Args:
            tenant_id: Optional tenant filter
            limit: Maximum results
            
        Returns:
            List of disabled policies
        """
        query = select(CAPolicyModel).where(
            CAPolicyModel.state == PolicyState.DISABLED
        )

        if tenant_id:
            query = query.where(CAPolicyModel.tenant_id == tenant_id)

        query = query.order_by(desc(CAPolicyModel.updated_at))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_mfa_policies(
        self,
        tenant_id: str | None = None,
        limit: int = 100
    ) -> list[CAPolicyModel]:
        """Get policies that require MFA.
        
        Args:
            tenant_id: Optional tenant filter
            limit: Maximum results
            
        Returns:
            List of MFA policies
        """
        query = select(CAPolicyModel).where(
            and_(
                CAPolicyModel.is_mfa_required == True,
                CAPolicyModel.state == PolicyState.ENABLED
            )
        )

        if tenant_id:
            query = query.where(CAPolicyModel.tenant_id == tenant_id)

        query = query.order_by(desc(CAPolicyModel.security_score))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_policies_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get summary of CA policies for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Summary statistics
        """
        # Get counts by state
        enabled_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.state == PolicyState.ENABLED
                )
            )
        )
        disabled_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.state == PolicyState.DISABLED
                )
            )
        )
        report_only_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.state == PolicyState.REPORT_ONLY
                )
            )
        )

        # Get MFA policies count
        mfa_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.is_mfa_required == True
                )
            )
        )

        # Get baseline policies count
        baseline_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.is_baseline_policy == True
                )
            )
        )

        # Get baseline compliant count
        compliant_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.baseline_compliant == True
                )
            )
        )

        # Get recent changes count (last 7 days)
        recent_changes_count = await self.db.execute(
            select(func.count(CAPolicyChangeModel.id)).where(
                and_(
                    CAPolicyChangeModel.tenant_id == tenant_id,
                    CAPolicyChangeModel.detected_at >= datetime.utcnow() - timedelta(days=7)
                )
            )
        )

        # Get high severity alerts count
        high_severity_count = await self.db.execute(
            select(func.count(CAPolicyAlertModel.id)).where(
                and_(
                    CAPolicyAlertModel.tenant_id == tenant_id,
                    CAPolicyAlertModel.severity.in_([AlertSeverity.HIGH, AlertSeverity.CRITICAL]),
                    CAPolicyAlertModel.is_acknowledged == False
                )
            )
        )

        # Get policies covering all users
        all_users_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.applies_to_all_users == True
                )
            )
        )

        # Get policies covering all apps
        all_apps_count = await self.db.execute(
            select(func.count(CAPolicyModel.id)).where(
                and_(
                    CAPolicyModel.tenant_id == tenant_id,
                    CAPolicyModel.applies_to_all_apps == True
                )
            )
        )

        total = enabled_count.scalar() + disabled_count.scalar() + report_only_count.scalar()
        baseline_violations = baseline_count.scalar() - compliant_count.scalar()

        return {
            "total_policies": total,
            "enabled": enabled_count.scalar(),
            "disabled": disabled_count.scalar(),
            "report_only": report_only_count.scalar(),
            "mfa_policies": mfa_count.scalar(),
            "baseline_policies": baseline_count.scalar(),
            "baseline_compliant": compliant_count.scalar(),
            "baseline_violations": max(0, baseline_violations),
            "recent_changes": recent_changes_count.scalar(),
            "high_severity_alerts": high_severity_count.scalar(),
            "policies_covering_all_users": all_users_count.scalar(),
            "policies_covering_all_apps": all_apps_count.scalar(),
        }
