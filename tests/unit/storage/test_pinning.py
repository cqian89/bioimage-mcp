import sqlite3
import pytest
from datetime import UTC, datetime, timedelta
from bioimage_mcp.storage.service import StorageService
from bioimage_mcp.storage.sqlite import init_schema
from bioimage_mcp.config.schema import Config, StorageSettings
from pathlib import Path


@pytest.fixture
def storage_service(tmp_path):
    root = (tmp_path / "mcp").absolute()
    root.mkdir()
    config = Config(
        artifact_store_root=root,
        tool_manifest_roots=[(root / "tools").absolute()],
        storage=StorageSettings(retention_days=7),
        session_ttl_hours=24,
    )
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    return StorageService(config, conn)


def test_pin_session(storage_service):
    """T047: Unit test for StorageService.pin_session()"""
    # Setup
    session_id = "test_sess"
    now = datetime.now(UTC).isoformat()
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status, is_pinned) VALUES (?, ?, ?, ?, ?)",
        (session_id, now, now, "active", 0),
    )
    storage_service.conn.commit()

    # Action
    session = storage_service.pin_session(session_id)

    # Verification
    assert session.session_id == session_id
    assert session.is_pinned is True

    # Verify in DB
    row = storage_service.conn.execute(
        "SELECT is_pinned FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    assert row["is_pinned"] == 1


def test_unpin_session(storage_service):
    """T048: Unit test for StorageService.unpin_session()"""
    # Setup
    session_id = "test_sess"
    now = datetime.now(UTC).isoformat()
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status, is_pinned) VALUES (?, ?, ?, ?, ?)",
        (session_id, now, now, "active", 1),
    )
    storage_service.conn.commit()

    # Action
    session = storage_service.unpin_session(session_id)

    # Verification
    assert session.session_id == session_id
    assert session.is_pinned is False

    # Verify in DB
    row = storage_service.conn.execute(
        "SELECT is_pinned FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    assert row["is_pinned"] == 0


def test_prune_skips_pinned(storage_service):
    """T049: Unit test for prune() skipping pinned sessions"""
    # Setup: one expired session, one expired but pinned session
    now = datetime.now(UTC)
    old = (now - timedelta(days=10)).isoformat()

    # Expired session
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status, completed_at, is_pinned) VALUES (?, ?, ?, ?, ?, ?)",
        ("expired_sess", old, old, "completed", old, 0),
    )
    # Expired but pinned session
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status, completed_at, is_pinned) VALUES (?, ?, ?, ?, ?, ?)",
        ("pinned_sess", old, old, "completed", old, 1),
    )
    storage_service.conn.commit()

    # Action
    result = storage_service.prune()

    # Verification
    assert result.sessions_deleted == 1

    # Verify expired_sess is gone
    row = storage_service.conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE session_id = 'expired_sess'"
    ).fetchone()
    assert row[0] == 0

    # Verify pinned_sess is still there
    row = storage_service.conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE session_id = 'pinned_sess'"
    ).fetchone()
    assert row[0] == 1


def test_pin_session_not_found(storage_service):
    with pytest.raises(KeyError):
        storage_service.pin_session("nonexistent")


def test_unpin_session_not_found(storage_service):
    with pytest.raises(KeyError):
        storage_service.unpin_session("nonexistent")
