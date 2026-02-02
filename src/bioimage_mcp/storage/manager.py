from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioimage_mcp.config.schema import Config


class StorageManager:
    """Decision layer for storage retention and quota management."""

    def __init__(self, config: Config, conn: sqlite3.Connection):
        self._config = config
        self._conn = conn

    def get_total_bytes(self) -> int:
        """Get total bytes used by non-memory artifacts."""
        row = self._conn.execute(
            "SELECT value FROM registry_state WHERE key = 'total_artifact_bytes'"
        ).fetchone()
        if row:
            try:
                return int(row["value"])
            except ValueError:
                pass

        # Fallback/Repair
        row = self._conn.execute(
            "SELECT SUM(size_bytes) as total FROM artifacts WHERE storage_type != 'memory'"
        ).fetchone()
        total = row["total"] or 0

        # Store repaired value
        self._conn.execute(
            "INSERT INTO registry_state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET "
            "value = EXCLUDED.value, updated_at = EXCLUDED.updated_at",
            ("total_artifact_bytes", str(total), datetime.now(UTC).isoformat()),
        )
        self._conn.commit()
        return total

    def get_quota_bytes(self) -> int:
        """Get the configured quota limit in bytes."""
        return self._config.storage.quota_bytes

    def get_usage_fraction(self) -> float:
        """Get current usage as a fraction of quota (0.0 to 1.0+)."""
        quota = self.get_quota_bytes()
        if quota <= 0:
            return 0.0
        return self.get_total_bytes() / quota

    def get_protected_session_ids(self) -> set[str]:
        """Get IDs of sessions protected from cleanup by policy."""
        count = self._config.storage.protect_recent_sessions
        rows = self._conn.execute(
            "SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT ?",
            (count,),
        ).fetchall()
        return {row["session_id"] for row in rows}

    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is currently active."""
        row = self._conn.execute(
            "SELECT status FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row is not None and row["status"] == "active"

    def list_cleanup_candidates(
        self, now_iso: str | None = None, *, limit: int = 100
    ) -> list[dict]:
        """Select artifacts eligible for deletion based on retention rules."""
        if now_iso is None:
            now_iso = datetime.now(UTC).isoformat()

        now = datetime.fromisoformat(now_iso)
        retention_days = self._config.storage.retention_days
        cutoff = (now - timedelta(days=retention_days)).isoformat()

        protected_session_ids = self.get_protected_session_ids()

        # Query for candidates:
        # - created_at < cutoff
        # - pinned == 0
        # - storage_type != 'memory'
        # - session_id NOT IN protected_session_ids
        # - session_id NOT IN active sessions (status == 'active')

        # We need to handle session_id being NULL as well (orphaned artifacts)
        # Orphaned artifacts are NOT protected by active/recent session checks

        query = """
            SELECT a.ref_id, a.uri, a.size_bytes, a.created_at, a.storage_type, a.session_id
            FROM artifacts a
            LEFT JOIN sessions s ON a.session_id = s.session_id
            WHERE a.created_at < ?
              AND a.pinned = 0
              AND a.storage_type != 'memory'
              AND (a.session_id IS NULL OR (
                  a.session_id NOT IN ({protected_placeholders})
                  AND (s.status IS NULL OR s.status != 'active')
              ))
            ORDER BY a.created_at ASC
            LIMIT ?
        """

        placeholders = ", ".join(["?"] * len(protected_session_ids))
        # If no protected sessions, the NOT IN (...) will be empty which is problematic in SQL
        if not protected_session_ids:
            query = query.replace("a.session_id NOT IN ({protected_placeholders})", "1=1")
            params = [cutoff, limit]
        else:
            query = query.format(protected_placeholders=placeholders)
            params = [cutoff, *list(protected_session_ids), limit]

        rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
