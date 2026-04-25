"""Novel Polish Backend - FastAPI Application"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rest import router as rest_router
from app.api.ws import websocket_logs, setup_logging_handler
from app.core.config import (
    CORS_ORIGINS,
    HOST,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    PORT,
)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    logger.info(f"Novel Polish Backend starting on {HOST}:{PORT}")
    logger.info("REST API: GET /api/health")
    logger.info("WebSocket: WS /ws/logs")
    yield
    logger.info("Novel Polish Backend shutting down")


# Create FastAPI app
app = FastAPI(
    title="Novel Polish Backend",
    description="Backend service for Novel Polish desktop application",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach WebSocket handler to root logger
setup_logging_handler(logger)
# Also attach to uvicorn logger for request logging
uvicorn_logger = logging.getLogger("uvicorn")
setup_logging_handler(uvicorn_logger)

# Include routers
app.include_router(rest_router)
app.add_api_websocket_route("/ws/logs", websocket_logs)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
