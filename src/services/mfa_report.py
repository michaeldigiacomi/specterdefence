"""MFA Enrollment Tracking service for SpecterDefence."""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.mfa_report import MFAReportClient
from src.clients.ms_graph import MSGraphClient
from src.models.db import TenantModel
from src.models.mfa_report import (
    ComplianceStatus,
    MFAComplianceAlertModel,
    MFAEnrollmentHistoryModel,
    MFAStrengthLevel,
    MFAUserModel,
)
from src.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class MFAReportService:
    """Service for MFA enrollment tracking and reporting."""

    # Compliance thresholds
    ADMIN_MFA_REQUIRED = True
    USER_MFA_TARGET_PERCENTAGE = 95.0

    # MFA strength priority for comparison
    STRENGTH_PRIORITY = {
        MFAStrengthLevel.STRONG: 3,
        MFAStrengthLevel.MODERATE: 2,
        MFAStrengthLevel.WEAK: 1,
        MFAStrengthLevel.NONE: 0,
    }

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db_session: Async database session
        """
        self.db = db_session

    async def scan_tenant_mfa(
        self, tenant_id: str, full_scan: bool = True, check_compliance: bool = True
    ) -> dict[str, Any]:
        """Scan all users for MFA enrollment status.

        Args:
            tenant_id: Internal tenant UUID
            full_scan: Whether to perform a full scan of all users
            check_compliance: Whether to check compliance after scan

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

        # Create MFA report client
        mfa_client = MFAReportClient(graph_client)

        logger.info(f"Starting MFA scan for tenant {tenant.name}")

        # Scan all users
        results: dict[str, Any] = {
            "users_scanned": 0,
            "new_mfa_registrations": 0,
            "compliance_violations": 0,
            "critical_findings": 0,
        }

        try:
            # Get all users with MFA data
            users_data = await mfa_client.scan_all_users_mfa()
            results["users_scanned"] = len(users_data)

            # Process each user
            for user_data in users_data:
                try:
                    user_result = await self._process_user_mfa_data(
                        tenant_id=tenant_id, user_data=user_data
                    )

                    if user_result.get("is_new_registration"):
                        results["new_mfa_registrations"] += 1
                    if user_result.get("is_critical_finding"):
                        results["critical_findings"] += 1

                except Exception as e:
                    logger.error(
                        f"Error processing user {user_data.get('user_principal_name')}: {e}"
                    )
                    continue

            # Check compliance if requested
            if check_compliance:
                compliance_result = await self._check_tenant_compliance(tenant_id)
                results["compliance_violations"] = compliance_result["total_violations"]

            # Create enrollment snapshot
            await self._create_enrollment_snapshot(tenant_id)

            results["success"] = True
            results["message"] = (
                f"Scan completed. {results['users_scanned']} users scanned, "
                f"{results['new_mfa_registrations']} new MFA registrations, "
                f"{results['critical_findings']} critical findings, "
                f"{results['compliance_violations']} compliance violations."
            )

        except Exception as e:
            logger.error(f"Error during MFA scan: {e}")
            results["success"] = False
            results["message"] = f"Scan failed: {str(e)}"

        return results

    async def _process_user_mfa_data(
        self, tenant_id: str, user_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Process and store MFA data for a user.

        Args:
            tenant_id: Internal tenant UUID
            user_data: User MFA data from Graph API

        Returns:
            Processing results
        """
        user_id = user_data.get("user_id")
        user_principal_name = user_data.get("user_principal_name")

        # Check if user already exists
        existing_user = await self._get_existing_user(tenant_id, user_id)

        # Determine MFA strength
        strength_str = user_data.get("strength", "none")
        try:
            mfa_strength = MFAStrengthLevel(strength_str)
        except ValueError:
            mfa_strength = MFAStrengthLevel.NONE

        # Determine compliance status
        is_admin = user_data.get("is_admin", False)
        is_mfa_registered = user_data.get("is_mfa_registered", False)

        if existing_user and existing_user.compliance_exempt:
            compliance_status = ComplianceStatus.EXEMPT
        elif is_admin:
            compliance_status = (
                ComplianceStatus.COMPLIANT
                if is_mfa_registered
                and mfa_strength in [MFAStrengthLevel.STRONG, MFAStrengthLevel.MODERATE]
                else ComplianceStatus.NON_COMPLIANT
            )
        else:
            compliance_status = (
                ComplianceStatus.COMPLIANT if is_mfa_registered else ComplianceStatus.NON_COMPLIANT
            )

        result = {
            "is_new_registration": False,
            "is_critical_finding": False,
        }

        # Track new registrations
        if is_mfa_registered and existing_user and not existing_user.is_mfa_registered:
            result["is_new_registration"] = True

        # Track critical findings (admin without MFA)
        if is_admin and not is_mfa_registered:
            result["is_critical_finding"] = True
            # Create compliance alert
            await self._create_compliance_alert(
                tenant_id=tenant_id,
                user_id=existing_user.id if existing_user else None,
                alert_type="admin_no_mfa",
                severity="critical",
                title=f"Critical: Admin without MFA - {user_principal_name}",
                description=f"Admin user {user_principal_name} does not have MFA registered. This is a critical security risk.",
            )

        # Track weak MFA for admins
        if is_admin and is_mfa_registered and mfa_strength == MFAStrengthLevel.WEAK:
            await self._create_compliance_alert(
                tenant_id=tenant_id,
                user_id=existing_user.id if existing_user else None,
                alert_type="admin_weak_mfa",
                severity="high",
                title=f"High: Admin with weak MFA - {user_principal_name}",
                description=f"Admin user {user_principal_name} is using weak MFA (SMS/Voice). Consider upgrading to Authenticator app or FIDO2.",
            )

        if existing_user:
            # Update existing user
            await self._update_user_mfa_data(
                existing_user, user_data, mfa_strength, compliance_status
            )
        else:
            # Create new user
            await self._create_user_mfa_data(tenant_id, user_data, mfa_strength, compliance_status)

        return result

    async def _create_user_mfa_data(
        self,
        tenant_id: str,
        user_data: dict[str, Any],
        mfa_strength: MFAStrengthLevel,
        compliance_status: ComplianceStatus,
    ) -> MFAUserModel:
        """Create new MFA user record.

        Args:
            tenant_id: Internal tenant UUID
            user_data: User MFA data
            mfa_strength: Calculated MFA strength
            compliance_status: Calculated compliance status

        Returns:
            Created user model
        """
        user = MFAUserModel(
            tenant_id=tenant_id,
            user_id=user_data.get("user_id"),
            user_principal_name=user_data.get("user_principal_name"),
            display_name=user_data.get("display_name"),
            is_mfa_registered=user_data.get("is_mfa_registered", False),
            mfa_methods=user_data.get("mfa_methods", []),
            primary_mfa_method=user_data.get("primary_method"),
            mfa_strength=mfa_strength,
            is_admin=user_data.get("is_admin", False),
            admin_roles=user_data.get("admin_roles", []),
            compliance_status=compliance_status,
            account_enabled=user_data.get("account_enabled", True),
            sign_in_activity=user_data.get("sign_in_activity"),
            user_type=user_data.get("user_type", "Member"),
            user_data=user_data.get("raw_user_data", {}),
        )

        # Set first registration date if MFA is registered
        if user.is_mfa_registered:
            user.first_mfa_registration = datetime.utcnow()
            user.last_mfa_update = datetime.utcnow()

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def _update_user_mfa_data(
        self,
        user: MFAUserModel,
        user_data: dict[str, Any],
        mfa_strength: MFAStrengthLevel,
        compliance_status: ComplianceStatus,
    ) -> None:
        """Update existing MFA user record.

        Args:
            user: Existing user model
            user_data: New user MFA data
            mfa_strength: Calculated MFA strength
            compliance_status: Calculated compliance status
        """
        # Track if MFA was just registered
        was_mfa_registered = user.is_mfa_registered

        user.display_name = user_data.get("display_name", user.display_name)
        user.is_mfa_registered = user_data.get("is_mfa_registered", False)
        user.mfa_methods = user_data.get("mfa_methods", [])
        user.primary_mfa_method = user_data.get("primary_method")
        user.mfa_strength = mfa_strength
        user.is_admin = user_data.get("is_admin", False)
        user.admin_roles = user_data.get("admin_roles", [])
        user.compliance_status = compliance_status
        user.account_enabled = user_data.get("account_enabled", True)
        user.sign_in_activity = user_data.get("sign_in_activity")
        user.user_type = user_data.get("user_type", user.user_type)
        user.user_data = user_data.get("raw_user_data", {})
        user.last_scan_at = datetime.utcnow()

        # Set first registration date if newly registered
        if user.is_mfa_registered and not was_mfa_registered:
            user.first_mfa_registration = datetime.utcnow()
            user.last_mfa_update = datetime.utcnow()
        elif user.is_mfa_registered:
            user.last_mfa_update = datetime.utcnow()

        await self.db.commit()

    async def _check_tenant_compliance(self, tenant_id: str) -> dict[str, Any]:
        """Check compliance status for a tenant.

        Args:
            tenant_id: Internal tenant UUID

        Returns:
            Compliance check results
        """
        result = await self.db.execute(
            select(MFAUserModel).where(
                and_(
                    MFAUserModel.tenant_id == tenant_id,
                    MFAUserModel.compliance_status == ComplianceStatus.NON_COMPLIANT,
                    MFAUserModel.compliance_exempt == False,
                    MFAUserModel.account_enabled,
                )
            )
        )
        non_compliant_users = result.scalars().all()

        # Check for admins without MFA
        admin_no_mfa_count = sum(1 for u in non_compliant_users if u.is_admin)

        return {
            "total_violations": len(non_compliant_users),
            "admin_violations": admin_no_mfa_count,
            "user_violations": len(non_compliant_users) - admin_no_mfa_count,
        }

    async def _create_compliance_alert(
        self,
        tenant_id: str,
        user_id: Any | None,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
    ) -> MFAComplianceAlertModel | None:
        """Create a compliance alert.

        Args:
            tenant_id: Internal tenant UUID
            user_id: User UUID (may be None if user not yet created)
            alert_type: Type of alert
            severity: Alert severity
            title: Alert title
            description: Alert description

        Returns:
            Created alert or None
        """
        try:
            # Check for existing unresolved alert of same type
            if user_id:
                result = await self.db.execute(
                    select(MFAComplianceAlertModel).where(
                        and_(
                            MFAComplianceAlertModel.user_id == user_id,
                            MFAComplianceAlertModel.alert_type == alert_type,
                            MFAComplianceAlertModel.is_resolved == False,
                        )
                    )
                )
                if result.scalar_one_or_none():
                    return None  # Alert already exists

            alert = MFAComplianceAlertModel(
                user_id=user_id,
                tenant_id=tenant_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                alert_metadata={
                    "created_by_scan": True,
                    "auto_generated": True,
                },
            )

            self.db.add(alert)
            await self.db.commit()
            await self.db.refresh(alert)

            return alert
        except Exception as e:
            logger.error(f"Error creating compliance alert: {e}")
            return None

    async def _create_enrollment_snapshot(self, tenant_id: str) -> MFAEnrollmentHistoryModel | None:
        """Create an enrollment snapshot for historical tracking.

        Args:
            tenant_id: Internal tenant UUID

        Returns:
            Created snapshot or None
        """
        try:
            # Get current counts
            total_users = await self._get_count(tenant_id)
            mfa_registered = await self._get_mfa_registered_count(tenant_id)
            total_admins = await self._get_admin_count(tenant_id)
            admins_with_mfa = await self._get_admin_with_mfa_count(tenant_id)

            # Get method counts
            fido2_count = await self._get_method_count(tenant_id, MFAStrengthLevel.STRONG)
            auth_app_count = await self._get_method_count(tenant_id, MFAStrengthLevel.MODERATE)
            sms_count = await self._get_method_count(tenant_id, MFAStrengthLevel.WEAK)

            # Get strength counts
            strong_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.STRONG)
            moderate_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.MODERATE)
            weak_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.WEAK)
            exempt_count = await self._get_exempt_count(tenant_id)

            # Calculate percentages
            mfa_coverage = (mfa_registered / total_users * 100) if total_users > 0 else 0
            admin_mfa_coverage = (admins_with_mfa / total_admins * 100) if total_admins > 0 else 0

            snapshot = MFAEnrollmentHistoryModel(
                tenant_id=tenant_id,
                snapshot_date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
                total_users=total_users,
                mfa_registered_users=mfa_registered,
                non_compliant_users=total_users - mfa_registered - exempt_count,
                total_admins=total_admins,
                admins_with_mfa=admins_with_mfa,
                admins_without_mfa=total_admins - admins_with_mfa,
                fido2_users=fido2_count,
                authenticator_app_users=auth_app_count,
                sms_users=sms_count,
                voice_users=0,  # Combined with SMS for simplicity
                strong_mfa_users=strong_count,
                moderate_mfa_users=moderate_count,
                weak_mfa_users=weak_count,
                exempt_users=exempt_count,
                mfa_coverage_percentage=round(float(mfa_coverage), 2),
                admin_mfa_coverage_percentage=round(float(admin_mfa_coverage), 2),
            )

            # Check for existing snapshot for today
            result = await self.db.execute(
                select(MFAEnrollmentHistoryModel).where(
                    and_(
                        MFAEnrollmentHistoryModel.tenant_id == tenant_id,
                        MFAEnrollmentHistoryModel.snapshot_date == snapshot.snapshot_date,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing snapshot
                existing.total_users = snapshot.total_users
                existing.mfa_registered_users = snapshot.mfa_registered_users
                existing.non_compliant_users = snapshot.non_compliant_users
                existing.total_admins = snapshot.total_admins
                existing.admins_with_mfa = snapshot.admins_with_mfa
                existing.admins_without_mfa = snapshot.admins_without_mfa
                existing.fido2_users = snapshot.fido2_users
                existing.authenticator_app_users = snapshot.authenticator_app_users
                existing.sms_users = snapshot.sms_users
                existing.strong_mfa_users = snapshot.strong_mfa_users
                existing.moderate_mfa_users = snapshot.moderate_mfa_users
                existing.weak_mfa_users = snapshot.weak_mfa_users
                existing.exempt_users = snapshot.exempt_users
                existing.mfa_coverage_percentage = snapshot.mfa_coverage_percentage
                existing.admin_mfa_coverage_percentage = snapshot.admin_mfa_coverage_percentage
            else:
                self.db.add(snapshot)

            await self.db.commit()

            return existing if existing else snapshot
        except Exception as e:
            logger.error(f"Error creating enrollment snapshot: {e}")
            return None

    # Count helper methods
    def _get_tenant_filter(self, model: Any, tenant_id: str | list[str]) -> Any:
        if tenant_id == "NONE":
            return model.tenant_id == "NONE_ASSIGNED"
        elif isinstance(tenant_id, list):
            return model.tenant_id.in_(tenant_id)
        return model.tenant_id == tenant_id

    async def _get_count(self, tenant_id: str | list[str]) -> int:
        """Get total user count."""
        result = await self.db.execute(
            select(func.count(MFAUserModel.id)).where(self._get_tenant_filter(MFAUserModel, tenant_id))
        )
        return result.scalar() or 0

    async def _get_mfa_registered_count(self, tenant_id: str | list[str]) -> int:
        """Get MFA registered user count."""
        result = await self.db.execute(
            select(func.count(MFAUserModel.id)).where(
                and_(
                    self._get_tenant_filter(MFAUserModel, tenant_id),
                    MFAUserModel.is_mfa_registered,
                )
            )
        )
        return result.scalar() or 0

    async def _get_admin_count(self, tenant_id: str | list[str]) -> int:
        """Get admin user count."""
        result = await self.db.execute(
            select(func.count(MFAUserModel.id)).where(
                and_(
                    self._get_tenant_filter(MFAUserModel, tenant_id),
                    MFAUserModel.is_admin,
                )
            )
        )
        return result.scalar() or 0

    async def _get_admin_with_mfa_count(self, tenant_id: str | list[str]) -> int:
        """Get admin users with MFA count."""
        result = await self.db.execute(
            select(func.count(MFAUserModel.id)).where(
                and_(
                    self._get_tenant_filter(MFAUserModel, tenant_id),
                    MFAUserModel.is_admin,
                    MFAUserModel.is_mfa_registered,
                )
            )
        )
        return result.scalar() or 0

    async def _get_strength_count(self, tenant_id: str | list[str], strength: MFAStrengthLevel) -> int:
        """Get users by MFA strength count."""
        result = await self.db.execute(
            select(func.count(MFAUserModel.id)).where(
                and_(
                    self._get_tenant_filter(MFAUserModel, tenant_id),
                    MFAUserModel.mfa_strength == strength,
                )
            )
        )
        return result.scalar() or 0

    async def _get_method_count(self, tenant_id: str | list[str], strength: MFAStrengthLevel) -> int:
        """Get users by method strength (approximation)."""
        return await self._get_strength_count(tenant_id, strength)

    async def _get_exempt_count(self, tenant_id: str | list[str]) -> int:
        """Get exempt user count."""
        result = await self.db.execute(
            select(func.count(MFAUserModel.id)).where(
                and_(
                    self._get_tenant_filter(MFAUserModel, tenant_id),
                    MFAUserModel.compliance_exempt,
                )
            )
        )
        return result.scalar() or 0

    async def _get_existing_user(self, tenant_id: str, user_id: str) -> MFAUserModel | None:
        """Get existing user from database.

        Args:
            tenant_id: Internal tenant UUID
            user_id: Microsoft Graph user ID

        Returns:
            Existing user or None
        """
        result = await self.db.execute(
            select(MFAUserModel).where(
                and_(
                    MFAUserModel.tenant_id == tenant_id,
                    MFAUserModel.user_id == user_id,
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
        result = await self.db.execute(select(TenantModel).where(TenantModel.id == tenant_id))
        return result.scalar_one_or_none()

    # Public API methods

    async def get_users(
        self,
        tenant_id: str | list[str] | None = None,
        is_mfa_registered: bool | None = None,
        is_admin: bool | None = None,
        compliance_status: ComplianceStatus | None = None,
        mfa_strength: MFAStrengthLevel | None = None,
        needs_attention: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get MFA users with filtering.

        Args:
            tenant_id: Filter by tenant
            is_mfa_registered: Filter by MFA registration status
            is_admin: Filter by admin status
            compliance_status: Filter by compliance status
            mfa_strength: Filter by MFA strength
            needs_attention: Filter by attention required
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with items and total count
        """
        query = select(MFAUserModel)

        if tenant_id:
            query = query.where(self._get_tenant_filter(MFAUserModel, tenant_id))
        if is_mfa_registered is not None:
            query = query.where(MFAUserModel.is_mfa_registered == is_mfa_registered)
        if is_admin is not None:
            query = query.where(MFAUserModel.is_admin == is_admin)
        if compliance_status:
            query = query.where(MFAUserModel.compliance_status == compliance_status)
        if mfa_strength:
            query = query.where(MFAUserModel.mfa_strength == mfa_strength)
        if needs_attention is not None:
            # needs_attention logic: not exempt, enabled, and (no MFA or admin with weak MFA)
            if needs_attention:
                query = query.where(
                    and_(
                        MFAUserModel.compliance_exempt == False,
                        MFAUserModel.account_enabled,
                        or_(
                            MFAUserModel.is_mfa_registered == False,
                            and_(
                                MFAUserModel.is_admin,
                                MFAUserModel.mfa_strength == MFAStrengthLevel.WEAK,
                            ),
                        ),
                    )
                )
            else:
                query = query.where(
                    or_(
                        MFAUserModel.compliance_exempt,
                        MFAUserModel.account_enabled == False,
                        and_(
                            MFAUserModel.is_mfa_registered,
                            or_(
                                MFAUserModel.is_admin == False,
                                MFAUserModel.mfa_strength != MFAStrengthLevel.WEAK,
                            ),
                        ),
                    )
                )

        # Get total count
        count_result = await self.db.execute(
            select(func.count(MFAUserModel.id)).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(desc(MFAUserModel.is_admin), MFAUserModel.user_principal_name)
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_users_without_mfa(
        self, tenant_id: str | list[str], include_exempt: bool = False, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Get users without MFA registration.

        Args:
            tenant_id: Tenant UUID
            include_exempt: Whether to include exempt users
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with items and total count
        """
        conditions = [
            self._get_tenant_filter(MFAUserModel, tenant_id),
            MFAUserModel.is_mfa_registered == False,
            MFAUserModel.account_enabled,
        ]

        if not include_exempt:
            conditions.append(MFAUserModel.compliance_exempt == False)

        query = select(MFAUserModel).where(and_(*conditions))

        # Get total count
        count_result = await self.db.execute(
            select(func.count(MFAUserModel.id)).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply ordering: admins first, then by name
        query = query.order_by(desc(MFAUserModel.is_admin), MFAUserModel.user_principal_name)
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_admins_without_mfa(self, tenant_id: str | list[str], limit: int = 100) -> list[MFAUserModel]:
        """Get admin users without MFA (critical findings).

        Args:
            tenant_id: Tenant UUID
            limit: Maximum results

        Returns:
            List of admin users without MFA
        """
        query = select(MFAUserModel).where(
            and_(
                self._get_tenant_filter(MFAUserModel, tenant_id),
                MFAUserModel.is_admin,
                MFAUserModel.is_mfa_registered == False,
                MFAUserModel.compliance_exempt == False,
                MFAUserModel.account_enabled,
            )
        )

        query = query.order_by(MFAUserModel.user_principal_name)
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_enrollment_summary(self, tenant_id: str | list[str]) -> dict[str, Any]:
        """Get MFA enrollment summary for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Enrollment summary data
        """
        # Get counts
        total_users = await self._get_count(tenant_id)
        mfa_registered = await self._get_mfa_registered_count(tenant_id)
        total_admins = await self._get_admin_count(tenant_id)
        admins_with_mfa = await self._get_admin_with_mfa_count(tenant_id)
        admins_without_mfa = total_admins - admins_with_mfa

        # Get method counts
        fido2_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.STRONG)
        auth_app_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.MODERATE)
        sms_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.WEAK)

        # Get strength counts
        strong_count = fido2_count
        moderate_count = auth_app_count
        weak_count = sms_count

        exempt_count = await self._get_exempt_count(tenant_id)
        non_compliant = total_users - mfa_registered - exempt_count

        # Calculate percentages
        mfa_coverage = (mfa_registered / total_users * 100) if total_users > 0 else 0
        admin_mfa_coverage = (admins_with_mfa / total_admins * 100) if total_admins > 0 else 0
        compliance_rate = (
            ((mfa_registered + exempt_count) / total_users * 100) if total_users > 0 else 0
        )

        return {
            "tenant_id": tenant_id,
            "snapshot_date": datetime.utcnow(),
            "total_users": total_users,
            "mfa_registered_users": mfa_registered,
            "non_compliant_users": non_compliant,
            "total_admins": total_admins,
            "admins_with_mfa": admins_with_mfa,
            "admins_without_mfa": admins_without_mfa,
            "fido2_users": fido2_count,
            "authenticator_app_users": auth_app_count,
            "sms_users": sms_count,
            "strong_mfa_users": strong_count,
            "moderate_mfa_users": moderate_count,
            "weak_mfa_users": weak_count,
            "exempt_users": exempt_count,
            "coverage_percentage": round(float(mfa_coverage), 2),
            "admin_coverage_percentage": round(float(admin_mfa_coverage), 2),
            "critical_findings_rate": round(float(compliance_rate), 2),
            "meets_admin_requirement": admin_mfa_coverage >= 100 if total_admins > 0 else True,
            "meets_user_target": mfa_coverage >= self.USER_MFA_TARGET_PERCENTAGE,
        }

    async def get_enrollment_trends(self, tenant_id: str, days: int = 30) -> dict[str, Any]:
        """Get MFA enrollment trends over time.

        Args:
            tenant_id: Tenant UUID
            days: Number of days to look back

        Returns:
            Trend data
        """
        since_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(MFAEnrollmentHistoryModel)
            .where(
                and_(
                    MFAEnrollmentHistoryModel.tenant_id == tenant_id,
                    MFAEnrollmentHistoryModel.snapshot_date >= since_date,
                )
            )
            .order_by(MFAEnrollmentHistoryModel.snapshot_date)
        )

        snapshots = result.scalars().all()

        trends = [
            {
                "date": s.snapshot_date,
                "total_users": s.total_users,
                "mfa_registered_users": s.mfa_registered_users,
                "mfa_coverage_percentage": s.mfa_coverage_percentage,
                "admin_mfa_coverage_percentage": s.admin_mfa_coverage_percentage,
            }
            for s in snapshots
        ]

        return {
            "tenant_id": tenant_id,
            "trends": trends,
            "period_days": days,
        }

    async def get_mfa_method_distribution(self, tenant_id: str) -> dict[str, Any]:
        """Get distribution of MFA methods used.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Method distribution data
        """
        result = await self.db.execute(
            select(MFAUserModel).where(
                and_(
                    MFAUserModel.tenant_id == tenant_id,
                    MFAUserModel.is_mfa_registered,
                )
            )
        )

        users = result.scalars().all()

        # Count methods
        method_counts: dict[str, int] = {}
        for user in users:
            for method in user.mfa_methods:
                method_counts[method] = method_counts.get(method, 0) + 1

        # Calculate percentages
        total_mfa_users = len(users)
        distribution = []
        for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
            distribution.append(
                {
                    "method_type": method,
                    "count": count,
                    "percentage": round(count / total_mfa_users * 100, 2)
                    if total_mfa_users > 0
                    else 0,
                }
            )

        return {
            "tenant_id": tenant_id,
            "total_mfa_users": total_mfa_users,
            "distribution": distribution,
        }

    async def get_mfa_strength_distribution(self, tenant_id: str) -> dict[str, Any]:
        """Get distribution of MFA strength levels.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Strength distribution data
        """
        total_users = await self._get_count(tenant_id)
        strong_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.STRONG)
        moderate_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.MODERATE)
        weak_count = await self._get_strength_count(tenant_id, MFAStrengthLevel.WEAK)
        no_mfa_count = total_users - strong_count - moderate_count - weak_count

        distribution = [
            {
                "strength_level": MFAStrengthLevel.STRONG,
                "count": strong_count,
                "percentage": round(float(strong_count / total_users * 100), 2) if total_users > 0 else 0,
            },
            {
                "strength_level": MFAStrengthLevel.MODERATE,
                "count": moderate_count,
                "percentage": round(float(moderate_count / total_users * 100), 2)
                if total_users > 0
                else 0,
            },
            {
                "strength_level": MFAStrengthLevel.WEAK,
                "count": weak_count,
                "percentage": round(float(weak_count / total_users * 100 if total_users > 0 else 0), 2),
            },
            {
                "strength_level": MFAStrengthLevel.NONE,
                "count": no_mfa_count,
                "percentage": round(float(no_mfa_count / total_users * 100), 2) if total_users > 0 else 0,
            },
        ]

        return {
            "tenant_id": tenant_id,
            "distribution": distribution,
            "strong_mfa_percentage": round(float(strong_count / total_users * 100), 2)
            if total_users > 0
            else 0,
            "moderate_mfa_percentage": round(float(moderate_count / total_users * 100), 2)
            if total_users > 0
            else 0,
            "weak_mfa_percentage": round(float(weak_count / total_users * 100), 2)
            if total_users > 0
            else 0,
            "no_mfa_percentage": round(float(no_mfa_count / total_users * 100), 2)
            if total_users > 0
            else 0,
        }

    async def set_user_exemption(
        self,
        user_id: str,
        exempt: bool,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> MFAUserModel | None:
        """Set or remove MFA exemption for a user.

        Args:
            user_id: User UUID
            exempt: Whether to exempt from MFA requirements
            reason: Exemption reason
            expires_at: Exemption expiration date

        Returns:
            Updated user or None
        """
        result = await self.db.execute(select(MFAUserModel).where(MFAUserModel.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return None

        user.compliance_exempt = exempt
        user.exemption_reason = reason if exempt else None
        user.exemption_expires_at = expires_at if exempt else None

        # Update compliance status
        if exempt:
            user.compliance_status = ComplianceStatus.EXEMPT
        elif user.is_mfa_registered:
            user.compliance_status = ComplianceStatus.COMPLIANT
        else:
            user.compliance_status = ComplianceStatus.NON_COMPLIANT

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def resolve_alert(
        self, alert_id: str, resolved_by: str
    ) -> MFAComplianceAlertModel | None:
        """Resolve a compliance alert.

        Args:
            alert_id: Alert UUID
            resolved_by: User resolving the alert

        Returns:
            Updated alert or None
        """
        result = await self.db.execute(
            select(MFAComplianceAlertModel).where(MFAComplianceAlertModel.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def get_alerts(
        self,
        tenant_id: str | None = None,
        resolved: bool | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get MFA compliance alerts.

        Args:
            tenant_id: Filter by tenant
            resolved: Filter by resolution status
            severity: Filter by severity
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dictionary with items and total count
        """
        query = select(MFAComplianceAlertModel)

        if tenant_id:
            query = query.where(MFAComplianceAlertModel.tenant_id == tenant_id)
        if resolved is not None:
            query = query.where(MFAComplianceAlertModel.is_resolved == resolved)
        if severity:
            query = query.where(MFAComplianceAlertModel.severity == severity)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Apply pagination and ordering
        query = query.order_by(desc(MFAComplianceAlertModel.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }
