"""Tests for WebSocket endpoints"""

import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocketDisconnect
from app.api.ws import WebSocketLogHandler, active_connections, websocket_logs


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection route is registered"""
    from app.main import app

    # Verify the WebSocket route is registered
    ws_route = next((route for route in app.routes if route.path == "/ws/logs"), None)
    assert ws_route is not None


@pytest.mark.asyncio
async def test_websocket_handler_emit():
    """Test WebSocketLogHandler broadcasts to connected clients"""
    # Create a mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.send_text = AsyncMock()

    # Add to active connections
    active_connections.add(mock_ws)

    try:
        # Create handler
        handler = WebSocketLogHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test log message",
            args=(),
            exc_info=None,
        )

        # Emit should broadcast to the mock WebSocket
        handler.emit(record)

        # Verify send_text was called
        assert mock_ws.send_text.called
    finally:
        active_connections.discard(mock_ws)


@pytest.mark.asyncio
async def test_websocket_handler_emit_multiple_clients():
    """Test WebSocketLogHandler broadcasts to multiple clients"""
    # Create multiple mock WebSockets
    mock_ws1 = AsyncMock()
    mock_ws1.send_text = AsyncMock()
    mock_ws2 = AsyncMock()
    mock_ws2.send_text = AsyncMock()

    active_connections.add(mock_ws1)
    active_connections.add(mock_ws2)

    try:
        handler = WebSocketLogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Multi-client broadcast",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Both clients should receive the message
        assert mock_ws1.send_text.called
        assert mock_ws2.send_text.called
    finally:
        active_connections.discard(mock_ws1)
        active_connections.discard(mock_ws2)


@pytest.mark.asyncio
async def test_websocket_logs_endpoint_infers_disconnect():
    """Test websocket_logs function handles WebSocketDisconnect"""
    from fastapi import WebSocketDisconnect

    # Mock WebSocket that raises disconnect
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
    mock_ws.close = AsyncMock()

    # Should not raise, just exit gracefully
    await websocket_logs(mock_ws)

    # Verify accept was called
    mock_ws.accept.assert_called_once()
    # Verify the connection was added and then removed
    assert mock_ws not in active_connections


@pytest.mark.asyncio
async def test_websocket_logs_handles_ping():
    """Test websocket_logs function handles ping/pong"""
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(side_effect=["ping", WebSocketDisconnect()])
    mock_ws.send_text = AsyncMock()
    mock_ws.close = AsyncMock()

    await websocket_logs(mock_ws)

    # Should have responded to ping with pong
    mock_ws.send_text.assert_called_with("pong")


def test_websocket_log_handler_creation():
    """Test WebSocketLogHandler can be instantiated"""
    handler = WebSocketLogHandler()
    assert handler is not None
    assert handler.level == logging.NOTSET


def test_websocket_log_handler_format():
    """Test WebSocketLogHandler formats log records correctly"""
    handler = WebSocketLogHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=1,
        msg="Warning message",
        args=(),
        exc_info=None,
    )

    formatted = handler.format(record)
    assert "Warning message" in formatted
    assert "WARNING" in formatted


def test_no_connections_no_error():
    """Test handler doesn't raise error when no connections active"""
    # Ensure no connections
    active_connections.clear()

    handler = WebSocketLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="No listeners",
        args=(),
        exc_info=None,
    )

    # Should not raise
    handler.emit(record)


@pytest.mark.asyncio
async def test_websocket_logs_endpoint_with_real_async():
    """Test websocket_logs with simulated receive_text and close"""
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.close = AsyncMock()

    # Simulate the loop handling
    active_connections.add(mock_ws)

    # Verify cleanup on disconnect path
    mock_ws.receive_text.side_effect = Exception("Connection closed")
    try:
        await websocket_logs(mock_ws)
    except Exception:
        pass

    assert mock_ws not in active_connections
