"""Configuration Manager - Atomic file persistence with FileLock"""

import json
import logging
import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

import filelock
import json5

logger = logging.getLogger(__name__)


# ─── Supported LLM Providers ────────────────────────────────────────────────
LLM_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "api": "openai",
        "default_base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "name": "Anthropic",
        "api": "anthropic",
        "default_base_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-5-sonnet-latest", "claude-3-opus-latest", "claude-3-haiku-latest"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "api": "openai",
        "default_base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
    "qwen": {
        "name": "通义千问",
        "api": "openai",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "api": "openai",
        "default_base_url": "https://api.siliconflow.cn/v1",
        "models": ["THUDM/GLM-4-32B-0414", "Qwen/Qwen2-72B-Instruct", "deepseek-ai/DeepSeek-V2.5"],
    },
    "custom": {
        "name": "自定义",
        "api": "openai",
        "default_base_url": "",
        "models": [],
    },
}


def _make_provider_config(provider_id: str) -> Dict[str, Any]:
    """Build a default provider config entry."""
    info = LLM_PROVIDERS.get(provider_id, LLM_PROVIDERS["custom"])
    return {
        "name": info["name"],
        "api": info["api"],
        "api_key": "",
        "base_url": info["default_base_url"],
        "models": list(info["models"]),
        "active_model": info["models"][0] if info["models"] else "",
    }


def _build_default_llm_config() -> Dict[str, Any]:
    """Build the default LLM config section with all providers."""
    providers: Dict[str, Any] = {}
    for provider_id in LLM_PROVIDERS:
        providers[provider_id] = _make_provider_config(provider_id)

    return {
        "active_provider": "openai",
        "temperature": 0.4,
        "max_tokens": 4096,
        "safety_exempt_enabled": True,
        "xml_tag_isolation_enabled": True,
        "desensitize_mode": False,
        "providers": providers,
    }


def _get_config_dir() -> Path:
    """Get platform-appropriate user config directory.

    Returns:
        Path to the config directory:
        - Linux/macOS: ~/.config/NovelPolish
        - Windows: %APPDATA%/NovelPolish
    """
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        config_dir = Path(base) / "NovelPolish"
    else:
        # Linux/macOS: ~/.config/NovelPolish
        config_dir = Path.home() / ".config" / "NovelPolish"

    # Ensure directory exists
    config_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Config directory: {config_dir}")
    return config_dir


# Default configuration structure
DEFAULT_CONFIG: Dict[str, Any] = {
    "priority_order": ["P0", "P1", "P2", "P3"],
    "llm": _build_default_llm_config(),
    "engine": {
        "chunk_size": 1000,
        "chunk_size_min": 500,
        "chunk_size_max": 3000,
        "max_workers": 3,
        "max_revisions": 2,
        "context_overlap_chars": 200,
        "context_snap_to_punctuation": True,
        "request_jitter_range": [0.2, 1.5],
        "max_requests_per_second": 2,
        "chunk_timeout_seconds": 60,
        "enable_invalid_modification_break": True,
    },
    "network": {
        "request_timeout": 5,
        "retry_count": 3,
        "circuit_breaker_threshold": 3,
    },
    "ui": {
        "log_to_file_enabled": True,
        "log_file_dir": "./logs",
        "experimental_realtime_log": False,
        "sync_scroll_default": False,
    },
    "history": {
        "max_snapshots": 20,
    },
}

# Default rules structure
DEFAULT_RULES: Dict[str, Any] = {
    "main_categories": [
        {
            "name": "语法与标点",
            "priority": "P0",
            "is_active": True,
            "sub_categories": [
                {
                    "name": "错别字",
                    "priority": "P0",
                    "rules": [
                        {
                            "name": "常见形近字错误",
                            "is_active": True,
                            "instruction": '将"在"改为"再"当表示重复时；将"的"改为"地"当修饰动词时。',
                            "direction": "诊断并修改",
                        }
                    ],
                }
            ],
        },
        {
            "name": "逻辑一致性",
            "priority": "P1",
            "is_active": True,
            "sub_categories": [
                {
                    "name": "时间线矛盾",
                    "priority": "P0",
                    "rules": [
                        {
                            "name": "时序检查",
                            "is_active": True,
                            "instruction": "确保事件发生的先后顺序符合逻辑，不一致时调整副词或分句顺序。",
                            "direction": "诊断并修改",
                        }
                    ],
                }
            ],
        },
    ]
}


class ConfigurationManager:
    """Manage atomic read/write of config.jsonc and rules.json with FileLock"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            self.data_dir = _get_config_dir()
        else:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = self.data_dir / "config.jsonc"
        self.rules_path = self.data_dir / "rules.json"
        self.config_lock_path = self.data_dir / "config.jsonc.lock"
        self.rules_lock_path = self.data_dir / "rules.json.lock"

        # Initialize files if they don't exist
        self._ensure_files()

    def _ensure_files(self) -> None:
        """Ensure config and rules files exist with defaults"""
        if not self.config_path.exists():
            self._atomic_write_config(DEFAULT_CONFIG.copy())

        if not self.rules_path.exists():
            self._atomic_write_rules(DEFAULT_RULES.copy())

    def _atomic_write_config(self, data: Dict[str, Any]) -> None:
        """Write config with FileLock + temp file + os.replace"""
        with filelock.FileLock(self.config_lock_path, timeout=10):
            # Write to temporary file first
            tmp_path = self.config_path.with_suffix(".jsonc.tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json5.dump(data, f, indent=2, ensure_ascii=False)

                # Atomic rename
                os.replace(tmp_path, self.config_path)
                logger.info(f"Config written atomically to {self.config_path}")
            except Exception:
                # Clean up temp file on failure
                if tmp_path.exists():
                    tmp_path.unlink()
                raise

    def _atomic_write_rules(self, data: Dict[str, Any]) -> None:
        """Write rules with FileLock + temp file + os.replace"""
        with filelock.FileLock(self.rules_lock_path, timeout=10):
            tmp_path = self.rules_path.with_suffix(".json.tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                os.replace(tmp_path, self.rules_path)
                logger.info(f"Rules written atomically to {self.rules_path}")
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink()
                raise

    def read_config(self) -> Dict[str, Any]:
        """Read config.jsonc with fallback to default on error.
        Auto-fixes corrupted provider data on read and persists fixes.
        """
        with filelock.FileLock(self.config_lock_path, timeout=10):
            try:
                if not self.config_path.exists():
                    return DEFAULT_CONFIG.copy()

                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json5.load(f)

                # Auto-fix corrupted provider data and persist
                llm_config = data.get("llm", {})
                data["llm"], was_modified = self._migrate_llm_config(llm_config)
                if was_modified:
                    self._atomic_write_config(data)
                    logger.info("Auto-fixed corrupted provider data in config")

                logger.debug("Config read successfully")
                return data
            except Exception as e:
                msg = f"Config read failed: {e}, falling back to default"
                logger.warning(msg)
                return DEFAULT_CONFIG.copy()

    def write_config(self, data: Dict[str, Any]) -> None:
        """Write config.jsonc with validation + migration"""
        # Validate required keys
        for key in DEFAULT_CONFIG:
            if key not in data:
                logger.warning(f"Missing key '{key}' in config, using default")
                data[key] = DEFAULT_CONFIG[key]

        # Migrate old flat llm config to new provider-centric format
        data["llm"], _ = self._migrate_llm_config(data.get("llm", {}))

        self._atomic_write_config(data)

    def _migrate_llm_config(self, llm_config: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        """Migrate old flat llm config to new provider-centric format.
        Returns (config, was_modified) tuple for write-back if needed.
        """
        default = _build_default_llm_config()
        was_modified = False

        # If already migrated, check data integrity and fix if needed
        if "providers" in llm_config:
            # Ensure all provider slots exist (newly added providers)
            for provider_id in LLM_PROVIDERS:
                if provider_id not in llm_config["providers"]:
                    llm_config["providers"][provider_id] = _make_provider_config(provider_id)
                    was_modified = True

            # Fix ALL provider data that may have been written with wrong defaults
            for provider_id, provider_data in llm_config["providers"].items():
                if provider_id not in LLM_PROVIDERS:
                    continue
                info = LLM_PROVIDERS[provider_id]
                # Fix missing or wrong api field
                if provider_data.get("api") != info["api"]:
                    provider_data["api"] = info["api"]
                    was_modified = True
                # Only fix empty base_url (allow user to set custom base_url)
                if not provider_data.get("base_url"):
                    provider_data["base_url"] = info["default_base_url"]
                    was_modified = True
                # Fix models list if missing but provider should have models
                if not provider_data.get("models") and info["models"]:
                    provider_data["models"] = list(info["models"])
                    provider_data["active_model"] = info["models"][0]
                    was_modified = True
            return llm_config, was_modified

        # Migrate old format: flatten llm config → providers
        old_provider = llm_config.get("provider", "openai")
        providers: Dict[str, Any] = {}
        for provider_id in LLM_PROVIDERS:
            providers[provider_id] = _make_provider_config(provider_id)

        # Copy old values into the old provider slot
        if old_provider in providers:
            providers[old_provider]["api_key"] = llm_config.get("api_key", "")
            providers[old_provider]["base_url"] = llm_config.get("base_url", providers[old_provider]["base_url"])
            providers[old_provider]["active_model"] = llm_config.get("model", providers[old_provider]["active_model"])
            # Only add the old model if it exists and isn't in the default list
            old_model = llm_config.get("model")
            if old_model and old_model not in providers[old_provider]["models"]:
                providers[old_provider]["models"] = [old_model] + providers[old_provider]["models"]

        result = default.copy()
        result["providers"] = providers
        result["active_provider"] = old_provider
        result["temperature"] = llm_config.get("temperature", 0.4)
        result["max_tokens"] = llm_config.get("max_tokens", 4096)
        result["safety_exempt_enabled"] = llm_config.get("safety_exempt_enabled", True)
        result["xml_tag_isolation_enabled"] = llm_config.get("xml_tag_isolation_enabled", True)
        result["desensitize_mode"] = llm_config.get("desensitize_mode", False)

        logger.info(f"Migrated llm config from old format, active_provider={old_provider}")
        return result, True

    def patch_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Partially update config"""
        config = self.read_config()

        # Deep merge patch into config
        def deep_merge(base: Dict, updates: Dict) -> Dict:
            for key, value in updates.items():
                if (
                    key in base
                    and isinstance(base[key], dict)
                    and isinstance(value, dict)
                ):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base

        config = deep_merge(config, patch)
        self.write_config(config)
        return config

    def read_rules(self) -> Dict[str, Any]:
        """Read rules.json with fallback to default on error"""
        with filelock.FileLock(self.rules_lock_path, timeout=10):
            try:
                if not self.rules_path.exists():
                    return DEFAULT_RULES.copy()

                with open(self.rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                logger.debug("Rules read successfully")
                return data
            except Exception as e:
                msg = f"Rules read failed: {e}, falling back to default"
                logger.warning(msg)
                return DEFAULT_RULES.copy()

    def write_rules(self, data: Dict[str, Any]) -> None:
        """Write rules.json"""
        self._atomic_write_rules(data)

    def get_config_path(self) -> str:
        """Return config file path string"""
        return str(self.config_path.resolve())

    def get_rules_path(self) -> str:
        """Return rules file path string"""
        return str(self.rules_path.resolve())


# Global singleton instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get or create the global ConfigurationManager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def reset_config_manager() -> None:
    """Reset the global singleton (for testing)"""
    global _config_manager
    _config_manager = None
