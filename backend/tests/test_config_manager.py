"""Tests for Configuration Manager"""

import json5
import os
import tempfile
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from app.core.config_manager import (
    ConfigurationManager,
    DEFAULT_CONFIG,
    DEFAULT_RULES,
    get_config_manager,
    reset_config_manager,
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def config_manager(temp_data_dir):
    """Create a ConfigurationManager with temp directory"""
    manager = ConfigurationManager(data_dir=temp_data_dir)
    yield manager
    # Cleanup
    for f in Path(temp_data_dir).iterdir():
        if f.is_file():
            f.unlink()


class TestConfigurationManager:
    """Test basic ConfigurationManager operations"""

    def test_config_initializes_with_defaults(self, config_manager):
        """Test that config initializes with default values"""
        config = config_manager.read_config()
        assert config["priority_order"] == ["P0", "P1", "P2", "P3"]
        assert "llm" in config
        assert "engine" in config

    def test_rules_initializes_with_defaults(self, config_manager):
        """Test that rules initializes with default values"""
        rules = config_manager.read_rules()
        assert "main_categories" in rules
        assert len(rules["main_categories"]) > 0

    def test_write_and_read_config_roundtrip(self, config_manager):
        """Test config write and read are consistent"""
        new_config = DEFAULT_CONFIG.copy()
        new_config["llm"]["model"] = "gpt-4o-mini"

        config_manager.write_config(new_config)
        read_config = config_manager.read_config()

        assert read_config["llm"]["model"] == "gpt-4o-mini"

    def test_write_and_read_rules_roundtrip(self, config_manager):
        """Test rules write and read are consistent"""
        new_rules = DEFAULT_RULES.copy()
        new_rules["main_categories"].append(
            {
                "name": "测试类别",
                "priority": "P2",
                "is_active": True,
                "sub_categories": [],
            }
        )

        config_manager.write_rules(new_rules)
        read_rules = config_manager.read_rules()

        assert len(read_rules["main_categories"]) == len(new_rules["main_categories"])

    def test_patch_config_nested(self, config_manager):
        """Test patching nested config values"""
        patch = {
            "llm": {
                "model": "claude-3-sonnet",
                "temperature": 0.7,
            }
        }

        result = config_manager.patch_config(patch)
        assert result["llm"]["model"] == "claude-3-sonnet"
        assert result["llm"]["temperature"] == 0.7
        # Original keys should be preserved
        assert result["llm"]["api_key"] == DEFAULT_CONFIG["llm"]["api_key"]

    def test_patch_config_preserves_other_sections(self, config_manager):
        """Test that patching one section doesn't affect others"""
        original_engine = config_manager.read_config()["engine"].copy()

        patch = {"llm": {"model": "test-model"}}
        result = config_manager.patch_config(patch)

        # Engine section should be unchanged
        assert result["engine"] == original_engine


class TestAtomicWrites:
    """Test atomic write behavior"""

    def test_write_creates_atomic_replacement(self, temp_data_dir):
        """Test that writes use atomic os.replace"""
        manager = ConfigurationManager(data_dir=temp_data_dir)

        # Write some data
        test_config = DEFAULT_CONFIG.copy()
        test_config["llm"]["model"] = "pre-write-model"
        manager.write_config(test_config)

        # Verify file exists
        config_path = Path(temp_data_dir) / "config.jsonc"
        assert config_path.exists()

        # Write new data
        test_config["llm"]["model"] = "post-write-model"
        manager.write_config(test_config)

        # Read back and verify
        with open(config_path, "r", encoding="utf-8") as f:
            data = json5.load(f)
        assert data["llm"]["model"] == "post-write-model"

    def test_corrupted_config_falls_back_to_default(self, temp_data_dir):
        """Test that corrupted config file falls back to default"""
        manager = ConfigurationManager(data_dir=temp_data_dir)

        # Corrupt the file
        config_path = Path(temp_data_dir) / "config.jsonc"
        with open(config_path, "w") as f:
            f.write("{ invalid json }")

        # Read should return default
        result = manager.read_config()
        assert result == DEFAULT_CONFIG


class TestConcurrentAccess:
    """Test concurrent access with FileLock"""

    def test_concurrent_reads_are_thread_safe(self, config_manager):
        """Test that concurrent reads don't cause issues"""
        num_threads = 50
        results = []

        def read_config():
            result = config_manager.read_config()
            results.append(result)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(read_config) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        # All reads should return valid config
        assert len(results) == num_threads
        for result in results:
            assert result is not None
            assert "llm" in result

    def test_concurrent_writes_are_atomic(self, temp_data_dir):
        """Test that concurrent writes are atomic and don't corrupt file"""
        manager = ConfigurationManager(data_dir=temp_data_dir)

        num_threads = 50
        unique_model = f"model-thread-{{}}"

        def write_config(thread_id):
            # Each thread writes with a unique model name
            patch = {
                "llm": {
                    "model": unique_model.format(thread_id),
                    "temperature": thread_id / 100.0,
                }
            }
            manager.patch_config(patch)
            return thread_id

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_config, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        # After all writes, file should be valid JSON (not corrupted)
        config_path = Path(temp_data_dir) / "config.jsonc"
        with open(config_path, "r", encoding="utf-8") as f:
            data = json5.load(f)

        # Should be valid config structure
        assert "llm" in data
        assert "model" in data["llm"]
        assert "temperature" in data["llm"]

        # Should have one of the written values
        model_value = data["llm"]["model"]
        assert model_value.startswith("model-thread-")

    def test_concurrent_reads_and_writes(self, temp_data_dir):
        """Test mixed concurrent reads and writes"""
        manager = ConfigurationManager(data_dir=temp_data_dir)

        num_readers = 30
        num_writers = 20
        total_ops = num_readers + num_writers
        errors = []

        def do_read():
            try:
                result = manager.read_config()
                assert result is not None
            except Exception as e:
                errors.append(("read", e))

        def do_write(thread_id):
            try:
                manager.patch_config({"engine": {"max_workers": thread_id}})
            except Exception as e:
                errors.append(("write", e))

        with ThreadPoolExecutor(max_workers=total_ops) as executor:
            futures = []
            for i in range(num_writers):
                futures.append(executor.submit(do_write, i))
            for _ in range(num_readers):
                futures.append(executor.submit(do_read))

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    errors.append(("future", e))

        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # File should still be valid JSON
        config_path = Path(temp_data_dir) / "config.jsonc"
        with open(config_path, "r", encoding="utf-8") as f:
            data = json5.load(f)
        assert "engine" in data


class TestConfigAPI:
    """Test REST API integration"""

    @pytest.mark.asyncio
    async def test_get_config_via_api(self):
        """Test GET /api/config endpoint"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/config")
            assert response.status_code == 200
            data = response.json()
            assert "llm" in data

    @pytest.mark.asyncio
    async def test_patch_config_via_api(self):
        """Test PATCH /api/config endpoint"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            patch_data = {"llm": {"model": "api-test-model"}}
            response = await client.patch("/api/config", json=patch_data)
            assert response.status_code == 200
            result = response.json()
            assert result["llm"]["model"] == "api-test-model"

    @pytest.mark.asyncio
    async def test_get_rules_via_api(self):
        """Test GET /api/rules endpoint"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/rules")
            assert response.status_code == 200
            data = response.json()
            assert "main_categories" in data

    @pytest.mark.asyncio
    async def test_post_rules_via_api(self):
        """Test POST /api/rules endpoint"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            new_rules = DEFAULT_RULES.copy()
            new_rules["main_categories"] = []
            response = await client.post("/api/rules", json=new_rules)
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "ok"
