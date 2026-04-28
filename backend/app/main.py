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
    handlers=[
        logging.FileHandler("backend_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
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

        # Initialize LLM client and polishing service with active provider
        llm_config = config.get("llm", {})
        providers = llm_config.get("providers", {})
        active_provider = llm_config.get("active_provider", "openai")
        active_provider_cfg = providers.get(active_provider, {})
        api_key = active_provider_cfg.get("api_key", "")

        if api_key:
            logger.info(f"API key configured for '{active_provider}', initializing polishing service")
            from app.core.llm_client import create_llm_client
            client = await create_llm_client(
                provider=active_provider,
                api_key=api_key,
                base_url=active_provider_cfg.get("base_url", ""),
                model=active_provider_cfg.get("active_model", ""),
                api_type=active_provider_cfg.get("api", "openai"),  # Pass API type
                timeout=120.0,
            )
            service = await create_polishing_service(client)
            set_polishing_service(service)
            logger.info(f"Polishing service initialized with provider={active_provider}, model={active_provider_cfg.get('active_model')}, api={active_provider_cfg.get('api')}")
        else:
            logger.warning(f"No API key configured for active provider '{active_provider}' - /api/polish will return 503")

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


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Novel Polish Backend",
    description="Backend service for Novel Polish desktop application",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"!!! [MIDDLEWARE] Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"!!! [MIDDLEWARE] Response status: {response.status_code} for {request.url.path}")
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach WebSocket handler to the app logger only.
# uvicorn logs propagate to root logger automatically, so they are included.
setup_logging_handler(logger)

# Include routers
app.include_router(rest_router)
app.add_api_websocket_route("/ws/logs", websocket_logs)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
