"""REST API endpoints for config, rules, history, and polishing"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config_manager import get_config_manager, DEFAULT_CONFIG
from app.core.history_db import get_history_db

logger = logging.getLogger(__name__)

# Global polishing service (set via startup event)
_polishing_service: Optional[Any] = None


def set_polishing_service(service: Any) -> None:
    """Set the global polishing service instance"""
    global _polishing_service
    _polishing_service = service


def get_polishing_service() -> Any:
    """Get the global polishing service instance"""
    return _polishing_service


async def initialize_polishing_service() -> None:
    """
    Initialize or refresh the global polishing service based on current config.
    Closes the previous client if it exists.
    """
    global _polishing_service
    logger.info("!!! [INIT] Starting initialize_polishing_service...")
    
    # 1. Close old client to prevent leaks
    if _polishing_service and _polishing_service.llm_client:
        try:
            await _polishing_service.llm_client.close()
            logger.info("!!! [INIT] Closed old LLM client")
        except Exception as e:
            logger.warning(f"Error closing old LLM client during refresh: {e}")
    
    # 2. Read current config
    manager = get_config_manager()
    config = manager.read_config()
    logger.info(f"!!! [INIT] Read config: {config.get('llm', {}).get('active_provider')}")
    llm_config = config.get("llm", {})
    providers = llm_config.get("providers", {})
    active_provider = llm_config.get("active_provider", "openai")
    active_provider_cfg = providers.get(active_provider, {})
    api_key = active_provider_cfg.get("api_key", "")
    
    if not api_key:
        logger.warning(f"!!! [INIT] No API key found for {active_provider} - aborting")
        _polishing_service = None
        return
    
    # 3. Create new client and service
    from app.core.llm_client import create_llm_client
    from app.engine.polishing_service import create_polishing_service
    
    try:
        logger.info("!!! [INIT] Creating LLM client...")
        client = await create_llm_client(
            provider=active_provider,
            api_key=api_key,
            base_url=active_provider_cfg.get("base_url", ""),
            model=active_provider_cfg.get("active_model", ""),
            api_type=active_provider_cfg.get("api", "openai"),
            timeout=120.0,
        )
        logger.info("!!! [INIT] LLM client created successfully")
        
        logger.info("!!! [INIT] Creating polishing service...")
        service = await create_polishing_service(client)
        set_polishing_service(service)
        logger.info(f"!!! [INIT] Polishing service set globally: provider={active_provider}")
    except Exception as e:
        logger.error(f"!!! [INIT] FAILED to initialize polishing service: {e}", exc_info=True)
        _polishing_service = None


router = APIRouter()


@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@router.get("/api/config")
async def get_config() -> Dict[str, Any]:
    """Get full configuration"""
    manager = get_config_manager()
    return manager.read_config()


@router.patch("/api/config")
async def patch_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Partially update configuration (supports nested keys)"""
    from app.core.config_manager import FileLockError
    manager = get_config_manager()
    try:
        return manager.patch_config(patch)
    except FileLockError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/api/config")
async def post_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Replace entire configuration with provided values (full replacement)"""
    from app.core.config_manager import FileLockError
    manager = get_config_manager()
    if manager._is_read_only:
        raise HTTPException(status_code=409, detail="Config is read-only due to lock timeout. Please retry later.")
    manager.write_config(config)
    return {"status": "ok", "message": "Config written successfully"}


@router.post("/api/config/reset")
async def reset_config() -> Dict[str, Any]:
    """Reset configuration to defaults"""
    manager = get_config_manager()
    manager.write_config(DEFAULT_CONFIG)
    return {"status": "ok", "message": "Config reset to defaults"}


@router.post("/api/config/test-connection")
async def test_connection(provider_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test LLM API connection with given provider credentials.
    And refresh the global polishing service to ensure new config is active.
    """
    from app.core.llm_client import create_llm_client, LLMConnectionError
    from app.api.rest import initialize_polishing_service

    # Support both nested provider config and flat config for testing
    providers = provider_config.get("providers", {})
    active_provider = provider_config.get("active_provider", "openai")
    
    if active_provider in providers:
        provider_data = providers[active_provider]
    else:
        # Fallback to flat config (direct fields in provider_config)
        provider_data = provider_config

    api_key = provider_data.get("api_key", "").strip()
    base_url = provider_data.get("base_url", "").strip()
    active_model = provider_data.get("model", provider_data.get("active_model", "")).strip()
    api_type = provider_data.get("api", "openai").strip()

    if not api_key:
        return {"ok": False, "error": "API Key 不能为空"}
    if not base_url:
        return {"ok": False, "error": "Base URL 不能为空"}
    if not active_model:
        return {"ok": False, "error": "请先选择一个模型"}

    client = None
    try:
        client = await create_llm_client(
            provider=active_provider,
            api_key=api_key,
            base_url=base_url,
            model=active_model,
            api_type=api_type,
            timeout=30.0,
        )
        result = await client.test_connection()
        
        # IMPORTANT: Even if connection is not fully verified, refresh the global service instance
        # so we can test the pipeline with our mock client.
        await initialize_polishing_service()
        
        return {"ok": True, "model": result["model"], "response": result.get("response", "OK")}
    except LLMConnectionError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"连接失败: {str(e)}"}
    finally:
        if client:
            await client.close()


@router.get("/api/config/path")
async def get_config_path() -> Dict[str, str]:
    """Get configuration file paths"""
    manager = get_config_manager()
    return {
        "config": manager.get_config_path(),
        "rules": manager.get_rules_path(),
    }


@router.get("/api/rules")
async def get_rules() -> Dict[str, Any]:
    """Get rules configuration"""
    manager = get_config_manager()
    return manager.read_rules()


@router.post("/api/rules")
async def post_rules(rules: Dict[str, Any]) -> Dict[str, Any]:
    """Replace rules configuration entirely"""
    manager = get_config_manager()
    manager.write_rules(rules)
    return {"status": "ok", "message": "Rules updated successfully"}


@router.post("/api/history/rollback/{snapshot_id}")
async def rollback_to_snapshot(snapshot_id: int) -> Dict[str, Any]:
    """Rollback system config and rules to a specific snapshot state"""
    db = get_history_db()
    snapshot = await db.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    manager = get_config_manager()
    
    # 1. Rollback config
    config_snapshot = snapshot.get("config_snapshot", {})
    if config_snapshot:
        # Merge with current config to avoid erasing other sections (like 'ui' or 'engine')
        current_config = manager.read_config()
        updated_config = {**current_config, **config_snapshot}
        manager.write_config(updated_config)
    
    # 2. Rollback rules
    rules_snapshot = snapshot.get("rules_snapshot", {})
    if rules_snapshot:
        manager.write_rules(rules_snapshot)
    
    # 3. Refresh the active service instance
    await initialize_polishing_service()
    
    return {"status": "ok", "message": f"Successfully rolled back to snapshot {snapshot_id}"}

@router.get("/api/history")
async def get_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Get list of all snapshots (newest first)"""
    db = get_history_db()
    return await db.get_all_snapshots(limit=limit)


@router.get("/api/history/count")
async def get_history_count() -> Dict[str, int]:
    """Get total number of snapshots"""
    db = get_history_db()
    count = await db.get_snapshot_count()
    return {"count": count}


@router.get("/api/history/{snapshot_id}")
async def get_history_detail(snapshot_id: int) -> Dict[str, Any]:
    """Get a specific snapshot by ID"""
    db = get_history_db()
    snapshot = await db.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.delete("/api/history/{snapshot_id}")
async def delete_history(snapshot_id: int) -> Dict[str, Any]:
    """Delete a specific snapshot"""
    db = get_history_db()
    success = await db.delete_snapshot(snapshot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"status": "ok", "message": "Snapshot deleted"}


class PolishTextRequest(BaseModel):
    """Request body for POST /api/polish"""
    text: str = Field(..., min_length=1, max_length=100000, description="Fiction text to polish")
    rules_state: Optional[Dict[str, Any]] = Field(None, description="Rules to apply")
    enable_safety_exempt: bool = Field(True, description="Enable safety exemption")
    enable_xml_isolation: bool = Field(True, description="Enable XML isolation")


@router.post("/api/polish")
async def polish_text(request: PolishTextRequest) -> Dict[str, Any]:
    """
    Polish fiction text using LLM.
    """
    logger.info(f"!!! [REST] Received polish request. Text length: {len(request.text)}")
    
    from app.engine.polishing_service import PolishRequest
    
    service = get_polishing_service()
    logger.info(f"!!! [REST] Service instance: {service} (Type: {type(service)})")
    
    if service is None:
        logger.info("!!! [REST] Service is None, attempting emergency initialization...")
        await initialize_polishing_service()
        service = get_polishing_service()
        if service is None:
            logger.error("!!! [REST] Emergency initialization failed!")
            raise HTTPException(status_code=503, detail="Polishing service not initialized")
    
    config = get_config_manager().read_config()
    rules = get_config_manager().read_rules()
    
    polish_request = PolishRequest(
        text=request.text,
        rules_state=request.rules_state,
        enable_safety_exempt=request.enable_safety_exempt,
        enable_xml_isolation=request.enable_xml_isolation,
    )
    
    try:
        logger.info("!!! [REST] Calling service.polish_text()...")
        result = await service.polish_text(polish_request)
        logger.info("!!! [REST] service.polish_text() returned successfully.")

        # Record history snapshot (both success and partial failure)
        try:
            db = get_history_db()
            await db.insert_snapshot(
                original_text=request.text,
                revised_text=result.polished_text,
                rules_snapshot=request.rules_state if request.rules_state else rules,
                config_snapshot={"llm": config.get("llm", {})},
                chunk_params={
                    "chunks_processed": result.chunks_processed,
                    "total_tokens": result.total_tokens,
                },
            )
        except Exception as hist_err:
            logger.warning(f"Failed to record history: {hist_err}")

        # Check if all chunks failed (silent failure)
        if result.total_tokens == 0 and result.chunks_processed > 0:
            logger.warning(f"Polish request produced no tokens - LLM may have failed. chunks={result.chunks_processed}")
            return {
                "original_text": result.original_text,
                "polished_text": result.polished_text,
                "modifications": result.modifications,
                "chunks_processed": result.chunks_processed,
                "total_tokens": result.total_tokens,
                "warning": "No tokens consumed - LLM may not have been called. Check API key and model configuration.",
            }

        return {
            "original_text": result.original_text,
            "polished_text": result.polished_text,
            "modifications": result.modifications,
            "chunks_processed": result.chunks_processed,
            "total_tokens": result.total_tokens,
        }
    except Exception as e:
        logger.error(f"!!! [REST] Polish request failed: {e}", exc_info=True)
        # Record failed attempt in history
        try:
            db = get_history_db()
            await db.insert_snapshot(
                original_text=request.text,
                revised_text=request.text,  # No revision on failure
                rules_snapshot=request.rules_state if request.rules_state else rules,
                config_snapshot={"llm": config.get("llm", {})},
                chunk_params={"error": str(e)},
            )
        except Exception as hist_err:
            logger.warning(f"Failed to record history for failed request: {hist_err}")
        raise HTTPException(status_code=500, detail=str(e))
