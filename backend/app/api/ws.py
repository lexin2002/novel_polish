"""WebSocket endpoints and log broadcasting"""

import asyncio
import logging
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that broadcasts logs to all WebSocket clients"""

    def emit(self, record: logging.LogRecord):
        """Broadcast log message to all connected WebSocket clients"""
        if not active_connections:
            return

        try:
            msg = self.format(record)
            for connection in list(active_connections):
                try:
                    # Schedule async send without blocking
                    asyncio.create_task(connection.send_text(msg))
                except Exception:
                    # Connection may be closed, remove it
                    active_connections.discard(connection)
        except Exception:
            self.handleError(record)


def setup_logging_handler(logger: logging.Logger) -> WebSocketLogHandler:
    """Attach WebSocket handler to a logger"""
    handler = WebSocketLogHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
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
