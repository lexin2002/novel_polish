"""Tests for History Database"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from app.core.history_db import HistoryDatabase, get_history_db, init_history_db


@pytest.fixture
async def temp_history_db(tmp_path):
    """Create a temporary history database for testing"""
    db_path = tmp_path / "test_history.db"
    logs_dir = tmp_path / "logs"
    db = HistoryDatabase(db_path=str(db_path), logs_dir=str(logs_dir))
    await db.initialize()
    db.set_max_snapshots(20)
    yield db


@pytest.fixture
def sample_snapshot_data():
    """Sample snapshot data for testing"""
    return {
        "original_text": "这是原始文本",
        "revised_text": "这是修改后的文本",
        "rules_snapshot": {
            "main_categories": [
                {
                    "name": "语法",
                    "priority": "P0",
                    "is_active": True,
                    "sub_categories": [],
                }
            ]
        },
        "config_snapshot": {"llm": {"model": "gpt-4o"}, "engine": {"chunk_size": 1000}},
        "chunk_params": {"chunk_size": 1000, "total_chunks": 3},
    }


class TestHistoryDatabase:
    """Test HistoryDatabase basic operations"""

    @pytest.mark.asyncio
    async def test_initialize_creates_table(self, temp_history_db):
        """Test database initialization creates the snapshots table"""
        db = temp_history_db
        # The table should exist, try a simple query
        count = await db.get_snapshot_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_insert_snapshot_returns_id(
        self, temp_history_db, sample_snapshot_data
    ):
        """Test inserting a snapshot returns the correct ID"""
        db = temp_history_db
        snapshot_id = await db.insert_snapshot(**sample_snapshot_data)
        assert snapshot_id == 1

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_snapshot(
        self, temp_history_db, sample_snapshot_data
    ):
        """Test inserting and retrieving a snapshot"""
        db = temp_history_db
        inserted_id = await db.insert_snapshot(**sample_snapshot_data)

        snapshot = await db.get_snapshot_by_id(inserted_id)
        assert snapshot is not None
        assert snapshot["original_text"] == sample_snapshot_data["original_text"]
        assert snapshot["revised_text"] == sample_snapshot_data["revised_text"]
        assert snapshot["rules_snapshot"] == sample_snapshot_data["rules_snapshot"]

    @pytest.mark.asyncio
    async def test_get_all_snapshots_returns_newest_first(
        self, temp_history_db, sample_snapshot_data
    ):
        """Test that get_all_snapshots returns records in descending timestamp order"""
        db = temp_history_db

        # Insert multiple snapshots
        for i in range(3):
            data = sample_snapshot_data.copy()
            data["original_text"] = f"Original {i}"
            await db.insert_snapshot(**data)

        snapshots = await db.get_all_snapshots()
        assert len(snapshots) == 3
        # Newest first
        assert snapshots[0]["original_text"] == "Original 2"
        assert snapshots[2]["original_text"] == "Original 0"

    @pytest.mark.asyncio
    async def test_delete_snapshot(self, temp_history_db, sample_snapshot_data):
        """Test deleting a snapshot"""
        db = temp_history_db
        inserted_id = await db.insert_snapshot(**sample_snapshot_data)

        # Verify it exists
        snapshot = await db.get_snapshot_by_id(inserted_id)
        assert snapshot is not None

        # Delete it
        success = await db.delete_snapshot(inserted_id)
        assert success is True

        # Verify it's gone
        snapshot = await db.get_snapshot_by_id(inserted_id)
        assert snapshot is None

    @pytest.mark.asyncio
    async def test_snapshot_count(self, temp_history_db, sample_snapshot_data):
        """Test getting snapshot count"""
        db = temp_history_db
        assert await db.get_snapshot_count() == 0

        await db.insert_snapshot(**sample_snapshot_data)
        assert await db.get_snapshot_count() == 1

        await db.insert_snapshot(**sample_snapshot_data)
        assert await db.get_snapshot_count() == 2


class TestAutoCleanup:
    """Test auto-cleanup functionality"""

    @pytest.mark.asyncio
    async def test_auto_cleanup_removes_old_snapshots(
        self, tmp_path, sample_snapshot_data
    ):
        """Test that auto-cleanup removes old snapshots when exceeding max"""
        db_path = tmp_path / "test_history.db"
        logs_dir = tmp_path / "logs"
        db = HistoryDatabase(db_path=str(db_path), logs_dir=str(logs_dir))
        await db.initialize()
        db.set_max_snapshots(20)

        # Insert 25 snapshots
        for i in range(25):
            await db.insert_snapshot(**sample_snapshot_data)

        # Should only have 20
        count = await db.get_snapshot_count()
        assert count == 20

    @pytest.mark.asyncio
    async def test_auto_cleanup_deletes_associated_logs(
        self, tmp_path, sample_snapshot_data
    ):
        """Test that auto-cleanup also deletes associated log files"""
        db_path = tmp_path / "test_history.db"
        logs_dir = tmp_path / "logs"
        db = HistoryDatabase(db_path=str(db_path), logs_dir=str(logs_dir))
        await db.initialize()
        db.set_max_snapshots(20)

        # Create a mock log file that will be copied
        log_source = tmp_path / "source.log"
        log_source.write_text("Test log content")

        # Insert 25 snapshots with the log file
        for i in range(25):
            await db.insert_snapshot(
                **sample_snapshot_data, source_log_path=str(log_source)
            )

        # Count remaining log files in history/logs/
        log_files = list(logs_dir.glob("snapshot_*.log"))
        assert len(log_files) == 20

    @pytest.mark.asyncio
    async def test_cleanup_respects_max_snapshots_setting(
        self, tmp_path, sample_snapshot_data
    ):
        """Test that cleanup respects the max_snapshots setting"""
        db_path = tmp_path / "test_history.db"
        logs_dir = tmp_path / "logs"
        db = HistoryDatabase(db_path=str(db_path), logs_dir=str(logs_dir))
        await db.initialize()
        db.set_max_snapshots(10)

        # Insert 15 snapshots
        for i in range(15):
            await db.insert_snapshot(**sample_snapshot_data)

        # Should only have 10
        count = await db.get_snapshot_count()
        assert count == 10


class TestHistoryAPI:
    """Test REST API integration for history endpoints"""

    @pytest.mark.asyncio
    async def test_get_history_via_api(self):
        """Test GET /api/history endpoint"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        # Need to initialize the history db first
        from app.core.history_db import get_history_db

        history_db = get_history_db()
        await history_db.initialize()
        history_db.set_max_snapshots(20)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/history")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_history_count_via_api(self):
        """Test GET /api/history/count endpoint"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        from app.core.history_db import get_history_db

        history_db = get_history_db()
        await history_db.initialize()
        history_db.set_max_snapshots(20)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/history/count")
            assert response.status_code == 200
            data = response.json()
            assert "count" in data

    @pytest.mark.asyncio
    async def test_get_history_detail_via_api(self):
        """Test GET /api/history/{id} endpoint"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        from app.core.history_db import get_history_db

        history_db = get_history_db()
        await history_db.initialize()
        history_db.set_max_snapshots(20)

        # First insert a snapshot
        snapshot_data = {
            "original_text": "Test",
            "revised_text": "Test revised",
            "rules_snapshot": {"main_categories": []},
            "config_snapshot": {},
        }
        inserted_id = await history_db.insert_snapshot(**snapshot_data)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/history/{inserted_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["original_text"] == "Test"

    @pytest.mark.asyncio
    async def test_get_history_detail_not_found(self):
        """Test GET /api/history/{id} returns 404 for non-existent ID"""
        from httpx import AsyncClient, ASGITransport

        from app.main import app

        from app.core.history_db import get_history_db

        history_db = get_history_db()
        await history_db.initialize()
        history_db.set_max_snapshots(20)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/history/99999")
            assert response.status_code == 404
