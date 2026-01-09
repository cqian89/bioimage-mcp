from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from bioimage_mcp.sessions.models import Session

if TYPE_CHECKING:
    from bioimage_mcp.config.schema import Config

logger = logging.getLogger(__name__)


class StorageService:
    """Service for artifact storage management, retention, and quota enforcement."""

    def __init__(self, config: Config, conn: sqlite3.Connection) -> None:
        self.config = config
        self.conn = conn
        self.storage_config = config.storage
        self.root = config.artifact_store_root
        logger.debug("StorageService initialized with root: %s", self.root)

    def complete_session(self, session_id: str) -> Session:
        """Mark a session as completed.

        Fetches the session after it has been marked as completed.
        """
        # Fetch updated session
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Session {session_id} not found")

        return Session(**dict(row))

    def get_session_state(self, session_id: str) -> str:
        """Determine the current state of a session based on activity and retention.

        States:
        - active: Recently active and not completed
        - pinned: Explicitly pinned to prevent cleanup
        - completed: Manually or automatically completed, within retention period
        - expired: Either idle past TTL or completed past retention period
        """
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Session {session_id} not found")

        session = Session(**dict(row))

        if session.is_pinned:
            return "pinned"

        now = datetime.now(UTC)

        if session.completed_at is None:
            # Check idle timeout
            last_activity = datetime.fromisoformat(session.last_activity_at)
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=UTC)

            ttl_delta = timedelta(hours=self.config.session_ttl_hours)
            if now - last_activity > ttl_delta:
                return "expired"
            return "active"
        else:
            # Check retention period
            completed_at = datetime.fromisoformat(session.completed_at)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=UTC)

            retention_delta = timedelta(days=self.config.storage.retention_days)
            if now - completed_at > retention_delta:
                return "expired"
            return "completed"
