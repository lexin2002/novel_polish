"""REST API endpoints for config, rules, and history"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.core.config_manager import get_config_manager
from app.core.history_db import get_history_db

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
    manager = get_config_manager()
    return manager.patch_config(patch)


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
