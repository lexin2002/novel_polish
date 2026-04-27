"""Novel Polish Backend - FastAPI Application"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rest import router as rest_router, set_polishing_service
from app.api.ws import websocket_logs, setup_logging_handler
from app.core.config import (
    CORS_ORIGINS,
    HOST,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    PORT,
)
from app.core.config_manager import get_config_manager
from app.core.history_db import get_history_db
from app.engine.polishing_service import create_polishing_service

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

    # Initialize history database
    history_db = get_history_db()
    await history_db.initialize()

    # Set max snapshots from config
    try:
        config = get_config_manager().read_config()
        max_snapshots = config.get("history", {}).get("max_snapshots", 20)
        history_db.set_max_snapshots(max_snapshots)
        logger.info(f"History max_snapshots set to {max_snapshots}")

        # Initialize SiliconFlow client and polishing service if API key is configured
        llm_config = config.get("llm", {})
        providers = llm_config.get("providers", {})
        siliconflow_cfg = providers.get("siliconflow", {})
        api_key = siliconflow_cfg.get("api_key", "")
        if api_key:
            logger.info("SiliconFlow API key configured, initializing polishing service")
            from app.core.siliconflow_client import create_siliconflow_client
            client = await create_siliconflow_client(
                api_key=api_key,
                base_url=siliconflow_cfg.get("base_url"),
                model=siliconflow_cfg.get("active_model"),
            )
            service = await create_polishing_service(client)
            set_polishing_service(service)
            logger.info("Polishing service initialized successfully")
        else:
            logger.warning("No SiliconFlow API key configured - /api/polish will return 503")

    except Exception as e:
        logger.warning(f"Could not load config: {e}")

    yield

    # Cleanup
    service = None
    try:
        from app.api.rest import get_polishing_service
        service = get_polishing_service()
        if service and service.llm_client:
            await service.llm_client.close()
    except Exception as e:
        logger.warning(f"Error closing LLM client: {e}")

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
