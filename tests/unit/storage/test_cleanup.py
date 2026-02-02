from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.storage.cleanup import maybe_cleanup, run_cleanup
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock()
    config.artifact_store_root = tmp_path / "artifacts"
    config.artifact_store_root.mkdir()

    config.storage.retention_days = 1
    config.storage.quota_bytes = 1000
    config.storage.trigger_fraction = 1.0
    config.storage.target_fraction = 0.5
    config.storage.cooldown_seconds = 0
    config.storage.protect_recent_sessions = 0

    return config


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def test_cleanup_retention(mock_config, conn):
    # Create an old artifact
    old_time = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    art_path = mock_config.artifact_store_root / "old.txt"
    art_path.write_text("old content")

    conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "old-1",
            "file",
            f"file://{art_path}",
            "txt",
            "file",
            "text/plain",
            11,
            "{}",
            "{}",
            old_time,
        ),
    )
    conn.commit()

    # Create a new artifact
    new_time = datetime.now(UTC).isoformat()
    new_path = mock_config.artifact_store_root / "new.txt"
    new_path.write_text("new content")

    conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "new-1",
            "file",
            f"file://{new_path}",
            "txt",
            "file",
            "text/plain",
            11,
            "{}",
            "{}",
            new_time,
        ),
    )
    conn.commit()

    summary = run_cleanup(mock_config, conn, reason="test")

    assert summary["deleted_count"] == 1
    assert not art_path.exists()
    assert new_path.exists()

    # Check event log
    row = conn.execute("SELECT * FROM cleanup_events").fetchone()
    assert row["deleted_count"] == 1
    assert row["reason"] == "test"


def test_cleanup_quota(mock_config, conn):
    # Set quota to 15 bytes
    mock_config.storage.quota_bytes = 15
    mock_config.storage.trigger_fraction = 1.0
    mock_config.storage.target_fraction = 0.5  # target 7 bytes

    # Create two artifacts, total 20 bytes
    time1 = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    path1 = mock_config.artifact_store_root / "1.txt"
    path1.write_text("1234567890")  # 10 bytes

    conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("id-1", "file", f"file://{path1}", "txt", "file", "text/plain", 10, "{}", "{}", time1),
    )

    time2 = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    path2 = mock_config.artifact_store_root / "2.txt"
    path2.write_text("1234567890")  # 10 bytes

    conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("id-2", "file", f"file://{path2}", "txt", "file", "text/plain", 10, "{}", "{}", time2),
    )
    conn.commit()

    # Total is 20, quota is 15. should trigger.
    summary = maybe_cleanup(mock_config, conn, reason="test_quota")

    # Should delete both to reach target 7 bytes?
    # Oldest first. After id-1 deleted, current is 10. 10 > 7. So delete id-2.
    assert summary["deleted_count"] == 2
    assert not path1.exists()
    assert not path2.exists()


def test_cleanup_dry_run(mock_config, conn):
    old_time = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    art_path = mock_config.artifact_store_root / "old.txt"
    art_path.write_text("old content")

    conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "old-1",
            "file",
            f"file://{art_path}",
            "txt",
            "file",
            "text/plain",
            11,
            "{}",
            "{}",
            old_time,
        ),
    )
    conn.commit()

    summary = run_cleanup(mock_config, conn, reason="test", dry_run=True)

    assert summary["deleted_count"] == 1
    assert art_path.exists()

    # Check DB
    row = conn.execute("SELECT * FROM artifacts WHERE ref_id = 'old-1'").fetchone()
    assert row is not None
