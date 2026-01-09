from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.config.schema import Config, StorageSettings
from bioimage_mcp.storage.service import StorageService
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def mock_config(tmp_path: Path):
    config = MagicMock(spec=Config)
    config.artifact_store_root = tmp_path
    config.storage = StorageSettings(
        quota_bytes=1000,
        warning_threshold=0.8,
        critical_threshold=0.9,
        retention_days=7,
        auto_cleanup_enabled=False,
    )
    config.session_ttl_hours = 24
    return config


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


@pytest.fixture
def storage_service(mock_config, conn):
    return StorageService(mock_config, conn)


def add_session(
    conn,
    session_id,
    status="active",
    is_pinned=0,
    created_at=None,
    last_activity_at=None,
    completed_at=None,
):
    now = datetime.now(UTC).isoformat()
    created_at = created_at or now
    last_activity_at = last_activity_at or now
    conn.execute(
        "INSERT INTO sessions (session_id, status, is_pinned, created_at, last_activity_at, completed_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, status, is_pinned, created_at, last_activity_at, completed_at),
    )


def add_artifact(conn, ref_id, session_id, size_bytes, uri=None):
    uri = uri or f"file:///tmp/artifacts/{ref_id}"
    conn.execute(
        "INSERT INTO artifacts (ref_id, type, uri, format, storage_type, mime_type, size_bytes, checksums_json, metadata_json, created_at, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ref_id,
            "BioImageRef",
            uri,
            "OME-TIFF",
            "file",
            "image/tiff",
            size_bytes,
            "{}",
            "{}",
            datetime.now(UTC).isoformat(),
            session_id,
        ),
    )


def test_get_status_empty(storage_service):
    """T018: Unit test for StorageService.get_status() - empty state"""
    status = storage_service.get_status()
    assert status.total_bytes == 1000
    assert status.used_bytes == 0
    assert status.usage_percent == 0.0
    assert status.orphan_bytes == 0
    for state in ["active", "completed", "expired", "pinned"]:
        assert status.by_state[state].session_count == 0
        assert status.by_state[state].total_bytes == 0


def test_get_status_with_data(storage_service, conn, tmp_path):
    """T018: Unit test for StorageService.get_status() - with data"""
    # Active session
    add_session(conn, "s1", status="active")
    add_artifact(conn, "a1", "s1", 100)

    # Completed session
    add_session(conn, "s2", status="completed", completed_at=datetime.now(UTC).isoformat())
    add_artifact(conn, "a2", "s2", 200)

    # Expired session (old completed)
    old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    add_session(conn, "s3", status="completed", completed_at=old_time)
    add_artifact(conn, "a3", "s3", 300)

    # Pinned session
    add_session(conn, "s4", status="active", is_pinned=1)
    add_artifact(conn, "a4", "s4", 400)

    # Add an orphan file
    obj_dir = tmp_path / "objects"
    obj_dir.mkdir(parents=True, exist_ok=True)
    orphan_file = obj_dir / "orphan.dat"
    orphan_file.write_bytes(b"hello")

    status = storage_service.get_status()
    assert status.used_bytes == 1005
    assert status.usage_percent == pytest.approx(100.5)
    assert status.orphan_bytes == 5

    assert status.by_state["active"].session_count == 1
    assert status.by_state["active"].total_bytes == 100

    assert status.by_state["completed"].session_count == 1
    assert status.by_state["completed"].total_bytes == 200

    assert status.by_state["expired"].session_count == 1
    assert status.by_state["expired"].total_bytes == 300

    assert status.by_state["pinned"].session_count == 1
    assert status.by_state["pinned"].total_bytes == 400


def test_get_session_size(storage_service, conn):
    """T019: Unit test for StorageService.get_session_size(session_id)"""
    add_session(conn, "s1")
    add_artifact(conn, "a1", "s1", 100)
    add_artifact(conn, "a2", "s1", 200)

    assert storage_service.get_session_size("s1") == 300
    assert storage_service.get_session_size("nonexistent") == 0


def test_find_orphans(storage_service, conn, tmp_path):
    """T022: Unit test for StorageService.find_orphans()"""
    obj_dir = tmp_path / "objects"
    obj_dir.mkdir(parents=True, exist_ok=True)

    # Tracked file
    tracked_path = obj_dir / "tracked.dat"
    tracked_path.write_bytes(b"tracked")
    add_session(conn, "s1")
    add_artifact(conn, "a1", "s1", 7, uri=f"file://{tracked_path}")

    # Orphan file
    orphan_path = obj_dir / "orphan.dat"
    orphan_path.write_bytes(b"orphan")

    # Another tracked file (but with different URI scheme, should still be tracked if it's in objects/)
    # Actually orphans are defined as files in objects/ not in artifacts table.

    orphans = storage_service.find_orphans()
    assert len(orphans) == 1
    assert orphans[0].path == orphan_path
    assert orphans[0].size_bytes == 6


def test_delete_orphans(storage_service, tmp_path):
    """T023: Unit test for StorageService.delete_orphans()"""
    obj_dir = tmp_path / "objects"
    obj_dir.mkdir(parents=True, exist_ok=True)

    orphan_path = obj_dir / "orphan.dat"
    orphan_path.write_bytes(b"orphan")

    from bioimage_mcp.storage.models import OrphanFile

    orphans = [OrphanFile(path=orphan_path, size_bytes=6)]

    deleted_count = storage_service.delete_orphans(orphans)
    assert deleted_count == 1
    assert not orphan_path.exists()


def test_prune_dry_run(storage_service, conn, tmp_path):
    """T020: Unit test for StorageService.prune() dry_run mode"""
    # Expired session
    old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    add_session(conn, "s1", status="completed", completed_at=old_time)

    obj_dir = tmp_path / "objects"
    obj_dir.mkdir(parents=True, exist_ok=True)
    a1_path = obj_dir / "a1.dat"
    a1_path.write_bytes(b"data")
    add_artifact(conn, "a1", "s1", 4, uri=f"file://{a1_path}")

    # Orphan
    orphan_path = obj_dir / "orphan.dat"
    orphan_path.write_bytes(b"orphan")

    result = storage_service.prune(dry_run=True, include_orphans=True)

    assert result.sessions_deleted == 1
    assert result.artifacts_deleted == 1
    assert result.bytes_reclaimed == 4
    assert result.orphan_files_deleted == 1

    # Verify nothing was actually deleted
    assert a1_path.exists()
    assert orphan_path.exists()
    assert conn.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1


def test_prune_actual_deletion(storage_service, conn, tmp_path):
    """T021: Unit test for StorageService.prune() actual deletion"""
    # Expired session
    old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    add_session(conn, "s1", status="completed", completed_at=old_time)

    obj_dir = tmp_path / "objects"
    obj_dir.mkdir(parents=True, exist_ok=True)
    a1_path = obj_dir / "a1.dat"
    a1_path.write_bytes(b"data")
    add_artifact(conn, "a1", "s1", 4, uri=f"file://{a1_path}")

    # Pinned session (should NOT be deleted even if old)
    add_session(conn, "s2", status="completed", completed_at=old_time, is_pinned=1)
    a2_path = obj_dir / "a2.dat"
    a2_path.write_bytes(b"pinned")
    add_artifact(conn, "a2", "s2", 6, uri=f"file://{a2_path}")

    # Active session (should NOT be deleted)
    add_session(conn, "s3", status="active")

    # Orphan
    orphan_path = obj_dir / "orphan.dat"
    orphan_path.write_bytes(b"orphan")

    result = storage_service.prune(dry_run=False, include_orphans=True)

    assert result.sessions_deleted == 1
    assert result.artifacts_deleted == 1
    assert result.bytes_reclaimed == 4
    assert result.orphan_files_deleted == 1

    # Verify deletion
    assert not a1_path.exists()
    assert not orphan_path.exists()
    assert a2_path.exists()

    assert conn.execute("SELECT count(*) FROM sessions WHERE session_id = 's1'").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM sessions WHERE session_id = 's2'").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM sessions WHERE session_id = 's3'").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM artifacts WHERE ref_id = 'a1'").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM artifacts WHERE ref_id = 'a2'").fetchone()[0] == 1
