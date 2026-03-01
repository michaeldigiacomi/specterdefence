"""Tests for WebSocket endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import FastAPI, WebSocket

from src.api.websocket import (
    ConnectionManager,
    alert_websocket,
    get_websocket_stats,
    handle_client_message,
)
from src.services.alert_stream import (
    AlertStreamService,
    AlertStreamManager,
    StreamAlert,
    AlertStatus,
    SeverityLevel,
)


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock(spec=WebSocket)
        ws.client.host = "127.0.0.1"
        ws.client.port = 12345
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a new client."""
        client_id = "test_client_1"
        filters = {"severity": ["HIGH", "CRITICAL"]}
        
        await manager.connect(mock_websocket, client_id, filters)
        
        mock_websocket.accept.assert_called_once()
        assert client_id in manager.active_connections
        assert manager.connection_filters[client_id] == filters

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a client."""
        client_id = "test_client_1"
        await manager.connect(mock_websocket, client_id, {})
        
        await manager.disconnect(client_id)
        
        assert client_id not in manager.active_connections
        assert client_id not in manager.connection_filters

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Test sending a message to a specific client."""
        client_id = "test_client_1"
        await manager.connect(mock_websocket, client_id, {})
        
        message = {"type": "test", "data": "hello"}
        result = await manager.send_personal_message(message, client_id)
        
        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_to_disconnected_client(self, manager):
        """Test sending message to disconnected client returns False."""
        result = await manager.send_personal_message({"type": "test"}, "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all connected clients."""
        # Create multiple mock websockets
        ws1 = AsyncMock(spec=WebSocket)
        ws1.client.host = "127.0.0.1"
        ws1.client.port = 12345
        
        ws2 = AsyncMock(spec=WebSocket)
        ws2.client.host = "127.0.0.1"
        ws2.client.port = 12346
        
        await manager.connect(ws1, "client_1", {})
        await manager.connect(ws2, "client_2", {})
        
        message = {"type": "broadcast", "data": "hello all"}
        sent_count = await manager.broadcast(message)
        
        assert sent_count == 2
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_with_filters(self, manager):
        """Test broadcasting respects client filters."""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.client.host = "127.0.0.1"
        ws1.client.port = 12345
        
        ws2 = AsyncMock(spec=WebSocket)
        ws2.client.host = "127.0.0.1"
        ws2.client.port = 12346
        
        # Client 1 only wants CRITICAL alerts
        await manager.connect(ws1, "client_1", {"severity": ["CRITICAL"]})
        # Client 2 wants all alerts
        await manager.connect(ws2, "client_2", {})
        
        # Send MEDIUM severity alert - should only go to client_2
        message = {"severity": "MEDIUM", "type": "new_alert"}
        sent_count = await manager.broadcast(message)
        
        assert sent_count == 1
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_with_failed_client(self, manager):
        """Test broadcast handles client errors gracefully."""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.client.host = "127.0.0.1"
        ws1.client.port = 12345
        ws1.send_json.side_effect = Exception("Connection closed")
        
        ws2 = AsyncMock(spec=WebSocket)
        ws2.client.host = "127.0.0.1"
        ws2.client.port = 12346
        
        await manager.connect(ws1, "client_1", {})
        await manager.connect(ws2, "client_2", {})
        
        message = {"type": "test"}
        sent_count = await manager.broadcast(message)
        
        # Only client_2 should receive, client_1 should be disconnected
        assert sent_count == 1
        assert "client_1" not in manager.active_connections

    def test_get_connection_count(self, manager, mock_websocket):
        """Test getting connection count."""
        assert manager.get_connection_count() == 0
        
        # Use run_coroutine_threadsafe or similar for sync test
        import asyncio
        asyncio.run(manager.connect(mock_websocket, "client_1", {}))
        assert manager.get_connection_count() == 1

    def test_should_send_to_client_no_filters(self, manager):
        """Test that messages pass when no filters are set."""
        message = {"severity": "HIGH", "event_type": "test"}
        assert manager._should_send_to_client(message, {}) is True

    def test_should_send_to_client_severity_filter_match(self, manager):
        """Test severity filter matching."""
        filters = {"severity": ["HIGH", "CRITICAL"]}
        message = {"severity": "HIGH", "event_type": "test"}
        assert manager._should_send_to_client(message, filters) is True

    def test_should_send_to_client_severity_filter_no_match(self, manager):
        """Test severity filter not matching."""
        filters = {"severity": ["CRITICAL"]}
        message = {"severity": "LOW", "event_type": "test"}
        assert manager._should_send_to_client(message, filters) is False

    def test_should_send_to_client_event_type_filter(self, manager):
        """Test event type filter."""
        filters = {"event_types": ["brute_force", "new_country"]}
        
        # Matching event type
        message1 = {"severity": "HIGH", "event_type": "brute_force"}
        assert manager._should_send_to_client(message1, filters) is True
        
        # Non-matching event type
        message2 = {"severity": "HIGH", "event_type": "admin_action"}
        assert manager._should_send_to_client(message2, filters) is False

    def test_should_send_to_client_tenant_filter(self, manager):
        """Test tenant filter."""
        filters = {"tenant_id": "tenant-123"}
        
        # Matching tenant
        message1 = {"severity": "HIGH", "tenant_id": "tenant-123"}
        assert manager._should_send_to_client(message1, filters) is True
        
        # Non-matching tenant
        message2 = {"severity": "HIGH", "tenant_id": "tenant-456"}
        assert manager._should_send_to_client(message2, filters) is False


class TestWebSocketStats:
    """Tests for WebSocket statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_websocket_stats(self):
        """Test getting WebSocket statistics."""
        # Mock the global manager
        with patch('src.api.websocket.manager') as mock_manager:
            mock_manager.get_connection_count.return_value = 5
            mock_manager.get_client_ids.return_value = ["c1", "c2", "c3", "c4", "c5"]
            
            stats = await get_websocket_stats()
            
            assert stats["connected_clients"] == 5
            assert stats["client_ids"] == ["c1", "c2", "c3", "c4", "c5"]
            assert "timestamp" in stats


class TestClientMessageHandling:
    """Tests for client message handling."""

    @pytest.fixture
    def mock_stream_manager(self):
        """Create a mock AlertStreamManager."""
        manager = AsyncMock(spec=AlertStreamManager)
        return manager

    @pytest.mark.asyncio
    async def test_handle_ping_message(self, mock_stream_manager):
        """Test handling ping message."""
        with patch('src.api.websocket.manager') as mock_conn_manager:
            mock_conn_manager.send_personal_message = AsyncMock(return_value=True)
            
            data = {"type": "ping"}
            await handle_client_message(data, "client_1", mock_stream_manager)
            
            mock_conn_manager.send_personal_message.assert_called_once()
            call_args = mock_conn_manager.send_personal_message.call_args
            assert call_args[0][0]["type"] == "pong"

    @pytest.mark.asyncio
    async def test_handle_acknowledge_message(self, mock_stream_manager):
        """Test handling acknowledge message."""
        mock_stream_manager.acknowledge_alert = AsyncMock(return_value=True)
        
        with patch('src.api.websocket.manager') as mock_conn_manager:
            mock_conn_manager.send_personal_message = AsyncMock(return_value=True)
            
            data = {"type": "acknowledge", "alert_id": "alert-123"}
            await handle_client_message(data, "client_1", mock_stream_manager)
            
            mock_stream_manager.acknowledge_alert.assert_called_once_with("alert-123", "client_1")
            mock_conn_manager.send_personal_message.assert_called()

    @pytest.mark.asyncio
    async def test_handle_dismiss_message(self, mock_stream_manager):
        """Test handling dismiss message."""
        mock_stream_manager.dismiss_alert = AsyncMock(return_value=True)
        
        with patch('src.api.websocket.manager') as mock_conn_manager:
            mock_conn_manager.send_personal_message = AsyncMock(return_value=True)
            
            data = {"type": "dismiss", "alert_id": "alert-123"}
            await handle_client_message(data, "client_1", mock_stream_manager)
            
            mock_stream_manager.dismiss_alert.assert_called_once_with("alert-123", "client_1")
            mock_conn_manager.send_personal_message.assert_called()

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, mock_stream_manager):
        """Test handling subscribe message."""
        mock_stream_manager.update_subscription = AsyncMock()
        
        with patch('src.api.websocket.manager') as mock_conn_manager:
            mock_conn_manager.send_personal_message = AsyncMock(return_value=True)
            
            filters = {"severity": ["CRITICAL"]}
            data = {"type": "subscribe", "filters": filters}
            await handle_client_message(data, "client_1", mock_stream_manager)
            
            mock_stream_manager.update_subscription.assert_called_once_with("client_1", filters)

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_message(self, mock_stream_manager):
        """Test handling unsubscribe message."""
        mock_stream_manager.update_subscription = AsyncMock()
        
        with patch('src.api.websocket.manager') as mock_conn_manager:
            mock_conn_manager.send_personal_message = AsyncMock(return_value=True)
            
            data = {"type": "unsubscribe"}
            await handle_client_message(data, "client_1", mock_stream_manager)
            
            mock_stream_manager.update_subscription.assert_called_once_with("client_1", {})

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, mock_stream_manager):
        """Test handling unknown message type."""
        with patch('src.api.websocket.manager') as mock_conn_manager:
            mock_conn_manager.send_personal_message = AsyncMock(return_value=True)
            
            data = {"type": "unknown_type"}
            await handle_client_message(data, "client_1", mock_stream_manager)
            
            call_args = mock_conn_manager.send_personal_message.call_args
            assert call_args[0][0]["type"] == "error"
            assert "unknown_type" in call_args[0][0]["message"]


class TestAlertStreamService:
    """Tests for AlertStreamService."""

    @pytest.mark.asyncio
    async def test_publish_alert(self):
        """Test publishing an alert."""
        # Create a mock db session
        mock_db = AsyncMock()
        stream_service = AlertStreamService(mock_db)
        
        alert = StreamAlert(
            id=str(uuid4()),
            severity=SeverityLevel.HIGH,
            event_type="brute_force",
            title="Test Alert",
            message="Test message",
            user_email="test@example.com",
        )
        
        # Track callback
        callback_called = False
        def callback(a):
            nonlocal callback_called
            callback_called = True
        
        stream_service.register_callback(callback)
        await stream_service.publish_alert(alert)
        
        assert callback_called is True
        assert len(stream_service._recent_alerts) == 1

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        mock_db = AsyncMock()
        stream_service = AlertStreamService(mock_db)
        
        alert_id = str(uuid4())
        
        # Add alert to recent
        alert = StreamAlert(
            id=alert_id,
            severity=SeverityLevel.HIGH,
            event_type="test",
            title="Test",
            message="Test",
        )
        stream_service._recent_alerts.append(alert)
        
        result = await stream_service.acknowledge_alert(alert_id, "user_1")
        
        assert result is True
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "user_1"

    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_alert(self):
        """Test acknowledging a non-existent alert."""
        mock_db = AsyncMock()
        stream_service = AlertStreamService(mock_db)
        
        result = await stream_service.acknowledge_alert("nonexistent", "user_1")
        assert result is False

    @pytest.mark.asyncio
    async def test_dismiss_alert(self):
        """Test dismissing an alert."""
        mock_db = AsyncMock()
        stream_service = AlertStreamService(mock_db)
        
        alert_id = str(uuid4())
        
        alert = StreamAlert(
            id=alert_id,
            severity=SeverityLevel.LOW,
            event_type="test",
            title="Test",
            message="Test",
        )
        stream_service._recent_alerts.append(alert)
        
        result = await stream_service.dismiss_alert(alert_id, "user_1")
        
        assert result is True
        assert alert.status == AlertStatus.DISMISSED


class TestAlertStreamManager:
    """Tests for AlertStreamManager."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        manager = AsyncMock()
        manager.send_personal_message = AsyncMock(return_value=True)
        manager.broadcast = AsyncMock(return_value=1)
        return manager

    @pytest.fixture
    def mock_stream_service(self):
        """Create a mock AlertStreamService."""
        service = AsyncMock(spec=AlertStreamService)
        service.get_recent_alerts = AsyncMock(return_value=[])
        return service

    @pytest.mark.asyncio
    async def test_subscribe_client(self, mock_stream_service, mock_connection_manager):
        """Test subscribing a client."""
        manager = AlertStreamManager(mock_stream_service, mock_connection_manager)
        
        filters = {"severity": ["CRITICAL"]}
        await manager.subscribe_client("client_1", filters)
        
        assert manager._client_filters["client_1"] == filters
        mock_stream_service.get_recent_alerts.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_client(self, mock_stream_service, mock_connection_manager):
        """Test unsubscribing a client."""
        manager = AlertStreamManager(mock_stream_service, mock_connection_manager)
        
        await manager.subscribe_client("client_1", {})
        await manager.unsubscribe_client("client_1")
        
        assert "client_1" not in manager._client_filters

    @pytest.mark.asyncio
    async def test_broadcast_alert(self, mock_stream_service, mock_connection_manager):
        """Test broadcasting an alert."""
        manager = AlertStreamManager(mock_stream_service, mock_connection_manager)
        
        alert = StreamAlert(
            id=str(uuid4()),
            severity=SeverityLevel.CRITICAL,
            event_type="test",
            title="Test Alert",
            message="Test message",
            user_email=None,
            tenant_id=None,
        )
        
        sent_count = await manager.broadcast_alert(alert)
        
        assert sent_count == 1
        mock_connection_manager.broadcast.assert_called_once()
        call_args = mock_connection_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "new_alert"
        assert call_args["alert"]["id"] == alert.id

    @pytest.mark.asyncio
    async def test_acknowledge_alert_broadcast(self, mock_stream_service, mock_connection_manager):
        """Test that acknowledging broadcasts to all clients."""
        mock_stream_service.acknowledge_alert = AsyncMock(return_value=True)
        
        manager = AlertStreamManager(mock_stream_service, mock_connection_manager)
        
        result = await manager.acknowledge_alert("alert-123", "client_1")
        
        assert result is True
        mock_connection_manager.broadcast.assert_called_once()
        call_args = mock_connection_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "alert_acknowledged"

    @pytest.mark.asyncio
    async def test_dismiss_alert_broadcast(self, mock_stream_service, mock_connection_manager):
        """Test that dismissing broadcasts to all clients."""
        mock_stream_service.dismiss_alert = AsyncMock(return_value=True)
        
        manager = AlertStreamManager(mock_stream_service, mock_connection_manager)
        
        result = await manager.dismiss_alert("alert-123", "client_1")
        
        assert result is True
        mock_connection_manager.broadcast.assert_called_once()
        call_args = mock_connection_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "alert_dismissed"


class TestStreamAlert:
    """Tests for StreamAlert dataclass."""

    def test_to_dict(self):
        """Test converting StreamAlert to dictionary."""
        alert = StreamAlert(
            id="alert-123",
            severity=SeverityLevel.CRITICAL,
            event_type="brute_force",
            title="Brute Force Attack",
            message="Multiple failed login attempts detected",
            user_email="user@example.com",
            tenant_id="tenant-456",
            metadata={"ip_address": "1.2.3.4"},
        )
        
        result = alert.to_dict()
        
        assert result["id"] == "alert-123"
        assert result["severity"] == "CRITICAL"
        assert result["event_type"] == "brute_force"
        assert result["severity_emoji"] == "🔥"
        assert result["event_type_name"] == "Brute Force Attack"
        assert result["status"] == "new"

    def test_to_dict_with_acknowledgment(self):
        """Test converting acknowledged alert to dictionary."""
        alert = StreamAlert(
            id="alert-123",
            severity=SeverityLevel.HIGH,
            event_type="test",
            title="Test",
            message="Test",
            user_email=None,
            tenant_id=None,
            status=AlertStatus.ACKNOWLEDGED,
            acknowledged_by="admin",
            acknowledged_at=datetime.now(timezone.utc),
        )
        
        result = alert.to_dict()
        
        assert result["status"] == "acknowledged"
        assert result["acknowledged_by"] == "admin"
        assert result["acknowledged_at"] is not None
