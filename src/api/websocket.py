"""WebSocket endpoints for real-time alert streaming."""

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.alert_stream import AlertStreamManager, AlertStreamService

logger = logging.getLogger(__name__)
router = APIRouter()

# Global connection manager for WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections for alert streaming."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}
        self.connection_filters: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        filters: dict | None = None
    ) -> None:
        """Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            client_id: Unique client identifier
            filters: Optional filter configuration
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
            self.connection_filters[client_id] = filters or {}
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")

    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection.
        
        Args:
            client_id: Client identifier to disconnect
        """
        async with self._lock:
            self.active_connections.pop(client_id, None)
            self.connection_filters.pop(client_id, None)
        logger.info(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, client_id: str) -> bool:
        """Send a message to a specific client.
        
        Args:
            message: Message to send
            client_id: Target client ID
            
        Returns:
            True if sent successfully, False otherwise
        """
        if client_id not in self.active_connections:
            return False

        try:
            await self.active_connections[client_id].send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {client_id}: {e}")
            return False

    async def broadcast(self, message: dict) -> int:
        """Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of successful sends
        """
        sent_count = 0
        disconnected = []

        for client_id, connection in list(self.active_connections.items()):
            try:
                # Apply filters if configured
                filters = self.connection_filters.get(client_id, {})
                if self._should_send_to_client(message, filters):
                    await connection.send_json(message)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

        return sent_count

    def _should_send_to_client(self, message: dict, filters: dict) -> bool:
        """Check if message should be sent based on client filters.
        
        Args:
            message: Alert message
            filters: Client filter configuration
            
        Returns:
            True if message passes filters
        """
        if not filters:
            return True

        # Filter by severity
        severity_filter = filters.get("severity")
        if severity_filter and message.get("severity") not in severity_filter:
            return False

        # Filter by event type
        event_type_filter = filters.get("event_types")
        if event_type_filter and message.get("event_type") not in event_type_filter:
            return False

        # Filter by tenant
        tenant_filter = filters.get("tenant_id")
        if tenant_filter and message.get("tenant_id") != tenant_filter:
            return False

        return True

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)

    def get_client_ids(self) -> list[str]:
        """Get list of all connected client IDs."""
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/alerts")
async def alert_websocket(
    websocket: WebSocket,
    severity: str | None = Query(None, description="Filter by severity (comma-separated)"),
    event_types: str | None = Query(None, description="Filter by event types (comma-separated)"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> None:
    """WebSocket endpoint for real-time alert streaming.
    
    Supports filtering by:
    - severity: LOW,MEDIUM,HIGH,CRITICAL
    - event_types: impossible_travel,new_country,brute_force,etc
    - tenant_id: specific tenant UUID
    
    Query Parameters:
        severity: Comma-separated severity levels
        event_types: Comma-separated event types
        tenant_id: Tenant UUID to filter by
    """
    # Generate client ID
    client_id = f"{websocket.client.host}:{websocket.client.port}"

    # Parse filters
    filters = {}
    if severity:
        filters["severity"] = [s.strip().upper() for s in severity.split(",")]
    if event_types:
        filters["event_types"] = [et.strip() for et in event_types.split(",")]
    if tenant_id:
        filters["tenant_id"] = tenant_id

    # Connect to manager
    await manager.connect(websocket, client_id, filters)

    # Get alert stream service
    stream_service = AlertStreamService(db)
    stream_manager = AlertStreamManager(stream_service, manager)

    try:
        # Subscribe to alert stream
        await stream_manager.subscribe_client(client_id, filters)

        # Send initial connection success message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "filters": filters,
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_client_message(data, client_id, stream_manager)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        await stream_manager.unsubscribe_client(client_id)
        await manager.disconnect(client_id)


async def handle_client_message(
    data: dict,
    client_id: str,
    stream_manager: AlertStreamManager
) -> None:
    """Handle incoming messages from WebSocket clients.
    
    Args:
        data: Received message data
        client_id: Client identifier
        stream_manager: Alert stream manager instance
    """
    msg_type = data.get("type")

    if msg_type == "ping":
        # Simple ping/pong for keepalive
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now(UTC).isoformat(),
        }, client_id)

    elif msg_type == "acknowledge":
        # Acknowledge an alert
        alert_id = data.get("alert_id")
        if alert_id:
            await stream_manager.acknowledge_alert(alert_id, client_id)
            await manager.send_personal_message({
                "type": "acknowledged",
                "alert_id": alert_id,
            }, client_id)

    elif msg_type == "dismiss":
        # Dismiss an alert
        alert_id = data.get("alert_id")
        if alert_id:
            await stream_manager.dismiss_alert(alert_id, client_id)
            await manager.send_personal_message({
                "type": "dismissed",
                "alert_id": alert_id,
            }, client_id)

    elif msg_type == "subscribe":
        # Update subscription filters
        filters = data.get("filters", {})
        await stream_manager.update_subscription(client_id, filters)
        await manager.send_personal_message({
            "type": "subscribed",
            "filters": filters,
        }, client_id)

    elif msg_type == "unsubscribe":
        # Remove all filters (receive all alerts)
        await stream_manager.update_subscription(client_id, {})
        await manager.send_personal_message({
            "type": "unsubscribed",
        }, client_id)

    elif msg_type == "get_stats":
        # Get connection statistics
        stats = {
            "type": "stats",
            "connected_clients": manager.get_connection_count(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await manager.send_personal_message(stats, client_id)

    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        }, client_id)


@router.get("/ws/stats")
async def get_websocket_stats() -> dict:
    """Get WebSocket connection statistics.
    
    Returns:
        Connection statistics
    """
    return {
        "connected_clients": manager.get_connection_count(),
        "client_ids": manager.get_client_ids(),
        "timestamp": datetime.now(UTC).isoformat(),
    }
