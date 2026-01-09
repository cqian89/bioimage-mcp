from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from bioimage_mcp.sessions.models import Session
from bioimage_mcp.storage.models import (
    OrphanFile,
    PruneResult,
    QuotaCheckResult,
    SessionStorageInfo,
    StorageStatus,
)

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

    def pin_session(self, session_id: str) -> Session:
        """Mark a session as pinned to prevent it from being pruned.
        - Sets is_pinned = 1
        - Returns: Updated Session model
        - Raises: KeyError if session_id not found
        """
        cursor = self.conn.execute(
            "UPDATE sessions SET is_pinned = 1 WHERE session_id = ?", (session_id,)
        )
        if cursor.rowcount == 0:
            raise KeyError(f"Session {session_id} not found")
        self.conn.commit()

        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return Session(**dict(row))

    def unpin_session(self, session_id: str) -> Session:
        """Remove the pin from a session, allowing it to be pruned if expired.
        - Sets is_pinned = 0
        - Returns: Updated Session model
        - Raises: KeyError if session_id not found
        """
        cursor = self.conn.execute(
            "UPDATE sessions SET is_pinned = 0 WHERE session_id = ?", (session_id,)
        )
        if cursor.rowcount == 0:
            raise KeyError(f"Session {session_id} not found")
        self.conn.commit()

        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
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

    def get_status(self) -> StorageStatus:
        """Returns current storage usage breakdown.
        - Aggregates size_bytes from the artifacts table.
        - Groups by session state (active, completed, expired, pinned).
        - Scans the objects/ directory for orphan detection.
        """
        # 1. Total bytes used by artifacts
        row = self.conn.execute("SELECT SUM(size_bytes) FROM artifacts").fetchone()
        artifact_bytes = row[0] or 0

        # 2. Orphans
        orphans = self.find_orphans()
        orphan_bytes = sum(o.size_bytes for o in orphans)

        used_bytes = artifact_bytes + orphan_bytes
        total_capacity = self.storage_config.quota_bytes
        usage_percent = (used_bytes / total_capacity * 100) if total_capacity > 0 else 0.0

        # 3. Group by state
        by_state = {
            "active": SessionStorageInfo(session_count=0, artifact_count=0, total_bytes=0),
            "completed": SessionStorageInfo(session_count=0, artifact_count=0, total_bytes=0),
            "expired": SessionStorageInfo(session_count=0, artifact_count=0, total_bytes=0),
            "pinned": SessionStorageInfo(session_count=0, artifact_count=0, total_bytes=0),
        }

        # Query all sessions and their artifact stats
        query = """
            SELECT s.session_id, COUNT(a.ref_id) as art_count, SUM(a.size_bytes) as art_bytes
            FROM sessions s
            LEFT JOIN artifacts a ON s.session_id = a.session_id
            GROUP BY s.session_id
        """
        for row in self.conn.execute(query):
            session_id = row["session_id"]
            state = self.get_session_state(session_id)
            info = by_state[state]
            info.session_count += 1
            info.artifact_count += row["art_count"]
            info.total_bytes += row["art_bytes"] or 0

        return StorageStatus(
            total_bytes=total_capacity,
            used_bytes=used_bytes,
            usage_percent=usage_percent,
            by_state=by_state,
            orphan_bytes=orphan_bytes,
        )

    def get_session_size(self, session_id: str) -> int:
        """Get total bytes used by a specific session.
        - Aggregates size_bytes from artifacts where session_id = ?
        """
        row = self.conn.execute(
            "SELECT SUM(size_bytes) FROM artifacts WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row[0] or 0

    def check_quota(self) -> QuotaCheckResult:
        """Pre-run quota validation used by ExecutionService before starting runs.
        Returns: QuotaCheckResult with allowed: bool, usage_percent: float, message: str
        """
        # 1. Total bytes used by artifacts
        row = self.conn.execute("SELECT SUM(size_bytes) FROM artifacts").fetchone()
        artifact_bytes = row[0] or 0

        # 2. Orphans (Note: scanning directory can be slow, but needed for accuracy)
        orphans = self.find_orphans()
        orphan_bytes = sum(o.size_bytes for o in orphans)

        used_bytes = artifact_bytes + orphan_bytes
        total_capacity = self.storage_config.quota_bytes
        usage_percent = (used_bytes / total_capacity * 100) if total_capacity > 0 else 0.0

        quota_gb = total_capacity / (1024**3)

        if usage_percent >= self.storage_config.critical_threshold * 100:
            return QuotaCheckResult(
                allowed=False,
                usage_percent=usage_percent,
                used_bytes=used_bytes,
                message=(
                    f"CRITICAL: Storage quota exceeded ({usage_percent:.1f}% of {quota_gb:.1f}GB used). "
                    "Run 'bioimage-mcp storage prune' to reclaim space."
                ),
            )

        if usage_percent >= self.storage_config.warning_threshold * 100:
            return QuotaCheckResult(
                allowed=True,
                usage_percent=usage_percent,
                used_bytes=used_bytes,
                message=f"WARNING: Storage quota usage high ({usage_percent:.1f}% of {quota_gb:.1f}GB used).",
            )

        return QuotaCheckResult(
            allowed=True,
            usage_percent=usage_percent,
            used_bytes=used_bytes,
            message=f"Storage usage below warning threshold ({usage_percent:.1f}% used).",
        )

    def find_orphans(self) -> list[OrphanFile]:
        """Identify files in storage root not tracked in database.
        - Scans artifact_store_root/objects/
        - Compares against artifacts.uri
        """
        obj_dir = self.root / "objects"
        if not obj_dir.exists():
            return []

        # Get all tracked URIs
        tracked_uris = {row["uri"] for row in self.conn.execute("SELECT uri FROM artifacts")}

        orphans = []
        for file_path in obj_dir.rglob("*"):
            if file_path.is_file():
                # We expect URIs to be file://<abs_path>
                # ArtifactStore.save uses file:// + str(path.absolute())
                uri = f"file://{file_path.absolute()}"
                if uri not in tracked_uris:
                    orphans.append(OrphanFile(path=file_path, size_bytes=file_path.stat().st_size))

        return orphans

    def delete_orphans(self, orphans: list[OrphanFile]) -> int:
        """Delete specified orphan files. Returns count deleted."""
        deleted_count = 0
        for orphan in orphans:
            try:
                orphan.path.unlink()
                deleted_count += 1
            except Exception as e:
                logger.error("Failed to delete orphan file %s: %s", orphan.path, e)
        return deleted_count

    def prune(
        self,
        dry_run: bool = False,
        include_orphans: bool = True,
        older_than_days: int | None = None,
    ) -> PruneResult:
        """Delete expired sessions and orphaned files.
        - Identifies expired, non-pinned sessions
        - Deletes files first, then DB records
        - Returns PruneResult
        """
        sessions_to_delete = []
        now = datetime.now(UTC)

        query = "SELECT session_id FROM sessions WHERE is_pinned = 0"
        for row in self.conn.execute(query):
            sid = row["session_id"]
            state = self.get_session_state(sid)

            if state == "expired":
                sessions_to_delete.append(sid)
            elif older_than_days is not None:
                # Re-evaluate if it should be expired based on older_than_days
                s_row = self.conn.execute(
                    "SELECT completed_at FROM sessions WHERE session_id = ?", (sid,)
                ).fetchone()
                if s_row["completed_at"]:
                    comp_at = datetime.fromisoformat(s_row["completed_at"])
                    if comp_at.tzinfo is None:
                        comp_at = comp_at.replace(tzinfo=UTC)
                    if now - comp_at > timedelta(days=older_than_days):
                        if sid not in sessions_to_delete:
                            sessions_to_delete.append(sid)

        res = PruneResult(
            sessions_deleted=0,
            artifacts_deleted=0,
            bytes_reclaimed=0,
            orphan_files_deleted=0,
            errors=[],
        )

        # Deletion Phase: File-First, DB-Second
        for sid in sessions_to_delete:
            artifacts = self.conn.execute(
                "SELECT ref_id, uri, size_bytes FROM artifacts WHERE session_id = ?", (sid,)
            ).fetchall()

            art_deleted = 0
            bytes_rec = 0
            for art in artifacts:
                uri = art["uri"]
                if uri.startswith("file://"):
                    path = Path(uri[7:])
                    if not dry_run:
                        try:
                            if path.exists():
                                path.unlink()
                            art_deleted += 1
                            bytes_rec += art["size_bytes"]
                        except Exception as e:
                            res.errors.append(f"Failed to delete artifact {art['ref_id']}: {e}")
                    else:
                        art_deleted += 1
                        bytes_rec += art["size_bytes"]
                else:
                    # Non-file artifacts (e.g. obj://) - just account for them
                    art_deleted += 1
                    bytes_rec += art["size_bytes"]

            if not dry_run:
                try:
                    self.conn.execute("DELETE FROM artifacts WHERE session_id = ?", (sid,))
                    self.conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
                    self.conn.commit()
                    res.sessions_deleted += 1
                    res.artifacts_deleted += art_deleted
                    res.bytes_reclaimed += bytes_rec
                except Exception as e:
                    res.errors.append(f"Failed to delete session {sid} from DB: {e}")
            else:
                res.sessions_deleted += 1
                res.artifacts_deleted += art_deleted
                res.bytes_reclaimed += bytes_rec

        if include_orphans:
            orphans = self.find_orphans()
            res.orphan_files_deleted = len(orphans)
            if not dry_run:
                deleted = self.delete_orphans(orphans)
                # We already counted them as to be deleted, but if we want to be precise:
                # res.orphan_files_deleted = deleted

        return res
