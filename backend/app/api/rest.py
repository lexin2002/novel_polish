"""REST API endpoints for config and rules"""

from typing import Any, Dict

from fastapi import APIRouter

from app.core.config_manager import get_config_manager

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
