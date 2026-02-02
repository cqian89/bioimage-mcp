from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from bioimage_mcp.config.schema import Config, StoragePolicy
from bioimage_mcp.storage.manager import StorageManager
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


@pytest.fixture
def config(tmp_path):
    root = tmp_path.absolute()
    return Config(
        artifact_store_root=root,
        tool_manifest_roots=[root / "tools"],
        storage=StoragePolicy(
            retention_days=7,
            quota_bytes=1000,
            trigger_fraction=0.9,
            target_fraction=0.7,
        ),
    )


def test_total_artifact_bytes_triggers(db_conn, config):
    manager = StorageManager(config, db_conn)

    # Initial state
    assert manager.get_total_bytes() == 0

    # Insert non-memory artifact
    db_conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "art1",
            "image",
            "file://test1",
            "tiff",
            "file",
            "image/tiff",
            100,
            "{}",
            "{}",
            "2026-01-01T00:00:00Z",
        ),
    )
    assert manager.get_total_bytes() == 100

    # Insert another non-memory artifact
    db_conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "art2",
            "image",
            "file://test2",
            "tiff",
            "file",
            "image/tiff",
            200,
            "{}",
            "{}",
            "2026-01-02T00:00:00Z",
        ),
    )
    assert manager.get_total_bytes() == 300

    # Insert memory artifact (should be excluded)
    db_conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "art3",
            "image",
            "memory://test3",
            "tiff",
            "memory",
            "image/tiff",
            500,
            "{}",
            "{}",
            "2026-01-03T00:00:00Z",
        ),
    )
    assert manager.get_total_bytes() == 300

    # Delete non-memory artifact
    db_conn.execute("DELETE FROM artifacts WHERE ref_id = 'art1'")
    assert manager.get_total_bytes() == 200

    # Delete memory artifact (should not change total)
    db_conn.execute("DELETE FROM artifacts WHERE ref_id = 'art3'")
    assert manager.get_total_bytes() == 200


def test_list_cleanup_candidates_ordering_and_exclusions(db_conn, config):
    manager = StorageManager(config, db_conn)
    now = datetime(2026, 2, 2, tzinfo=UTC)
    now_iso = now.isoformat()

    # Create sessions
    db_conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("active_sess", "2026-02-01T12:00:00Z", "2026-02-01T12:00:00Z", "active"),
    )
    db_conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("inactive_sess", "2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z", "closed"),
    )
    db_conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("recent_sess", "2026-02-02T10:00:00Z", "2026-02-02T10:00:00Z", "closed"),
    )

    # Insert artifacts
    artifacts = [
        # Old, eligible
        ("old1", "2026-01-01T00:00:00Z", 100, "inactive_sess", 0),
        ("old2", "2026-01-02T00:00:00Z", 100, None, 0),  # Orphaned
        # Old, pinned (excluded)
        ("pinned1", "2026-01-01T00:00:00Z", 100, "inactive_sess", 1),
        # Old, active session (excluded)
        ("active1", "2026-01-01T00:00:00Z", 100, "active_sess", 0),
        # Old, recent/protected session (excluded)
        ("recent1", "2026-01-01T00:00:00Z", 100, "recent_sess", 0),
        # New, not yet past retention (excluded by default retention check,
        # but might be included if cutoff moved)
        ("new1", "2026-02-01T00:00:00Z", 100, "inactive_sess", 0),
    ]

    for ref_id, created_at, size, sess_id, pinned in artifacts:
        db_conn.execute(
            """
            INSERT INTO artifacts (
                ref_id, type, uri, format, storage_type, mime_type, 
                size_bytes, checksums_json, metadata_json, created_at, 
                session_id, pinned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ref_id,
                "image",
                f"file://{ref_id}",
                "tiff",
                "file",
                "image/tiff",
                size,
                "{}",
                "{}",
                created_at,
                sess_id,
                pinned,
            ),
        )

    # Test standard retention cleanup (cutoff = now - 7 days = 2026-01-26)
    candidates = manager.list_cleanup_candidates(now_iso=now_iso)
    candidate_ids = [c["ref_id"] for c in candidates]

    assert "old1" in candidate_ids
    assert "old2" in candidate_ids
    assert "pinned1" not in candidate_ids
    assert "active1" not in candidate_ids
    assert "recent1" not in candidate_ids
    assert "new1" not in candidate_ids

    # Ordering check (old1 before old2)
    assert candidate_ids.index("old1") < candidate_ids.index("old2")

    # Test quota cleanup (move cutoff to future to include all eligible)
    future_cutoff = (now + timedelta(days=365)).isoformat()
    candidates_all = manager.list_cleanup_candidates(now_iso=future_cutoff)
    candidate_ids_all = [c["ref_id"] for c in candidates_all]

    assert "old1" in candidate_ids_all
    assert "old2" in candidate_ids_all
    assert "new1" in candidate_ids_all  # Now included because of future cutoff
    assert "pinned1" not in candidate_ids_all
    assert "active1" not in candidate_ids_all
    assert "recent1" not in candidate_ids_all
