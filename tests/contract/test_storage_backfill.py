import sqlite3
import pytest
from datetime import datetime, timedelta
from bioimage_mcp.storage.sqlite import init_schema, migrate_schema


def test_session_backfill_logic(tmp_path):
    """T007: Verify backfill logic for old sessions."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Initialize schema first to have the table
    init_schema(conn)

    # Insert sessions that should be backfilled
    from datetime import timezone

    now = datetime.now(timezone.utc)
    # ISO format that SQLite datetime() understands
    old_time = (now - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
    recent_time = (now - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status) VALUES (?, ?, ?, ?)",
        ("old_session", old_time, old_time, "active"),
    )
    conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_activity_at, status) VALUES (?, ?, ?, ?)",
        ("recent_session", recent_time, recent_time, "active"),
    )
    conn.commit()

    # Run migration again to trigger backfill
    migrate_schema(conn)

    # Check old_session
    row = conn.execute("SELECT * FROM sessions WHERE session_id = 'old_session'").fetchone()
    assert row["completed_at"] == old_time
    assert row["status"] == "completed"

    # Check recent_session
    row = conn.execute("SELECT * FROM sessions WHERE session_id = 'recent_session'").fetchone()
    assert row["completed_at"] is None
    assert row["status"] == "active"
