"""Office 365 Audit Log Collector main entry point.

This module implements the collector that runs as a Kubernetes CronJob
to periodically fetch audit logs from Office 365 Management Activity API.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure src is in path
sys.path.insert(0, "/app")

import contextlib

from src.analytics.logins import LoginAnalyticsService
from src.collector.o365_feed import (
    CONTENT_TYPES,
    O365ManagementClient,
    RateLimitError,
    map_content_type_to_log_type,
)
from src.database import async_session_maker, init_db
from src.models.audit_log import (
    AuditLogModel,
    CollectionStateModel,
    LogType,
    utc_now,
)
from src.models.db import TenantModel
from src.services.encryption import encryption_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration from environment
COLLECTION_LOOKBACK_MINUTES = int(os.getenv("COLLECTION_LOOKBACK_MINUTES", "60"))
COLLECTION_INTERVAL_MINUTES = int(os.getenv("COLLECTION_INTERVAL_MINUTES", "5"))
COLLECTION_LATENCY_BUFFER_MINUTES = int(os.getenv("COLLECTION_LATENCY_BUFFER_MINUTES", "15"))
MAX_EVENTS_PER_BATCH = int(os.getenv("MAX_EVENTS_PER_BATCH", "1000"))


class CollectorError(Exception):
    """Base exception for collector errors."""

    pass


def ensure_timezone_aware(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware (UTC).

    Args:
        dt: Datetime that may or may not have timezone info.

    Returns:
        Timezone-aware datetime in UTC or None if input is None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TenantCollector:
    """Collector for a single tenant's audit logs."""

    def __init__(self, tenant: TenantModel, session: AsyncSession):
        """Initialize tenant collector.

        Args:
            tenant: Tenant database model.
            session: Database session.
        """
        self.tenant = tenant
        self.session = session
        self.client: O365ManagementClient | None = None

        # Decrypt client secret
        try:
            self.decrypted_secret = encryption_service.decrypt(tenant.client_secret)
        except Exception as e:
            logger.error(f"Failed to decrypt secret for tenant {tenant.id}: {e}")
            raise CollectorError(f"Failed to decrypt tenant secret: {e}") from e

    async def __aenter__(self) -> "TenantCollector":
        """Async context manager entry."""
        self.client = O365ManagementClient(
            tenant_id=self.tenant.tenant_id,
            client_id=self.tenant.client_id,
            client_secret=self.decrypted_secret,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # No cleanup needed for the client
        pass

    async def get_collection_state(self) -> CollectionStateModel:
        """Get or create collection state for tenant.

        Returns:
            CollectionStateModel instance.
        """
        result = await self.session.execute(
            select(CollectionStateModel).where(CollectionStateModel.tenant_id == self.tenant.id)
        )
        state = result.scalar_one_or_none()

        if state is None:
            state = CollectionStateModel(
                tenant_id=self.tenant.id,
                last_collection_time=None,
            )
            self.session.add(state)
            await self.session.flush()

        # Ensure all datetime fields are timezone-aware
        state.last_collection_time = ensure_timezone_aware(state.last_collection_time)
        state.last_success_at = ensure_timezone_aware(state.last_success_at)
        state.last_error_at = ensure_timezone_aware(state.last_error_at)
        state.updated_at = ensure_timezone_aware(state.updated_at)

        return state

    async def update_collection_state(
        self,
        state: CollectionStateModel,
        success: bool = True,
        error_message: str | None = None,
        events_count: int = 0,
        collection_end_time: datetime | None = None,
    ) -> None:
        """Update collection state after collection attempt.

        Args:
            state: Collection state to update.
            success: Whether collection was successful.
            error_message: Error message if failed.
            events_count: Number of events collected.
            collection_end_time: The end_time used for this collection run.
        """
        now = utc_now()

        if success:
            # Update last_collection_time to the end of the window we just processed
            if collection_end_time:
                state.last_collection_time = collection_end_time
            else:
                state.last_collection_time = now

            state.last_success_at = now
            state.total_logs_collected += events_count
            state.last_error = None
            state.last_error_at = None
        else:
            state.last_error = error_message
            state.last_error_at = now

        state.updated_at = now
        await self.session.flush()

    async def store_events(self, events: list[dict[str, Any]], content_type: str) -> int:
        """Store events in database.

        Args:
            events: List of audit log events.
            content_type: Office 365 content type.

        Returns:
            Number of events stored.
        """
        if not events:
            return 0

        log_type = LogType(map_content_type_to_log_type(content_type))
        stored_count = 0

        for event in events:
            try:
                # Extract O365 creation time if available
                o365_created_at = None
                if "CreationTime" in event:
                    with contextlib.suppress(ValueError, AttributeError):
                        o365_created_at = datetime.fromisoformat(
                            event["CreationTime"].replace("Z", "+00:00")
                        )

                audit_log = AuditLogModel(
                    tenant_id=self.tenant.id,
                    log_type=log_type,
                    raw_data=event,
                    processed=False,
                    o365_created_at=o365_created_at,
                )
                self.session.add(audit_log)
                stored_count += 1

                # Flush periodically to avoid memory issues
                if stored_count % 100 == 0:
                    await self.session.flush()

            except Exception as e:
                logger.warning(f"Failed to store event: {e}")
                continue

        await self.session.flush()
        logger.info(f"Stored {stored_count} events for tenant {self.tenant.id}")
        return stored_count

    async def collect_content_type(
        self, content_type: str, start_time: datetime, end_time: datetime
    ) -> int:
        """Collect logs for a single content type.

        Args:
            content_type: Office 365 content type.
            start_time: Start time for collection.
            end_time: End time for collection.

        Returns:
            Number of events collected.
        """
        if not self.client:
            raise CollectorError("Client not initialized")

        total_events = 0

        try:
            async for event_batch in self.client.collect_logs(
                content_type=content_type, start_time=start_time, end_time=end_time
            ):
                if event_batch:
                    stored = await self.store_events(event_batch, content_type)
                    total_events += stored

                    # Check if we've hit the batch limit
                    if total_events >= MAX_EVENTS_PER_BATCH:
                        logger.warning(
                            f"Reached max events limit ({MAX_EVENTS_PER_BATCH}) "
                            f"for {content_type}"
                        )
                        break

        except RateLimitError:
            logger.error(f"Rate limit hit for {content_type}, stopping collection")
            raise
        except Exception as e:
            logger.error(f"Error collecting {content_type}: {e}")
            # Continue with other content types

        return total_events

    async def collect_all(self) -> dict[str, Any]:
        """Collect all audit logs for tenant.

        Returns:
            Dictionary with collection results.
        """
        state = await self.get_collection_state()

        # Determine time range for collection
        # Shift end_time back by latency buffer to ensure logs are available in API
        now = utc_now()
        end_time = now - timedelta(minutes=COLLECTION_LATENCY_BUFFER_MINUTES)

        if state.last_collection_time:
            # Start from last collection time, but not more than 24 hours ago
            # (O365 API limit for historical data)
            last_time = ensure_timezone_aware(state.last_collection_time)

            # If our delayed end_time is still before last_time, nothing to do yet
            if end_time <= last_time:
                logger.info(
                    f"Last collection ({last_time}) is more recent than current "
                    f"delayed end_time ({end_time}). Skipping collection for tenant {self.tenant.id}."
                )
                return {
                    "tenant_id": self.tenant.id,
                    "tenant_name": self.tenant.name,
                    "total_events": 0,
                    "success": True,
                    "skipped": True
                }

            start_time = max(
                last_time, end_time - timedelta(hours=23)  # Leave buffer for API
            )
        else:
            # First time collection - go back configured lookback period
            start_time = end_time - timedelta(minutes=COLLECTION_LOOKBACK_MINUTES)

        logger.info(
            f"Collecting logs for tenant {self.tenant.id} ({self.tenant.name}) "
            f"from {start_time} to {end_time} (Current time: {now})"
        )

        # Ensure subscriptions are active
        try:
            subscribed = await self.client.ensure_subscriptions()
            logger.info(f"Active subscriptions: {subscribed}")
        except Exception as e:
            logger.error(f"Failed to ensure subscriptions: {e}")
            # Continue anyway - subscriptions might already exist

        # Collect from each content type
        results = {
            "tenant_id": self.tenant.id,
            "tenant_name": self.tenant.name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "content_types": {},
            "total_events": 0,
            "success": True,
            "error": None,
        }

        total_events = 0

        for content_type in CONTENT_TYPES:
            try:
                logger.info(f"Collecting {content_type} for tenant {self.tenant.id}")
                events = await self.collect_content_type(
                    content_type=content_type, start_time=start_time, end_time=end_time
                )
                results["content_types"][content_type] = events
                total_events += events

            except RateLimitError:
                results["success"] = False
                results["error"] = f"Rate limit exceeded for {content_type}"
                break
            except Exception as e:
                logger.error(f"Failed to collect {content_type}: {e}")
                results["content_types"][content_type] = 0

        results["total_events"] = total_events

        # Update collection state
        await self.update_collection_state(
            state=state,
            success=results["success"],
            error_message=results["error"],
            events_count=total_events,
            collection_end_time=end_time,
        )

        await self.session.commit()

        return results


async def get_active_tenants(session: AsyncSession) -> list[TenantModel]:
    """Get all active tenants.

    Args:
        session: Database session.

    Returns:
        List of active tenant models.
    """
    result = await session.execute(select(TenantModel).where(TenantModel.is_active))
    return list(result.scalars().all())


async def collect_logs() -> dict[str, Any]:
    """Main collection function.

    Collects audit logs for all active tenants.

    Returns:
        Dictionary with overall collection results.
    """
    logger.info("=" * 60)
    logger.info("Starting Office 365 Audit Log Collection")
    logger.info("=" * 60)

    results = {
        "started_at": utc_now().isoformat(),
        "tenants_processed": 0,
        "tenants_successful": 0,
        "tenants_failed": 0,
        "total_events": 0,
        "tenant_results": [],
    }

    async with async_session_maker() as session:
        try:
            # Get active tenants
            tenants = await get_active_tenants(session)
            logger.info(f"Found {len(tenants)} active tenants")

            if not tenants:
                logger.warning("No active tenants found, nothing to collect")
                results["completed_at"] = utc_now().isoformat()
                return results

            # Collect for each tenant
            for tenant in tenants:
                tenant_result = {
                    "tenant_id": tenant.id,
                    "tenant_name": tenant.name,
                    "success": False,
                    "events": 0,
                    "error": None,
                }

                try:
                    async with TenantCollector(tenant, session) as collector:
                        collection_result = await collector.collect_all()

                        tenant_result["success"] = collection_result["success"]
                        tenant_result["events"] = collection_result["total_events"]
                        tenant_result["error"] = collection_result.get("error")

                        results["tenants_successful"] += 1
                        results["total_events"] += collection_result["total_events"]

                        logger.info(
                            f"Successfully collected {collection_result['total_events']} "
                            f"events for tenant {tenant.name}"
                        )

                        # Auto-process the collected logs right away
                        try:
                            logger.info(f"Processing collected logs for tenant {tenant.name}...")
                            analytics_service = LoginAnalyticsService(session)
                            processed_count = await analytics_service.process_audit_log_signins(
                                tenant_id=tenant.id,
                                limit=1000  # Process up to 1000 at a time
                            )
                            logger.info(f"Successfully processed {processed_count} signin logs into analytics for tenant {tenant.name}")

                            # Also mark other logs as processed
                            general_processed = await analytics_service.process_audit_log_general(
                                tenant_id=tenant.id,
                                limit=1000
                            )
                            if general_processed > 0:
                                logger.info(f"Successfully processed {general_processed} general audit logs for tenant {tenant.name}")
                        except Exception as process_err:
                            logger.error(f"Failed to process logs for tenant {tenant.name}: {process_err}")



                except Exception as e:
                    logger.error(f"Failed to collect for tenant {tenant.name}: {e}")
                    tenant_result["error"] = str(e)
                    results["tenants_failed"] += 1

                results["tenant_results"].append(tenant_result)
                results["tenants_processed"] += 1

            await session.commit()

        except Exception:
            logger.exception("Unexpected error during collection")
            await session.rollback()
            raise

    results["completed_at"] = utc_now().isoformat()

    logger.info("=" * 60)
    logger.info("Collection complete:")
    logger.info(f"  Tenants processed: {results['tenants_processed']}")
    logger.info(f"  Successful: {results['tenants_successful']}")
    logger.info(f"  Failed: {results['tenants_failed']}")
    logger.info(f"  Total events: {results['total_events']}")
    logger.info("=" * 60)

    return results


async def main() -> int:
    """Main entry point for collector.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        # Initialize database tables
        logger.info("Initializing database...")
        await init_db()

        # Run collection
        results = await collect_logs()

        # Determine exit code
        if results["tenants_failed"] > 0:
            logger.warning("Some tenants failed collection")
            return 1

        return 0

    except Exception as e:
        logger.exception(f"Fatal error in collector: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
