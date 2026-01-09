from __future__ import annotations

import sqlite3
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.config.schema import Config, StorageSettings
from bioimage_mcp.storage.service import StorageService
from bioimage_mcp.storage.sqlite import init_schema
from bioimage_mcp.storage.models import OrphanFile


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


def test_prune_active_session_T072(storage_service, conn):
    """T072: Test prune during active session (must not delete active sessions)"""
    add_session(conn, "active_session", status="active")
    add_artifact(conn, "a1", "active_session", 100)

    result = storage_service.prune()
    assert result.sessions_deleted == 0
    assert (
        conn.execute(
            "SELECT count(*) FROM sessions WHERE session_id = 'active_session'"
        ).fetchone()[0]
        == 1
    )


def test_idempotent_cleanup_T073(storage_service, conn, tmp_path):
    """T073: Test idempotent cleanup (file already deleted - no error)"""
    old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    add_session(conn, "expired_session", status="completed", completed_at=old_time)

    # Artifact path that doesn't exist
    missing_path = tmp_path / "missing.dat"
    add_artifact(conn, "a1", "expired_session", 100, uri=f"file://{missing_path}")

    # Should not raise FileNotFoundError
    result = storage_service.prune()
    assert result.sessions_deleted == 1
    assert result.artifacts_deleted == 1
    assert result.errors == []
    assert (
        conn.execute(
            "SELECT count(*) FROM sessions WHERE session_id = 'expired_session'"
        ).fetchone()[0]
        == 0
    )


def test_directory_based_artifacts_T074(storage_service, conn, tmp_path):
    """T074: Test directory-based artifacts (OME-Zarr folders)"""
    old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    add_session(conn, "expired_session", status="completed", completed_at=old_time)

    zarr_dir = tmp_path / "data.zarr"
    zarr_dir.mkdir()
    (zarr_dir / "meta.json").write_text("{}")

    add_artifact(conn, "a1", "expired_session", 100, uri=f"file://{zarr_dir}")

    result = storage_service.prune()
    assert result.sessions_deleted == 1
    assert not zarr_dir.exists()


def test_missing_file_with_index_entry_T075(storage_service, conn, tmp_path):
    """T075: Test missing file with index entry (stale DB record)"""
    # This is similar to T073 but specifically checking if DB record is gone
    old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    add_session(conn, "expired_session", status="completed", completed_at=old_time)

    missing_path = tmp_path / "stale.dat"
    add_artifact(conn, "a1", "expired_session", 100, uri=f"file://{missing_path}")

    storage_service.prune()
    assert conn.execute("SELECT count(*) FROM artifacts WHERE ref_id = 'a1'").fetchone()[0] == 0


def test_quota_check_empty_store_T076(storage_service):
    """T076: Test quota check on empty store"""
    result = storage_service.check_quota()
    assert result.allowed is True
    assert result.usage_percent == 0.0
    assert result.used_bytes == 0


def test_interrupted_prune_convergence_T089(storage_service, conn, tmp_path):
    """T089: Test interrupted prune convergence (rerun completes cleanly)"""
    old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    add_session(conn, "expired_session", status="completed", completed_at=old_time)

    path = tmp_path / "data.dat"
    path.write_bytes(b"data")
    add_artifact(conn, "a1", "expired_session", 4, uri=f"file://{path}")

    # Simulate interruption: file is deleted but DB record remains
    path.unlink()
    assert not path.exists()
    assert conn.execute("SELECT count(*) FROM artifacts WHERE ref_id = 'a1'").fetchone()[0] == 1

    # Prune should reconcile this
    result = storage_service.prune()
    assert result.sessions_deleted == 1
    assert result.artifacts_deleted == 1
    assert conn.execute("SELECT count(*) FROM artifacts WHERE ref_id = 'a1'").fetchone()[0] == 0


def test_concurrent_prune_safety_T088(storage_service, mock_config):
    """T088: Test concurrent prune safety (locking prevents overlap)"""
    import fcntl

    lock_file = mock_config.artifact_store_root / ".prune.lock"
    lock_file.touch()

    with open(lock_file, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Now prune should return a result with an error message about locking
        result = storage_service.prune()
        assert len(result.errors) == 1
        assert "concurrent" in result.errors[0].lower()
