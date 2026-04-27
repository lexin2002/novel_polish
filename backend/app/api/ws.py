"""WebSocket endpoints and log broadcasting"""

import asyncio
import logging
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that broadcasts logs to all WebSocket clients"""

    async def _safe_send(self, ws: WebSocket, msg: str) -> None:
        """Send message to a WebSocket connection, discarding on failure."""
        try:
            await ws.send_text(msg)
        except Exception:
            active_connections.discard(ws)

    def _schedule_send(self, ws: WebSocket, msg: str) -> None:
        """Schedule sending log message to a WebSocket connection.

        Handles both async and sync contexts:
        - If a running event loop exists, create a task directly.
        - Otherwise, use call_soon_threadsafe to schedule on the event loop.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._safe_send(ws, msg))
        except RuntimeError:
            # No running event loop (e.g. called from a sync thread)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(
                        lambda w=ws, m=msg: asyncio.create_task(self._safe_send(w, m))
                    )
            except RuntimeError:
                # No event loop at all — fallback: discard silently
                active_connections.discard(ws)

    def emit(self, record: logging.LogRecord):
        """Broadcast log message to all connected WebSocket clients."""
        if not active_connections:
            return

        try:
            msg = self.format(record)
            for ws in list(active_connections):
                self._schedule_send(ws, msg)
        except Exception:
            self.handleError(record)


def setup_logging_handler(logger: logging.Logger) -> WebSocketLogHandler:
    """Attach WebSocket handler to a logger"""
    handler = WebSocketLogHandler()
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    return handler


async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for log streaming"""
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Keep connection alive, wait for client messages
            try:
                data = await websocket.receive_text()
                # Echo back for ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    finally:
        active_connections.discard(websocket)
