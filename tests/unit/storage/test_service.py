import sqlite3
import pytest
from datetime import UTC, datetime, timedelta
from bioimage_mcp.storage.service import StorageService
from bioimage_mcp.storage.sqlite import init_schema
from bioimage_mcp.config.schema import Config, StorageSettings
from bioimage_mcp.sessions.models import Session
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


def test_complete_session(storage_service):
    # Setup: insert a session already marked as completed (as if by SessionStore)
    session_id = "test_sess"
    now = datetime.now(UTC).isoformat()
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status, completed_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, now, now, "completed", now),
    )
    storage_service.conn.commit()

    # Action
    session = storage_service.complete_session(session_id)

    # Verification
    assert session.session_id == session_id
    assert session.status == "completed"
    assert session.completed_at == now


def test_get_session_state_active(storage_service):
    session_id = "active_sess"
    now = datetime.now(UTC)
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status) VALUES (?, ?, ?, ?)",
        (session_id, now.isoformat(), now.isoformat(), "active"),
    )

    state = storage_service.get_session_state(session_id)
    assert state == "active"


def test_get_session_state_pinned(storage_service):
    session_id = "pinned_sess"
    now = datetime.now(UTC)
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status, is_pinned) VALUES (?, ?, ?, ?, ?)",
        (session_id, now.isoformat(), now.isoformat(), "active", 1),
    )

    state = storage_service.get_session_state(session_id)
    assert state == "pinned"


def test_get_session_state_expired_idle(storage_service):
    session_id = "idle_sess"
    # Over TTL
    last_activity = datetime.now(UTC) - timedelta(hours=25)
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status) VALUES (?, ?, ?, ?)",
        (session_id, last_activity.isoformat(), last_activity.isoformat(), "active"),
    )

    state = storage_service.get_session_state(session_id)
    assert state == "expired"


def test_get_session_state_completed(storage_service):
    session_id = "comp_sess"
    now = datetime.now(UTC)
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, completed_at, status) VALUES (?, ?, ?, ?, ?)",
        (session_id, now.isoformat(), now.isoformat(), now.isoformat(), "completed"),
    )

    state = storage_service.get_session_state(session_id)
    assert state == "completed"


def test_get_session_state_expired_retention(storage_service):
    session_id = "old_comp_sess"
    # Over retention (7 days)
    completed_at = datetime.now(UTC) - timedelta(days=8)
    storage_service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, completed_at, status) VALUES (?, ?, ?, ?, ?)",
        (
            session_id,
            completed_at.isoformat(),
            completed_at.isoformat(),
            completed_at.isoformat(),
            "completed",
        ),
    )

    state = storage_service.get_session_state(session_id)
    assert state == "expired"
