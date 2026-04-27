"""History Snapshot Database Service with aiosqlite"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)

# Database schema
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    original_text TEXT NOT NULL,
    revised_text TEXT NOT NULL,
    rules_snapshot TEXT NOT NULL,
    config_snapshot TEXT NOT NULL,
    log_file_path TEXT,
    chunk_params TEXT
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
ON snapshots(timestamp DESC);
"""


class HistoryDatabase:
    """Async SQLite database for managing polish history snapshots"""

    def __init__(
        self,
        db_path: str = "./data/history.db",
        logs_dir: str = "./data/history/logs",
    ):
        self.db_path = Path(db_path)
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._max_snapshots: Optional[int] = None

    async def initialize(self) -> None:
        """Initialize database and create tables if needed"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_TABLE_SQL)
            await db.execute(CREATE_INDEX_SQL)
            await db.commit()
        logger.info(f"History database initialized at {self.db_path}")

    def set_max_snapshots(self, max_snapshots: int) -> None:
        """Set maximum number of snapshots to retain"""
        self._max_snapshots = max_snapshots

    async def insert_snapshot(
        self,
        original_text: str,
        revised_text: str,
        rules_snapshot: Dict[str, Any],
        config_snapshot: Dict[str, Any],
        chunk_params: Optional[Dict[str, Any]] = None,
        source_log_path: Optional[str] = None,
    ) -> int:
        """
        Insert a new snapshot and perform auto-cleanup if needed.
        Returns the ID of the inserted snapshot.
        """
        timestamp = datetime.now().isoformat()
        rules_json = json.dumps(rules_snapshot, ensure_ascii=False)
        config_json = json.dumps(config_snapshot, ensure_ascii=False)
        chunk_params_json = (
            json.dumps(chunk_params, ensure_ascii=False)
            if chunk_params
            else None
        )

        # Copy log file if provided
        log_file_path: Optional[str] = None
        MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB limit
        if source_log_path and os.path.exists(source_log_path):
            try:
                log_size = os.path.getsize(source_log_path)
                if log_size > MAX_LOG_SIZE:
                    logger.warning(f"Log file too large ({log_size / 1024 / 1024:.1f}MB), skipping copy")
                else:
                    log_filename = f"snapshot_{timestamp.replace(':', '-')}.log"
                    dest_path = self.logs_dir / log_filename
                    shutil.copy2(source_log_path, dest_path)
                    log_file_path = str(dest_path)
                    logger.debug(f"Log file copied to {log_file_path}")
            except Exception as e:
                logger.warning(f"Failed to copy log file: {e}")
                log_file_path = None

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO snapshots
                (timestamp, original_text, revised_text, rules_snapshot,
                 config_snapshot, log_file_path, chunk_params)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    original_text,
                    revised_text,
                    rules_json,
                    config_json,
                    log_file_path,
                    chunk_params_json,
                ),
            )
            await db.commit()
            snapshot_id = cursor.lastrowid

        logger.info(f"Snapshot {snapshot_id} inserted at {timestamp}")

        # Auto-cleanup if needed
        if self._max_snapshots:
            await self._cleanup_old_snapshots()

        return snapshot_id

    async def _cleanup_old_snapshots(self) -> None:
        """Delete oldest snapshots if count exceeds max_snapshots"""
        if not self._max_snapshots:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Count total snapshots
            cursor = await db.execute("SELECT COUNT(*) FROM snapshots")
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0

            if total_count <= self._max_snapshots:
                return

            # Get IDs of snapshots to delete (oldest first)
            excess = total_count - self._max_snapshots
            cursor = await db.execute(
                """
                SELECT id, log_file_path FROM snapshots
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (excess,),
            )
            to_delete = await cursor.fetchall()

        deleted_count = 0
        for snapshot_record in to_delete:
            snapshot_id = snapshot_record[0]
            log_path = snapshot_record[1]
            # Delete associated log file
            if log_path and os.path.exists(log_path):
                try:
                    os.remove(log_path)
                    logger.debug(f"Deleted log: {log_path}")
                except Exception:
                    pass

            # Delete snapshot record
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM snapshots WHERE id = ?",
                    (snapshot_id,),
                )
                await db.commit()

            deleted_count += 1

        logger.info(f"Auto-cleanup removed {deleted_count} old snapshots")

    async def get_all_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of all snapshots (newest first)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, timestamp, original_text, revised_text,
                       log_file_path, chunk_params
                FROM snapshots
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "original_text": row["original_text"],
                    "revised_text": row["revised_text"],
                    "log_file_path": row["log_file_path"],
                    "chunk_params": (
                        json.loads(row["chunk_params"])
                        if row["chunk_params"]
                        else None
                    ),
                }
            )
        return results

    async def get_snapshot_by_id(
        self, snapshot_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific snapshot by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, timestamp, original_text, revised_text,
                       rules_snapshot, config_snapshot,
                       log_file_path, chunk_params
                FROM snapshots
                WHERE id = ?
                """,
                (snapshot_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "original_text": row["original_text"],
            "revised_text": row["revised_text"],
            "rules_snapshot": json.loads(row["rules_snapshot"]),
            "config_snapshot": json.loads(row["config_snapshot"]),
            "log_file_path": row["log_file_path"],
            "chunk_params": (
                json.loads(row["chunk_params"])
                if row["chunk_params"]
                else None
            ),
        }

    async def delete_snapshot(self, snapshot_id: int) -> bool:
        """Delete a specific snapshot and its associated log file"""
        # First get the log file path
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT log_file_path FROM snapshots WHERE id = ?",
                (snapshot_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return False

        log_path = row["log_file_path"]
        if log_path and os.path.exists(log_path):
            try:
                os.remove(log_path)
            except Exception as e:
                logger.warning(f"Failed to delete log file: {e}")

        # Delete the snapshot record
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM snapshots WHERE id = ?",
                (snapshot_id,),
            )
            await db.commit()

        return True

    async def get_snapshot_count(self) -> int:
        """Get total number of snapshots"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM snapshots")
            row = await cursor.fetchone()
            return row[0] if row else 0


# Global singleton instance
_history_db: Optional[HistoryDatabase] = None


def get_history_db() -> HistoryDatabase:
    """Get or create the global HistoryDatabase singleton"""
    global _history_db
    if _history_db is None:
        _history_db = HistoryDatabase()
    return _history_db


async def init_history_db() -> HistoryDatabase:
    """Initialize and return the history database"""
    db = get_history_db()
    await db.initialize()
    return db
