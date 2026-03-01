"""Alert streaming service for real-time WebSocket updates."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timezone, timedelta
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_

from src.models.alerts import (
    AlertHistoryModel, 
    SeverityLevel, 
    EventType,
    SEVERITY_COLORS,
    SEVERITY_EMOJIS,
    EVENT_TYPE_NAMES,
)

logger = logging.getLogger(__name__)


class AlertStatus(str, Enum):
    """Status of an alert in the stream."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


@dataclass
class StreamAlert:
    """Alert data structure for streaming."""
    id: str
    severity: SeverityLevel
    event_type: str
    title: str
    message: str
    user_email: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: AlertStatus = AlertStatus.NEW
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "event_type": self.event_type,
            "title": self.title,
            "message": self.message,
            "user_email": self.user_email,
            "tenant_id": self.tenant_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "severity_color": SEVERITY_COLORS.get(self.severity),
            "severity_emoji": SEVERITY_EMOJIS.get(self.severity),
            "event_type_name": EVENT_TYPE_NAMES.get(self.event_type, self.event_type),
        }


class AlertStreamService:
    """Service for managing alert streaming."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the alert stream service.
        
        Args:
            db: Database session
        """
        self.db = db
        self._alert_queue: asyncio.Queue[StreamAlert] = asyncio.Queue()
        self._recent_alerts: List[StreamAlert] = []
        self._max_recent = 100
        self._callbacks: List[Callable[[StreamAlert], None]] = []
    
    async def get_recent_alerts(
        self,
        limit: int = 50,
        severity: Optional[List[SeverityLevel]] = None,
        event_types: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> List[StreamAlert]:
        """Get recent alerts from the database.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity levels
            event_types: Filter by event types
            tenant_id: Filter by tenant ID
            
        Returns:
            List of recent alerts
        """
        query = select(AlertHistoryModel).order_by(desc(AlertHistoryModel.sent_at)).limit(limit)
        
        filters = []
        if severity:
            filters.append(AlertHistoryModel.severity.in_(severity))
        if event_types:
            filters.append(AlertHistoryModel.event_type.in_(event_types))
        if tenant_id:
            filters.append(AlertHistoryModel.tenant_id == tenant_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        result = await self.db.execute(query)
        alerts = result.scalars().all()
        
        return [
            StreamAlert(
                id=str(alert.id),
                severity=alert.severity,
                event_type=alert.event_type,
                title=alert.title,
                message=alert.message,
                user_email=alert.user_email,
                tenant_id=alert.tenant_id,
                metadata=alert.alert_metadata,
                timestamp=alert.sent_at,
            )
            for alert in alerts
        ]
    
    async def publish_alert(self, alert: StreamAlert) -> None:
        """Publish a new alert to the stream.
        
        Args:
            alert: Alert to publish
        """
        # Add to queue
        await self._alert_queue.put(alert)
        
        # Add to recent alerts
        self._recent_alerts.insert(0, alert)
        if len(self._recent_alerts) > self._max_recent:
            self._recent_alerts.pop()
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        logger.info(f"Alert published: {alert.id} - {alert.title}")
    
    def register_callback(self, callback: Callable[[StreamAlert], None]) -> None:
        """Register a callback for new alerts.
        
        Args:
            callback: Function to call when new alert arrives
        """
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[StreamAlert], None]) -> None:
        """Unregister a callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def get_alert_by_id(self, alert_id: str) -> Optional[StreamAlert]:
        """Get a specific alert by ID.
        
        Args:
            alert_id: Alert UUID
            
        Returns:
            Alert if found, None otherwise
        """
        # Check recent alerts first
        for alert in self._recent_alerts:
            if alert.id == alert_id:
                return alert
        
        # Query database
        from uuid import UUID
        try:
            uuid_id = UUID(alert_id)
        except ValueError:
            return None
        
        query = select(AlertHistoryModel).where(AlertHistoryModel.id == uuid_id)
        result = await self.db.execute(query)
        db_alert = result.scalar_one_or_none()
        
        if not db_alert:
            return None
        
        return StreamAlert(
            id=str(db_alert.id),
            severity=db_alert.severity,
            event_type=db_alert.event_type,
            title=db_alert.title,
            message=db_alert.message,
            user_email=db_alert.user_email,
            tenant_id=db_alert.tenant_id,
            metadata=db_alert.alert_metadata,
            timestamp=db_alert.sent_at,
        )
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> bool:
        """Mark an alert as acknowledged.
        
        Args:
            alert_id: Alert UUID
            acknowledged_by: User/client who acknowledged
            
        Returns:
            True if successful
        """
        alert = await self.get_alert_by_id(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now(timezone.utc)
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    async def dismiss_alert(self, alert_id: str, dismissed_by: str) -> bool:
        """Mark an alert as dismissed.
        
        Args:
            alert_id: Alert UUID
            dismissed_by: User/client who dismissed
            
        Returns:
            True if successful
        """
        alert = await self.get_alert_by_id(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.DISMISSED
        alert.acknowledged_by = dismissed_by
        alert.acknowledged_at = datetime.now(timezone.utc)
        
        logger.info(f"Alert {alert_id} dismissed by {dismissed_by}")
        return True


class AlertStreamManager:
    """Manages client subscriptions and alert distribution."""
    
    def __init__(
        self,
        stream_service: AlertStreamService,
        connection_manager: Any  # ConnectionManager from websocket.py
    ):
        """Initialize the stream manager.
        
        Args:
            stream_service: Alert stream service
            connection_manager: WebSocket connection manager
        """
        self.stream_service = stream_service
        self.connection_manager = connection_manager
        self._client_filters: Dict[str, Dict] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the alert distribution loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._distribution_loop())
        logger.info("Alert stream manager started")
    
    async def stop(self) -> None:
        """Stop the alert distribution loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Alert stream manager stopped")
    
    async def subscribe_client(self, client_id: str, filters: Dict) -> None:
        """Subscribe a client to the alert stream.
        
        Args:
            client_id: Client identifier
            filters: Filter configuration
        """
        self._client_filters[client_id] = filters
        
        # Send recent alerts as initial batch
        recent = await self.stream_service.get_recent_alerts(
            limit=20,
            severity=filters.get("severity"),
            event_types=filters.get("event_types"),
            tenant_id=filters.get("tenant_id"),
        )
        
        # Send initial batch
        if recent:
            await self.connection_manager.send_personal_message({
                "type": "initial_alerts",
                "alerts": [alert.to_dict() for alert in recent],
            }, client_id)
    
    async def unsubscribe_client(self, client_id: str) -> None:
        """Unsubscribe a client from the alert stream.
        
        Args:
            client_id: Client identifier
        """
        self._client_filters.pop(client_id, None)
    
    async def update_subscription(self, client_id: str, filters: Dict) -> None:
        """Update a client's subscription filters.
        
        Args:
            client_id: Client identifier
            filters: New filter configuration
        """
        self._client_filters[client_id] = filters
        
        # Send updated filter confirmation
        await self.connection_manager.send_personal_message({
            "type": "filters_updated",
            "filters": filters,
        }, client_id)
    
    async def acknowledge_alert(self, alert_id: str, client_id: str) -> bool:
        """Acknowledge an alert.
        
        Args:
            alert_id: Alert UUID
            client_id: Client who acknowledged
            
        Returns:
            True if successful
        """
        success = await self.stream_service.acknowledge_alert(alert_id, client_id)
        
        if success:
            # Broadcast to all clients
            await self.connection_manager.broadcast({
                "type": "alert_acknowledged",
                "alert_id": alert_id,
                "acknowledged_by": client_id,
            })
        
        return success
    
    async def dismiss_alert(self, alert_id: str, client_id: str) -> bool:
        """Dismiss an alert.
        
        Args:
            alert_id: Alert UUID
            client_id: Client who dismissed
            
        Returns:
            True if successful
        """
        success = await self.stream_service.dismiss_alert(alert_id, client_id)
        
        if success:
            # Broadcast to all clients
            await self.connection_manager.broadcast({
                "type": "alert_dismissed",
                "alert_id": alert_id,
                "dismissed_by": client_id,
            })
        
        return success
    
    async def _distribution_loop(self) -> None:
        """Main loop for distributing alerts to clients."""
        while self._running:
            try:
                # Wait for new alerts from the queue
                # This is a simplified version - in production, you'd integrate
                # with your actual alert generation pipeline
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in distribution loop: {e}")
    
    async def broadcast_alert(self, alert: StreamAlert) -> int:
        """Broadcast an alert to all connected clients.
        
        Args:
            alert: Alert to broadcast
            
        Returns:
            Number of clients the alert was sent to
        """
        message = {
            "type": "new_alert",
            "alert": alert.to_dict(),
        }
        
        return await self.connection_manager.broadcast(message)
