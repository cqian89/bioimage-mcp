import sqlite3
import pytest
from pathlib import Path
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import init_schema


def test_sessions_table_migration_columns(tmp_path):
    """T003: Verify sessions table has completed_at and is_pinned columns."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    # Run init_schema
    init_schema(conn)

    # Check columns in sessions table
    cursor = conn.execute("PRAGMA table_info(sessions)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    assert "completed_at" in columns
    assert "is_pinned" in columns
    # is_pinned should be INTEGER (default 0)
    assert columns["is_pinned"].upper() == "INTEGER"


def test_artifacts_table_migration_columns(tmp_path):
    """T004: Verify artifacts table has session_id column and it's indexed."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    # Run init_schema
    init_schema(conn)

    # Check columns in artifacts table
    cursor = conn.execute("PRAGMA table_info(artifacts)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    assert "session_id" in columns

    # Check foreign key
    cursor = conn.execute("PRAGMA foreign_key_list(artifacts)")
    fks = cursor.fetchall()
    session_id_fk = [fk for fk in fks if fk[3] == "session_id" and fk[2] == "sessions"]
    assert len(session_id_fk) > 0, "session_id should be a foreign key to sessions table"

    # Check index
    cursor = conn.execute("PRAGMA index_list(artifacts)")
    indices = cursor.fetchall()
    # We expect an index on session_id
    has_session_id_index = False
    for idx in indices:
        idx_name = idx[1]
        cursor = conn.execute(f"PRAGMA index_info({idx_name})")
        info = cursor.fetchall()
        if any(col[2] == "session_id" for col in info):
            has_session_id_index = True
            break
    assert has_session_id_index, "session_id should be indexed"
