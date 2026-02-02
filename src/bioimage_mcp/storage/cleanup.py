from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from bioimage_mcp.storage.manager import StorageManager

if TYPE_CHECKING:
    from bioimage_mcp.config.schema import Config

logger = logging.getLogger(__name__)


class CleanupSummary(TypedDict):
    reason: str
    dry_run: bool
    deleted_count: int
    freed_bytes: int
    before_bytes: int
    after_bytes: int
    notes: list[str]


def maybe_cleanup(
    config: Config,
    conn: sqlite3.Connection,
    *,
    reason: str = "periodic",
    force: bool = False,
) -> CleanupSummary | None:
    """Trigger cleanup if quota thresholds are met or retention is due."""
    manager = StorageManager(config, conn)
    now = datetime.now(UTC)

    # 1. Lock check
    row = conn.execute(
        "SELECT value FROM registry_state WHERE key = 'cleanup_lock_until'"
    ).fetchone()
    if row:
        try:
            lock_until = datetime.fromisoformat(row["value"])
            if now < lock_until and not force:
                return None
        except ValueError:
            pass

    # 2. Cooldown check
    if not force:
        row = conn.execute(
            "SELECT value FROM registry_state WHERE key = 'cleanup_last_run_at'"
        ).fetchone()
        if row:
            try:
                last_run = datetime.fromisoformat(row["value"])
                if now - last_run < timedelta(seconds=config.storage.cooldown_seconds):
                    return None
            except ValueError:
                pass

    # 3. Threshold check
    usage_fraction = manager.get_usage_fraction()
    should_run_quota = usage_fraction >= config.storage.trigger_fraction

    # We always run to check retention if enough time passed, but we might also trigger due to quota
    actual_reason = reason
    if should_run_quota:
        actual_reason = f"{reason}_quota"

    # Acquire lock
    lock_until_str = (now + timedelta(minutes=30)).isoformat()
    conn.execute(
        "INSERT INTO registry_state (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at",
        ("cleanup_lock_until", lock_until_str, now.isoformat()),
    )
    conn.commit()

    try:
        return run_cleanup(config, conn, reason=actual_reason, dry_run=False)
    finally:
        # Release lock
        conn.execute("DELETE FROM registry_state WHERE key = 'cleanup_lock_until'")
        conn.commit()


def run_cleanup(
    config: Config,
    conn: sqlite3.Connection,
    *,
    reason: str = "manual",
    dry_run: bool = False,
) -> CleanupSummary:
    """Execute cleanup logic (retention + quota) with safety skips."""
    start_time = datetime.now(UTC)
    manager = StorageManager(config, conn)
    before_bytes = manager.get_total_bytes()

    summary: CleanupSummary = {
        "reason": reason,
        "dry_run": dry_run,
        "deleted_count": 0,
        "freed_bytes": 0,
        "before_bytes": before_bytes,
        "after_bytes": before_bytes,
        "notes": [],
    }

    # 1. Selection: Candidates for retention
    # We use a large limit to catch all old artifacts
    candidates = manager.list_cleanup_candidates(limit=1000)

    # 2. Selection: Candidates for quota if needed
    quota_bytes = manager.get_quota_bytes()
    target_bytes = int(quota_bytes * config.storage.target_fraction)

    # If we are already over quota, or the retention cleanup didn't free enough,
    # we might need to be more aggressive.
    # But list_cleanup_candidates already filters for eligibility (pinned, active, etc.)
    # and returns them oldest first.

    # Actually, list_cleanup_candidates in manager.py filters by retention_days.
    # We need a way to get candidates for quota that might NOT be past retention_days
    # but are still eligible (not pinned, not active session).

    # I'll need to add a method to StorageManager or modify list_cleanup_candidates.
    # The plan says: "delete oldest eligible until total_bytes <= quota_bytes * target_fraction"

    # Let's see if I can use list_cleanup_candidates with a very far future cutoff for quota.

    # 3. Deletion Loop
    # We iterate through candidates. For each:
    # - Check if it exists on disk
    # - Rename to trash
    # - Delete from disk
    # - Delete from DB (which updates total_bytes via trigger)

    # We stop once we've processed all retention candidates AND total_bytes <= target_bytes
    # (if quota was the trigger)

    # Re-fetch candidates if quota is triggered and we need more
    current_bytes = before_bytes
    all_candidates = candidates

    # If total_bytes > trigger_fraction * quota, we need to reach target_fraction * quota
    is_quota_cleanup = current_bytes >= int(quota_bytes * config.storage.trigger_fraction)

    if is_quota_cleanup:
        # Get more candidates regardless of retention age
        # I'll use a very large cutoff to get all eligible artifacts
        future_cutoff = (datetime.now(UTC) + timedelta(days=365)).isoformat()
        all_candidates = manager.list_cleanup_candidates(now_iso=future_cutoff, limit=2000)

    for art in all_candidates:
        # Check if we should stop (only if this was a quota-driven cleanup and we reached target)
        if is_quota_cleanup and current_bytes <= target_bytes:
            # We still want to process artifacts past retention though
            art_created_at = datetime.fromisoformat(art["created_at"])
            retention_cutoff = datetime.now(UTC) - timedelta(days=config.storage.retention_days)
            if art_created_at > retention_cutoff:
                break

        # Process deletion
        uri = art["uri"]
        if not uri.startswith("file://"):
            summary["notes"].append(f"Skipping non-file URI: {uri}")
            continue

        path = Path(uri[7:])

        if not dry_run:
            if path.exists():
                try:
                    # Rename-to-trash
                    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
                    trash_path = path.with_suffix(f"{path.suffix}.deleted.{timestamp}")
                    path.rename(trash_path)

                    # Final delete
                    if trash_path.is_dir():
                        shutil.rmtree(trash_path)
                    else:
                        trash_path.unlink()
                except Exception as e:
                    summary["notes"].append(f"Error deleting {path}: {e}")
                    # If rename failed, we might still want to try deleting the DB row
                    # if the error suggests it's gone or inaccessible.
                    # But safer to skip for now.
                    continue
            else:
                summary["notes"].append(f"File missing on disk: {path}")

            # Delete from DB
            conn.execute("DELETE FROM artifacts WHERE ref_id = ?", (art["ref_id"],))
            # The trigger will update total_artifact_bytes in registry_state

        summary["deleted_count"] += 1
        summary["freed_bytes"] += art["size_bytes"]
        current_bytes -= art["size_bytes"]

    # Finalize
    if not dry_run:
        conn.commit()
        # Update last run state
        conn.execute(
            "INSERT INTO registry_state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at",
            ("cleanup_last_run_at", datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()),
        )
        conn.execute(
            "INSERT INTO registry_state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at",
            ("cleanup_last_run_reason", reason, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    summary["after_bytes"] = manager.get_total_bytes()

    # Log event
    end_time = datetime.now(UTC)
    conn.execute(
        """
        INSERT INTO cleanup_events (
            started_at, ended_at, reason, dry_run, deleted_count, 
            freed_bytes, before_bytes, after_bytes, notes_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            start_time.isoformat(),
            end_time.isoformat(),
            reason,
            1 if dry_run else 0,
            summary["deleted_count"],
            summary["freed_bytes"],
            summary["before_bytes"],
            summary["after_bytes"],
            json.dumps(summary["notes"]),
        ),
    )
    conn.commit()

    return summary
