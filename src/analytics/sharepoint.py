"""SharePoint analytics service for analyzing sharing events."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, func, select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLogModel, LogType
from src.models.sharepoint import SharePointSharingModel

logger = logging.getLogger(__name__)


# Operations that represent sharing link creation or updates
SHARING_LINK_OPERATIONS = {
    "AnonymousLinkCreated",
    "AnonymousLinkUpdated",
    "SecureLinkCreated",
    "AddedToSecureLink",
    "SharingLinkCreated",
    "SharingInheritanceBroken",
    "CompanyLinkCreated",
    "AddedToCompanyLink",
    "SharingInvitationCreated",
    "FileShared",
    "FolderShared",
    "Shared",
    "SharingSet",
}

# Operations that revoke sharing
SHARING_REVOKED_OPERATIONS = {
    "SharingRevoked",
    "AnonymousLinkRemoved",
    "SecureLinkRemoved",
    "CompanyLinkRemoved",
    "SharingInheritanceRestored",
}


class SharePointAnalyticsService:
    """Service for processing and analyzing SharePoint events."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the SharePoint analytics service.

        Args:
            db: Database session
        """
        self.db = db

    async def process_audit_log_sharepoint(self, tenant_id: str, limit: int = 100) -> int:
        """
        Process unprocessed SharePoint audit logs and detect sharing events.

        Args:
            tenant_id: Tenant ID to process
            limit: Maximum number of logs to process

        Returns:
            Number of logs processed
        """
        # Get unprocessed SharePoint logs
        result = await self.db.execute(
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.log_type == LogType.SHAREPOINT,
                    AuditLogModel.processed.is_(False),
                )
            )
            .order_by(AuditLogModel.o365_created_at)
            .limit(limit)
        )

        logs = result.scalars().all()
        processed_count = 0

        for log in logs:
            try:
                raw_data = log.raw_data
                if not isinstance(raw_data, dict):
                    log.processed = True
                    continue

                operation = raw_data.get("Operation", "")
                
                # Identify if this is a sharing event
                is_sharing_creation = operation in SHARING_LINK_OPERATIONS
                is_sharing_revocation = operation in SHARING_REVOKED_OPERATIONS
                
                if not is_sharing_creation and not is_sharing_revocation:
                    # Not a sharing event, just mark processed
                    log.processed = True
                    processed_count += 1
                    continue

                # Extract sharing details
                site_url = raw_data.get("SiteUrl")
                file_name = raw_data.get("SourceFileName")
                file_path = raw_data.get("SourceRelativeUrl")
                user_email = raw_data.get("UserId")
                
                event_time_str = raw_data.get("CreationTime")
                if event_time_str:
                    try:
                        # Normalize ISO format and ensure UTC awareness
                        event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
                        if event_time.tzinfo is None:
                            event_time = event_time.replace(tzinfo=UTC)
                    except (ValueError, AttributeError):
                        event_time = log.o365_created_at or datetime.now(UTC)
                else:
                    event_time = log.o365_created_at or datetime.now(UTC)
                
                # Double check event_time for awareness
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=UTC)

                if is_sharing_creation:
                    # Determine sharing type
                    sharing_type = "Secure"
                    if "Anonymous" in operation:
                        sharing_type = "Anonymous"
                    elif "Company" in operation:
                        sharing_type = "Organization"
                    elif "Invitation" in operation or "Shared" in operation:
                        sharing_type = "DirectInvite"
                    share_link_url = raw_data.get("SharingLinkUrl")
                    target_user = raw_data.get("TargetUserOrGroup")

                    # Create sharing record
                    sharing_record = SharePointSharingModel(
                        tenant_id=tenant_id,
                        audit_log_id=log.id,
                        event_time=event_time,
                        operation=operation,
                        site_url=site_url,
                        file_name=file_name,
                        file_path=file_path,
                        user_email=user_email,
                        sharing_type=sharing_type,
                        share_link_url=share_link_url,
                        target_user=target_user,
                        is_active=True,
                    )
                    self.db.add(sharing_record)
                    logger.info(f"Created SharePoint sharing record for {file_name} ({sharing_type})")

                elif is_sharing_revocation:
                    # Update existing records for this file to inactive
                    if file_path:
                        await self.db.execute(
                            update(SharePointSharingModel)
                            .where(
                                and_(
                                    SharePointSharingModel.tenant_id == tenant_id,
                                    SharePointSharingModel.file_path == file_path,
                                    SharePointSharingModel.is_active.is_(True),
                                )
                            )
                            .values(is_active=False, revoked_at=event_time)
                        )
                    logger.info(f"Revoked SharePoint sharing for {file_name}")

                log.processed = True
                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing SharePoint log {log.id}: {e}")
                log.processed = True  # Avoid infinite loops

        await self.db.commit()
        return processed_count

    def _apply_tenant_filter(self, query: Any, model_class: Any, tenant_id: str | list[str] | None) -> Any:
        if tenant_id is None:
            return query
        if tenant_id == "NONE":
            return query.where(model_class.tenant_id == "NONE_ASSIGNED")
        if isinstance(tenant_id, list):
            return query.where(model_class.tenant_id.in_(tenant_id))
        return query.where(model_class.tenant_id == tenant_id)

    async def get_summary_metrics(self, tenant_id: str | None) -> dict[str, Any]:
        """Get summary metrics for SharePoint sharing."""
        print(f"DEBUG get_summary_metrics called with tenant_id: {tenant_id}")
        metrics: dict[str, Any] = {
            "active_links_count": 0,
            "by_type": {"Anonymous": 0, "Secure": 0, "Organization": 0, "DirectInvite": 0},
            "top_sharers": {},
            "by_site": {},
            "recent_activity": []
        }
        
        # Total active links
        query = select(func.count(SharePointSharingModel.id)).where(
            SharePointSharingModel.is_active.is_(True)
        )
        query = self._apply_tenant_filter(query, SharePointSharingModel, tenant_id)
        result = await self.db.execute(query)
        metrics["active_links_count"] = result.scalar() or 0
        
        # Anonymous vs Secure vs others
        query = select(SharePointSharingModel.sharing_type, func.count(SharePointSharingModel.id)).where(
            SharePointSharingModel.is_active.is_(True)
        )
        query = self._apply_tenant_filter(query, SharePointSharingModel, tenant_id)
        query = query.group_by(SharePointSharingModel.sharing_type)
        result = await self.db.execute(query)
        for row in result.all():
            if row[0] in metrics["by_type"]:
                metrics["by_type"][row[0]] = row[1]
            elif row[0]:
                metrics["by_type"][row[0]] = row[1]
        
        # Most active sharers (top 5)
        query = select(SharePointSharingModel.user_email, func.count(SharePointSharingModel.id))
        query = self._apply_tenant_filter(query, SharePointSharingModel, tenant_id)
        query = (
            query.group_by(SharePointSharingModel.user_email)
            .order_by(desc(func.count(SharePointSharingModel.id)))
            .limit(5)
        )
        result = await self.db.execute(query)
        metrics["top_sharers"] = {row[0]: row[1] for row in result.all() if row[0]}
        
        # Breakdown by Site (Top 5)
        query = select(SharePointSharingModel.site_url, func.count(SharePointSharingModel.id)).where(
            SharePointSharingModel.is_active.is_(True)
        )
        query = self._apply_tenant_filter(query, SharePointSharingModel, tenant_id)
        query = (
            query.group_by(SharePointSharingModel.site_url)
            .order_by(desc(func.count(SharePointSharingModel.id)))
            .limit(5)
        )
        result = await self.db.execute(query)
        metrics["by_site"] = {row[0]: row[1] for row in result.all() if row[0]}

        # Recent shared files (for a quick activity feed)
        query = select(SharePointSharingModel)
        query = self._apply_tenant_filter(query, SharePointSharingModel, tenant_id)
        query = query.order_by(desc(SharePointSharingModel.event_time)).limit(10)
        result = await self.db.execute(query)
        recent_logs = result.scalars().all()
        metrics["recent_activity"] = [
            {
                "file_name": log.file_name,
                "operation": log.operation,
                "user": log.user_email,
                "time": log.event_time.isoformat()
            }
            for log in recent_logs
        ]
        
        return metrics

    async def get_active_sharing_links(
        self, tenant_id: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[SharePointSharingModel]:
        """Get current active sharing links."""
        query = select(SharePointSharingModel).where(SharePointSharingModel.is_active.is_(True))
        query = self._apply_tenant_filter(query, SharePointSharingModel, tenant_id)
        query = query.order_by(desc(SharePointSharingModel.event_time)).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
