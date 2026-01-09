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
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return StorageService(config, conn)


def create_session(service, session_id, created_at=None, completed_at=None, is_pinned=0):
    now = datetime.now(UTC)
    created_at = created_at or now
    last_activity_at = created_at
    status = "active" if completed_at is None else "completed"

    service.conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, completed_at, status, is_pinned) VALUES (?, ?, ?, ?, ?, ?)",
        (
            session_id,
            created_at.isoformat(),
            last_activity_at.isoformat(),
            completed_at.isoformat() if completed_at else None,
            status,
            is_pinned,
        ),
    )
    service.conn.commit()


def create_artifact(service, session_id, ref_id, size_bytes):
    service.conn.execute(
        """
        INSERT INTO artifacts (
            ref_id, session_id, type, uri, format, mime_type, size_bytes, 
            checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ref_id,
            session_id,
            "BioImageRef",
            f"file:///tmp/{ref_id}",
            "ome-tiff",
            "image/tiff",
            size_bytes,
            "{}",
            "{}",
            datetime.now(UTC).isoformat(),
        ),
    )
    service.conn.commit()


def test_list_sessions_default(storage_service):
    """T057: Unit test for list_sessions() default behavior"""
    now = datetime.now(UTC)
    create_session(storage_service, "sess_1", created_at=now - timedelta(hours=1))
    create_artifact(storage_service, "sess_1", "art1", 1000)

    create_session(storage_service, "sess_2", created_at=now - timedelta(hours=2))
    create_artifact(storage_service, "sess_2", "art2", 2000)

    summaries = storage_service.list_sessions()

    assert len(summaries) == 2
    # sess_2 is older, but default sort is by age (which usually means newest first in many lists, but let's check contract)
    # Contract says: sort_by="age" (default)
    # Usually "age" sort means newest first if it's a list of recent items.
    # The requirement says "Sort by session age (default)".
    # If age is "how long it has existed", then older sessions have larger age.
    # Let's assume newest first (age ascending in terms of seconds from now).

    assert summaries[0].session_id == "sess_1"
    assert summaries[1].session_id == "sess_2"
    assert summaries[0].artifact_count == 1
    assert summaries[0].total_bytes == 1000


def test_list_sessions_state_filter(storage_service):
    """T058: Unit test for list_sessions() with state filter"""
    now = datetime.now(UTC)
    create_session(storage_service, "active_1")
    create_session(storage_service, "pinned_1", is_pinned=1)
    create_session(
        storage_service, "expired_1", created_at=now - timedelta(hours=48)
    )  # expired because > 24h TTL

    active_sessions = storage_service.list_sessions(state="active")
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == "active_1"

    pinned_sessions = storage_service.list_sessions(state="pinned")
    assert len(pinned_sessions) == 1
    assert pinned_sessions[0].session_id == "pinned_1"

    expired_sessions = storage_service.list_sessions(state="expired")
    assert len(expired_sessions) == 1
    assert expired_sessions[0].session_id == "expired_1"


def test_list_sessions_sort_options(storage_service):
    """T059: Unit test for list_sessions() with sort options"""
    now = datetime.now(UTC)
    # sess_a: 1h old, 2000 bytes
    create_session(storage_service, "sess_a", created_at=now - timedelta(hours=1))
    create_artifact(storage_service, "sess_a", "art_a", 2000)

    # sess_b: 2h old, 1000 bytes
    create_session(storage_service, "sess_b", created_at=now - timedelta(hours=2))
    create_artifact(storage_service, "sess_b", "art_b", 1000)

    # Sort by size (descending)
    summaries = storage_service.list_sessions(sort_by="size")
    assert summaries[0].session_id == "sess_a"
    assert summaries[1].session_id == "sess_b"

    # Sort by name (alphabetical)
    summaries = storage_service.list_sessions(sort_by="name")
    assert summaries[0].session_id == "sess_a"
    assert summaries[1].session_id == "sess_b"

    # Sort by age (newest first)
    summaries = storage_service.list_sessions(sort_by="age")
    assert summaries[0].session_id == "sess_a"
    assert summaries[1].session_id == "sess_b"
