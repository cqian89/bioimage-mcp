import pytest
from bioimage_mcp.cli import main
from bioimage_mcp.storage.sqlite import connect
from bioimage_mcp.config.loader import load_config
from datetime import UTC, datetime


@pytest.fixture
def mock_session(tmp_path, monkeypatch):
    # Setup a fake config and DB in tmp_path
    root = (tmp_path / "mcp").absolute()
    root.mkdir()
    (root / "state").mkdir()

    # We need to monkeypatch load_config to return our custom config
    from bioimage_mcp.config.schema import Config, StorageSettings

    config = Config(
        artifact_store_root=root,
        tool_manifest_roots=[],
        storage=StorageSettings(quota_bytes=1000),
    )
    monkeypatch.setattr("bioimage_mcp.config.loader.load_config", lambda: config)

    # Initialize DB
    conn = connect(config)
    session_id = "test_sess"
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status, is_pinned) VALUES (?, ?, ?, ?, ?)",
        (session_id, now, now, "active", 0),
    )
    conn.commit()
    conn.close()

    return session_id, config


def test_storage_pin_cli(mock_session, capsys):
    """T050: Integration test for `storage pin` CLI command"""
    session_id, config = mock_session

    # Action: Pin
    exit_code = main(["storage", "pin", session_id])
    assert exit_code == 0

    out, err = capsys.readouterr()
    assert f"Session {session_id} is now pinned" in out

    # Verify in DB
    conn = connect(config)
    row = conn.execute(
        "SELECT is_pinned FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    assert row["is_pinned"] == 1
    conn.close()


def test_storage_unpin_cli(mock_session, capsys):
    session_id, config = mock_session

    # Setup: Pin first
    conn = connect(config)
    conn.execute("UPDATE sessions SET is_pinned = 1 WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

    # Action: Unpin
    exit_code = main(["storage", "pin", session_id, "--unpin"])
    assert exit_code == 0

    out, err = capsys.readouterr()
    assert f"Session {session_id} is now unpinned" in out

    # Verify in DB
    conn = connect(config)
    row = conn.execute(
        "SELECT is_pinned FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    assert row["is_pinned"] == 0
    conn.close()


def test_storage_pin_not_found(mock_session):
    exit_code = main(["storage", "pin", "ghost"])
    assert exit_code == 1
