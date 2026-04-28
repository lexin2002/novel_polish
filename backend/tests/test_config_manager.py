"""Tests for ConfigurationManager"""

import copy
from pathlib import Path

import pytest

from app.core.config_manager import (
    ConfigurationManager,
    DEFAULT_CONFIG,
    DEFAULT_RULES,
    FileLockError,
    LLM_PROVIDERS,
)


class TestConfigManagerBasics:
    """Basic ConfigurationManager functionality"""

    def test_init_creates_directory(self, temp_data_dir: Path):
        """ConfigManager should create the data directory if it doesn't exist"""
        new_dir = temp_data_dir / "subdir" / "nested"
        assert not new_dir.exists()
        cm = ConfigurationManager(data_dir=str(new_dir))
        assert new_dir.exists()
        assert cm.config_path.exists()
        assert cm.rules_path.exists()

    def test_default_config_values(self, config_manager: ConfigurationManager):
        """Default config should have all required sections"""
        config = config_manager.read_config()
        assert "llm" in config
        assert "engine" in config
        assert "network" in config
        assert "ui" in config
        assert "history" in config
        assert "priority_order" in config
        assert config["priority_order"] == ["P0", "P1", "P2", "P3"]

    def test_default_config_llm_providers(self, config_manager: ConfigurationManager):
        """Default LLM config should have all providers"""
        config = config_manager.read_config()
        providers = config["llm"]["providers"]
        for provider_id in LLM_PROVIDERS:
            assert provider_id in providers, f"Missing provider: {provider_id}"
            assert providers[provider_id]["name"] != ""

    def test_default_rules_structure(self, config_manager: ConfigurationManager):
        """Default rules should have at least one main_category"""
        rules = config_manager.read_rules()
        assert "main_categories" in rules
        assert len(rules["main_categories"]) > 0
        assert rules["main_categories"][0]["name"] == "语法与标点"


class TestConfigCRUD:
    """Config create, read, update, delete operations"""

    def test_read_returns_default_when_file_missing(self, temp_data_dir: Path):
        """Reading non-existent config should return defaults"""
        cm = ConfigurationManager(data_dir=str(temp_data_dir))
        config = cm.read_config()
        assert config["engine"]["chunk_size"] == 1000

    def test_write_and_read_config(self, config_manager: ConfigurationManager):
        """After writing config, read should return the same values"""
        config = config_manager.read_config()
        config["engine"]["chunk_size"] = 2000
        config_manager.write_config(config)

        reread = config_manager.read_config()
        assert reread["engine"]["chunk_size"] == 2000
        assert reread["llm"]["active_provider"] == "openai"

    def test_patch_config_single_field(self, config_manager: ConfigurationManager):
        """Patching a single field should preserve other fields"""
        config_manager.patch_config({"engine": {"chunk_size": 1500}})
        config = config_manager.read_config()
        assert config["engine"]["chunk_size"] == 1500
        assert config["engine"]["max_workers"] == 3  # unchanged

    def test_patch_config_nested(self, config_manager: ConfigurationManager):
        """Patching nested fields should deep merge"""
        config_manager.patch_config({
            "llm": {
                "temperature": 0.7,
                "providers": {
                    "openai": {"active_model": "gpt-4-turbo"}
                }
            }
        })
        config = config_manager.read_config()
        assert config["llm"]["temperature"] == 0.7
        assert config["llm"]["providers"]["openai"]["active_model"] == "gpt-4-turbo"
        # Other providers unchanged
        assert config["llm"]["providers"]["anthropic"]["active_model"] == "claude-3-5-sonnet-latest"

    def test_reset_config_to_defaults(self, config_manager: ConfigurationManager):
        """Reset should restore default values"""
        config_manager.patch_config({"engine": {"chunk_size": 9999}})
        config_manager.write_config(DEFAULT_CONFIG)
        config = config_manager.read_config()
        assert config["engine"]["chunk_size"] == 1000

    def test_get_config_path(self, config_manager: ConfigurationManager, temp_data_dir: Path):
        """get_config_path should return the full path"""
        path = config_manager.get_config_path()
        assert path.endswith("config.jsonc")
        assert str(temp_data_dir) in path

    def test_get_rules_path(self, config_manager: ConfigurationManager, temp_data_dir: Path):
        """get_rules_path should return the full path"""
        path = config_manager.get_rules_path()
        assert path.endswith("rules.json")
        assert str(temp_data_dir) in path


class TestRulesCRUD:
    """Rules create, read, update operations"""

    def test_write_and_read_rules(self, config_manager: ConfigurationManager, sample_rules):
        """After writing rules, read should return the same data"""
        config_manager.write_rules(sample_rules)
        rules = config_manager.read_rules()
        assert rules["main_categories"][0]["name"] == sample_rules["main_categories"][0]["name"]

    def test_rules_integrity(self, config_manager: ConfigurationManager):
        """Rules should maintain 3-level nesting structure"""
        from app.core.config_manager import DEFAULT_RULES
        config_manager.write_rules(DEFAULT_RULES)
        rules = config_manager.read_rules()
        for cat in rules["main_categories"]:
            assert "name" in cat
            assert "priority" in cat
            assert "is_active" in cat
            assert "sub_categories" in cat
            for sub in cat["sub_categories"]:
                assert "name" in sub
                assert "priority" in sub
                assert "rules" in sub
                for rule in sub["rules"]:
                    assert "name" in rule
                    assert "is_active" in rule
                    assert "instruction" in rule

    def test_empty_rules(self, config_manager: ConfigurationManager):
        """Writing empty rules should be valid"""
        config_manager.write_rules({"main_categories": []})
        rules = config_manager.read_rules()
        assert rules["main_categories"] == []


class TestLLMMigration:
    """LLM config migration tests"""

    def test_old_format_migration(self, temp_data_dir: Path):
        """Old flat llm config should be migrated to provider format"""
        cm = ConfigurationManager(data_dir=str(temp_data_dir))
        old_config = {
            "llm": {
                "provider": "openai",
                "api_key": "sk-test",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "temperature": 0.5,
                "max_tokens": 2048,
            }
        }
        cm.write_config(old_config)
        config = cm.read_config()
        llm = config["llm"]
        # Should be migrated to provider format
        assert "providers" in llm
        assert llm["active_provider"] == "openai"
        assert llm["providers"]["openai"]["api_key"] == "sk-test"
        assert llm["temperature"] == 0.5

    def test_missing_providers_filled(self, config_manager: ConfigurationManager):
        """Missing provider slots should be auto-filled"""
        config = config_manager.read_config()
        # Remove a provider to simulate partial data
        llm = config["llm"]
        if "deepseek" in llm["providers"]:
            del llm["providers"]["deepseek"]
        config_manager.write_config(config)
        reread = config_manager.read_config()
        assert "deepseek" in reread["llm"]["providers"]
