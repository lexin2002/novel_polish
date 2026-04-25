"""Configuration Manager - Atomic file persistence with FileLock"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import filelock
import json5

logger = logging.getLogger(__name__)

# Default configuration structure
DEFAULT_CONFIG: Dict[str, Any] = {
    "priority_order": ["P0", "P1", "P2", "P3"],
    "llm": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.4,
        "max_tokens": 4096,
        "safety_exempt_enabled": True,
        "xml_tag_isolation_enabled": True,
        "desensitize_mode": False,
    },
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

    def __init__(self, data_dir: str = "./data"):
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
        """Read config.jsonc with fallback to default on error"""
        with filelock.FileLock(self.config_lock_path, timeout=10):
            try:
                if not self.config_path.exists():
                    return DEFAULT_CONFIG.copy()

                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json5.load(f)

                logger.debug("Config read successfully")
                return data
            except Exception as e:
                logger.warning(
                    f"Config read failed: {e}, falling back to default"
                )
                return DEFAULT_CONFIG.copy()

    def write_config(self, data: Dict[str, Any]) -> None:
        """Write config.jsonc with validation"""
        # Validate required keys
        for key in DEFAULT_CONFIG:
            if key not in data:
                logger.warning(f"Missing key '{key}' in config, using default")
                data[key] = DEFAULT_CONFIG[key]

        self._atomic_write_config(data)

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
                logger.warning(
                    f"Rules read failed: {e}, falling back to default"
                )
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
