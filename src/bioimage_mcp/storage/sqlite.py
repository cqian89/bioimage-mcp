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
            introspection_source TEXT,
            module TEXT,
            io_pattern TEXT
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
            session_id TEXT,
            pinned INTEGER NOT NULL DEFAULT 0,
            last_accessed_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_artifacts_created_at ON artifacts(created_at);

        CREATE TABLE IF NOT EXISTS cleanup_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            reason TEXT NOT NULL,
            dry_run INTEGER NOT NULL,
            deleted_count INTEGER NOT NULL,
            freed_bytes INTEGER NOT NULL,
            before_bytes INTEGER NOT NULL,
            after_bytes INTEGER NOT NULL,
            notes_json TEXT
        );

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
            env_lock_hash TEXT,
            callable_fingerprint TEXT,
            source_hash TEXT,
            program_version TEXT,
            PRIMARY KEY (tool_id, fn_id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            last_activity_at TEXT NOT NULL,
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

        CREATE TABLE IF NOT EXISTS registry_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )

    # Migrations
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(functions)")}
    if "module" not in existing_cols:
        conn.execute("ALTER TABLE functions ADD COLUMN module TEXT")
    if "io_pattern" not in existing_cols:
        conn.execute("ALTER TABLE functions ADD COLUMN io_pattern TEXT")

    # schema_cache migrations
    cache_cols = {row["name"] for row in conn.execute("PRAGMA table_info(schema_cache)")}
    if "env_lock_hash" not in cache_cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN env_lock_hash TEXT")
    if "callable_fingerprint" not in cache_cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN callable_fingerprint TEXT")
    if "source_hash" not in cache_cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN source_hash TEXT")
    if "program_version" not in cache_cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN program_version TEXT")

    # artifacts migrations
    art_cols = {row["name"] for row in conn.execute("PRAGMA table_info(artifacts)")}
    if "session_id" not in art_cols:
        conn.execute("ALTER TABLE artifacts ADD COLUMN session_id TEXT")
    if "pinned" not in art_cols:
        conn.execute("ALTER TABLE artifacts ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
    if "last_accessed_at" not in art_cols:
        conn.execute("ALTER TABLE artifacts ADD COLUMN last_accessed_at TEXT")

    # Final indexes and triggers (after migrations)
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_artifacts_session_id ON artifacts(session_id);
        CREATE INDEX IF NOT EXISTS idx_artifacts_pinned ON artifacts(pinned);

        -- Trigger to update total artifact bytes on insert
        CREATE TRIGGER IF NOT EXISTS trg_artifacts_total_bytes_insert
        AFTER INSERT ON artifacts
        WHEN NEW.storage_type != 'memory'
        BEGIN
            INSERT INTO registry_state (key, value, updated_at)
            VALUES ('total_artifact_bytes', CAST(NEW.size_bytes AS TEXT), datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value = CAST(CAST(value AS INTEGER) + NEW.size_bytes AS TEXT),
                updated_at = datetime('now')
            WHERE key = 'total_artifact_bytes';
        END;

        -- Trigger to update total artifact bytes on delete
        CREATE TRIGGER IF NOT EXISTS trg_artifacts_total_bytes_delete
        AFTER DELETE ON artifacts
        WHEN OLD.storage_type != 'memory'
        BEGIN
            UPDATE registry_state
            SET value = CAST(CAST(value AS INTEGER) - OLD.size_bytes AS TEXT),
                updated_at = datetime('now')
            WHERE key = 'total_artifact_bytes';
        END;
        """
    )

    # Recompute/Backfill total_artifact_bytes if missing or clearly invalid
    total_row = conn.execute(
        "SELECT SUM(size_bytes) as total FROM artifacts WHERE storage_type != 'memory'"
    ).fetchone()
    actual_total = total_row["total"] or 0

    state_row = conn.execute(
        "SELECT value FROM registry_state WHERE key = 'total_artifact_bytes'"
    ).fetchone()
    if state_row is None:
        conn.execute(
            "INSERT INTO registry_state (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            ("total_artifact_bytes", str(actual_total)),
        )
    else:
        try:
            stored_total = int(state_row["value"])
            if stored_total < 0:  # Clearly invalid
                conn.execute(
                    "UPDATE registry_state SET value = ?, updated_at = datetime('now') WHERE key = 'total_artifact_bytes'",
                    (str(actual_total),),
                )
        except ValueError:
            conn.execute(
                "UPDATE registry_state SET value = ?, updated_at = datetime('now') WHERE key = 'total_artifact_bytes'",
                (str(actual_total),),
            )

    conn.commit()
