from __future__ import annotations

import sqlite3
from pathlib import Path

from bioimage_mcp.config.schema import Config


def get_db_path(config: Config) -> Path:
    state_dir = config.artifact_store_root / "state"
    return state_dir / "bioimage_mcp.sqlite3"


def connect(config: Config) -> sqlite3.Connection:
    db_path = get_db_path(config)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS tools (
            tool_id TEXT PRIMARY KEY,
            tool_version TEXT NOT NULL,
            env_id TEXT NOT NULL,
            description TEXT NOT NULL,
            manifest_path TEXT NOT NULL,
            installed INTEGER NOT NULL,
            available INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS functions (
            fn_id TEXT PRIMARY KEY,
            tool_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            outputs_json TEXT NOT NULL,
            params_schema_json TEXT NOT NULL,
            introspection_source TEXT
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            ref_id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            uri TEXT NOT NULL,
            format TEXT NOT NULL,
            storage_type TEXT NOT NULL DEFAULT 'file',
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            checksums_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            session_id TEXT REFERENCES sessions(session_id)
        );

        CREATE INDEX IF NOT EXISTS idx_artifacts_session_id ON artifacts(session_id);

        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            workflow_spec_json TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            params_json TEXT NOT NULL,
            outputs_json TEXT,
            log_ref_id TEXT NOT NULL,
            error_json TEXT,
            provenance_json TEXT NOT NULL,
            native_output_ref_id TEXT
        );

        CREATE TABLE IF NOT EXISTS diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manifest_path TEXT NOT NULL,
            tool_id TEXT,
            errors_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schema_cache (
            tool_id TEXT NOT NULL,
            tool_version TEXT NOT NULL,
            fn_id TEXT NOT NULL,
            params_schema_json TEXT NOT NULL,
            introspection_source TEXT NOT NULL,
            introspected_at TEXT NOT NULL,
            PRIMARY KEY (tool_id, fn_id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            last_activity_at TEXT NOT NULL,
            completed_at TEXT,
            is_pinned INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            connection_hint TEXT
        );

        CREATE TABLE IF NOT EXISTS session_steps (
            step_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            fn_id TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            params_json TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            run_id TEXT,
            error_json TEXT,
            outputs_json TEXT,
            log_ref_id TEXT,
            canonical INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS session_active_functions (
            session_id TEXT NOT NULL,
            fn_id TEXT NOT NULL,
            PRIMARY KEY (session_id, fn_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        """
    )
    migrate_schema(conn)
    conn.commit()


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Apply migrations to existing tables."""
    # Migration: sessions table
    cursor = conn.execute("PRAGMA table_info(sessions)")
    columns = {row[1] for row in cursor.fetchall()}
    if "completed_at" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN completed_at TEXT")
    if "is_pinned" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")

    # Migration: artifacts table
    cursor = conn.execute("PRAGMA table_info(artifacts)")
    columns = {row[1] for row in cursor.fetchall()}
    if "session_id" not in columns:
        conn.execute(
            "ALTER TABLE artifacts ADD COLUMN session_id TEXT REFERENCES sessions(session_id)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_session_id ON artifacts(session_id)")

    # Migration: backfill session_id for existing artifacts (T007)
    # Since we don't have a direct link in old schema, we might leave them as NULL
    # or try to infer if possible. For now, leaving as NULL is fine as per T007
    # being "backfill logic" which could just be ensuring the column exists.
    # Actually, if we have session_steps, we might be able to find run_id -> artifacts.
    # But artifacts don't have run_id either in the old schema.
    # So NULL is the safest backfill for now unless we have more info.

    # Migration: mark old sessions as completed (T007)
    conn.execute(
        """
        UPDATE sessions
        SET completed_at = last_activity_at, status = 'completed'
        WHERE completed_at IS NULL
        AND datetime(last_activity_at) < datetime('now', '-24 hours')
        """
    )
