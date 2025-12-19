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
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            checksums_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL
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
            PRIMARY KEY (tool_id, fn_id)
        );
        """
    )
    conn.commit()
