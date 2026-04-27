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
    """Reset configuration to provided values (full replacement)"""
    from app.core.config_manager import FileLockError
    manager = get_config_manager()
    if manager._is_read_only:
        raise HTTPException(status_code=409, detail="Config is read-only due to lock timeout. Please retry later.")
    manager.write_config(config)
    return {"status": "ok", "message": "Config reset successfully"}


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

    Request body (from config.llm section):
        active_provider: str - Provider ID
        providers: Dict[str, ProviderConfig] - All provider configs

    Returns:
        {"ok": True, "model": "...", "response": "..."} on success
        {"ok": False, "error": "..."} on failure
    """
    from app.core.llm_client import create_llm_client, LLMConnectionError

    providers = provider_config.get("providers", {})
    active_provider = provider_config.get("active_provider", "openai")

    if active_provider not in providers:
        return {"ok": False, "error": f"Provider '{active_provider}' not found in config"}

    provider_data = providers[active_provider]
    api_key = provider_data.get("api_key", "").strip()
    base_url = provider_data.get("base_url", "").strip()
    active_model = provider_data.get("active_model", "").strip()
    api_type = provider_data.get("api", "openai").strip()  # Read api type from config

    if not api_key:
        return {"ok": False, "error": "API Key 不能为空"}
    if not base_url:
        return {"ok": False, "error": "Base URL 不能为空"}
    if not active_model:
        return {"ok": False, "error": "请先选择一个模型"}

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
        await client.close()
        return {"ok": True, "model": result["model"], "response": result.get("response", "OK")}
    except LLMConnectionError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"连接失败: {str(e)}"}


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

    Request body:
        text: str - The fiction text to polish
        rules_state: Optional[Dict] - Rules to apply
        enable_safety_exempt: Optional[bool] - Enable safety exemption (default: True)
        enable_xml_isolation: Optional[bool] - Enable XML isolation (default: True)

    Returns:
        Dict with polished_text, modifications, chunks_processed, total_tokens
    """
    from app.engine.polishing_service import PolishRequest

    service = get_polishing_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Polishing service not initialized")

    polish_request = PolishRequest(
        text=request.text,
        rules_state=request.rules_state,
        enable_safety_exempt=request.enable_safety_exempt,
        enable_xml_isolation=request.enable_xml_isolation,
    )

    try:
        result = await service.polish_text(polish_request)
        return {
            "original_text": result.original_text,
            "polished_text": result.polished_text,
            "modifications": result.modifications,
            "chunks_processed": result.chunks_processed,
            "total_tokens": result.total_tokens,
        }
    except Exception as e:
        logger.error(f"Polish request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
