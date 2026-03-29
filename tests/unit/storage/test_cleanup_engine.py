from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from bioimage_mcp.config.schema import Config, StoragePolicy
from bioimage_mcp.storage.cleanup import maybe_cleanup, run_cleanup
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
    (root / "tools").mkdir()
    (root / "objects").mkdir()
    return Config(
        artifact_store_root=root,
        tool_manifest_roots=[root / "tools"],
        storage=StoragePolicy(
            retention_days=7,
            quota_bytes=1000,
            trigger_fraction=0.9,
            target_fraction=0.7,
            cooldown_seconds=60,
        ),
    )


def test_cleanup_dry_run_safety(db_conn, config):
    # Create an artifact with a file on disk
    ref_id = "art1"
    art_path = config.artifact_store_root / "objects" / "file1.txt"
    art_path.write_text("hello")
    size = art_path.stat().st_size

    db_conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ref_id,
            "image",
            f"file://{art_path}",
            "tiff",
            "file",
            "image/tiff",
            size,
            "{}",
            "{}",
            "2026-01-01T00:00:00Z",
        ),
    )
    db_conn.commit()

    # Run cleanup in dry-run mode
    summary = run_cleanup(config, db_conn, dry_run=True)

    assert summary["dry_run"] is True
    assert summary["deleted_count"] == 1

    # Verify file still exists
    assert art_path.exists()

    # Verify DB row still exists
    row = db_conn.execute("SELECT * FROM artifacts WHERE ref_id = ?", (ref_id,)).fetchone()
    assert row is not None

    # Verify cleanup_events recorded dry_run=1
    event = db_conn.execute("SELECT * FROM cleanup_events").fetchone()
    assert event["dry_run"] == 1


def test_cleanup_quota_down_to_target(db_conn, config):
    # Set quota small: 1000 bytes. Trigger at 900, target at 700.
    # Create 10 artifacts of 100 bytes each = 1000 bytes.
    for i in range(10):
        ref_id = f"art{i}"
        art_path = config.artifact_store_root / "objects" / f"file{i}.txt"
        art_path.write_text("x" * 100)

        # Space out created_at so FIFO is deterministic
        created_at = (datetime.now(UTC) - timedelta(hours=10 - i)).isoformat()

        db_conn.execute(
            """
            INSERT INTO artifacts (
                ref_id, type, uri, format, storage_type, mime_type, 
                size_bytes, checksums_json, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ref_id,
                "image",
                f"file://{art_path}",
                "tiff",
                "file",
                "image/tiff",
                100,
                "{}",
                "{}",
                created_at,
            ),
        )
    db_conn.commit()

    manager = StorageManager(config, db_conn)
    assert manager.get_total_bytes() == 1000

    # Run cleanup. Should trigger quota cleanup.
    # We expect to go down to 700 bytes (target_fraction=0.7).
    # That means 3 artifacts should be deleted.
    summary = run_cleanup(config, db_conn, reason="quota_test", dry_run=False)

    assert summary["deleted_count"] == 3
    assert summary["after_bytes"] == 700

    # Verify oldest ones are gone: art0, art1, art2
    for i in range(3):
        assert not (config.artifact_store_root / "objects" / f"file{i}.txt").exists()

    # Verify newer ones remain: art3 to art9
    for i in range(3, 10):
        assert (config.artifact_store_root / "objects" / f"file{i}.txt").exists()


def test_cleanup_cooldown_enforcement(db_conn, config):
    # First run
    maybe_cleanup(config, db_conn, force=True)

    # Check last run time
    row = db_conn.execute(
        "SELECT value FROM registry_state WHERE key = 'cleanup_last_run_at'"
    ).fetchone()
    assert row is not None

    # Second run immediately should return None (skipped due to cooldown)
    summary = maybe_cleanup(config, db_conn, force=False)
    assert summary is None

    # Force run should ignore cooldown
    summary_forced = maybe_cleanup(config, db_conn, force=True)
    assert summary_forced is not None
