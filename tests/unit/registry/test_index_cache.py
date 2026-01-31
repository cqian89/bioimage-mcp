from __future__ import annotations

import json
import sqlite3
from unittest.mock import patch

import pytest

from bioimage_mcp.registry.index import RegistryIndex
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def index():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return RegistryIndex(conn)


def test_registry_index_schema_cache_full_validation(index):
    tool_id = "test-tool"
    tool_version = "1.0.0"
    fn_id = "test.fn"
    params_schema = {"type": "object", "properties": {"a": {"type": "integer"}}}
    introspection_source = "ast"
    env_lock_hash = "env-hash-1"
    source_hash = "source-hash-1"
    callable_fingerprint = "source-hash-1"  # Usually same

    # Upsert with full keys
    index.upsert_schema_cache(
        tool_id=tool_id,
        tool_version=tool_version,
        fn_id=fn_id,
        params_schema=params_schema,
        introspection_source=introspection_source,
        env_lock_hash=env_lock_hash,
        callable_fingerprint=callable_fingerprint,
        source_hash=source_hash,
    )

    # Hit with exact match
    hit = index.get_cached_schema(
        tool_id=tool_id,
        tool_version=tool_version,
        fn_id=fn_id,
        env_lock_hash=env_lock_hash,
        source_hash=source_hash,
    )
    assert hit is not None
    assert hit["params_schema"] == params_schema
    assert hit["env_lock_hash"] == env_lock_hash
    assert hit["source_hash"] == source_hash

    # Miss if tool_version differs
    assert (
        index.get_cached_schema(
            tool_id=tool_id,
            tool_version="2.0.0",
            fn_id=fn_id,
            env_lock_hash=env_lock_hash,
            source_hash=source_hash,
        )
        is None
    )

    # Miss if env_lock_hash differs
    assert (
        index.get_cached_schema(
            tool_id=tool_id,
            tool_version=tool_version,
            fn_id=fn_id,
            env_lock_hash="different-env",
            source_hash=source_hash,
        )
        is None
    )

    # Miss if source_hash differs
    assert (
        index.get_cached_schema(
            tool_id=tool_id,
            tool_version=tool_version,
            fn_id=fn_id,
            env_lock_hash=env_lock_hash,
            source_hash="different-source",
        )
        is None
    )


def test_registry_index_schema_cache_fingerprint_fallback(index):
    tool_id = "test-tool"
    tool_version = "1.0.0"
    fn_id = "test.fn"
    params_schema = {"type": "object"}
    introspection_source = "ast"
    callable_fingerprint = "fp-1"

    # Upsert with fingerprint but no explicit source_hash
    index.upsert_schema_cache(
        tool_id=tool_id,
        tool_version=tool_version,
        fn_id=fn_id,
        params_schema=params_schema,
        introspection_source=introspection_source,
        callable_fingerprint=callable_fingerprint,
    )

    # Should hit if source_hash matches fingerprint
    hit = index.get_cached_schema(
        tool_id=tool_id, tool_version=tool_version, fn_id=fn_id, source_hash="fp-1"
    )
    assert hit is not None
    assert hit["source_hash"] == "fp-1"


def test_registry_index_schema_cache_backward_compatibility(index):
    # Test that it doesn't crash if optional hashes are not provided for lookup
    tool_id = "test-tool"
    tool_version = "1.0.0"
    fn_id = "test.fn"
    params_schema = {"type": "object"}
    introspection_source = "ast"

    index.upsert_schema_cache(
        tool_id=tool_id,
        tool_version=tool_version,
        fn_id=fn_id,
        params_schema=params_schema,
        introspection_source=introspection_source,
        env_lock_hash="env-1",
        source_hash="src-1",
    )

    # Lookup without hashes should still hit (backward compatibility for callers)
    hit = index.get_cached_schema(tool_id=tool_id, tool_version=tool_version, fn_id=fn_id)
    assert hit is not None


def test_registry_index_schema_cache_program_version_invalidation(index):
    tool_id = "test-tool"
    tool_version = "1.0.0"
    fn_id = "test.fn"
    params_schema = {"type": "object"}
    introspection_source = "ast"

    # 1. Upsert with version A
    with patch("bioimage_mcp.registry.index.get_cache_version_key", return_value="v1"):
        index.upsert_schema_cache(
            tool_id=tool_id,
            tool_version=tool_version,
            fn_id=fn_id,
            params_schema=params_schema,
            introspection_source=introspection_source,
        )

    # 2. Hit with same version
    with patch("bioimage_mcp.registry.index.get_cache_version_key", return_value="v1"):
        hit = index.get_cached_schema(tool_id=tool_id, tool_version=tool_version, fn_id=fn_id)
        assert hit is not None

    # 3. Miss with different version
    with patch("bioimage_mcp.registry.index.get_cache_version_key", return_value="v2"):
        hit = index.get_cached_schema(tool_id=tool_id, tool_version=tool_version, fn_id=fn_id)
        assert hit is None


def test_registry_index_schema_cache_migration_graceful(index):
    # This test simulates an old DB without program_version column.
    # RegistryIndex.get_cached_schema should handle it gracefully (treat as miss)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Create old schema without program_version but with other expected columns
    conn.execute(
        """
        CREATE TABLE schema_cache (
            tool_id TEXT NOT NULL,
            tool_version TEXT NOT NULL,
            fn_id TEXT NOT NULL,
            params_schema_json TEXT NOT NULL,
            introspection_source TEXT NOT NULL,
            introspected_at TEXT NOT NULL,
            env_lock_hash TEXT,
            callable_fingerprint TEXT,
            source_hash TEXT,
            PRIMARY KEY (tool_id, fn_id)
        )
        """
    )
    # Insert some data
    conn.execute(
        """
        INSERT INTO schema_cache (
            tool_id, tool_version, fn_id, params_schema_json,
            introspection_source, introspected_at, env_lock_hash,
            callable_fingerprint, source_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("t1", "1.0", "f1", "{}", "ast", "2024-01-01T00:00:00Z", "e1", "c1", "s1"),
    )
    conn.commit()

    idx = RegistryIndex(conn)
    # Should be a miss because column is missing
    assert idx.get_cached_schema(tool_id="t1", tool_version="1.0", fn_id="f1") is None


def test_registry_index_schema_cache_null_program_version(index):
    # Test that NULL program_version (from older records) is treated as a miss
    tool_id = "test-tool"
    tool_version = "1.0.0"
    fn_id = "test.fn"
    params_schema = {"type": "object"}
    introspection_source = "ast"

    # Insert directly with NULL program_version
    index._conn.execute(
        """
        INSERT INTO schema_cache (
            tool_id, tool_version, fn_id, params_schema_json,
            introspection_source, introspected_at, program_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tool_id,
            tool_version,
            fn_id,
            json.dumps(params_schema),
            introspection_source,
            "2024-01-01",
            None,
        ),
    )
    index._conn.commit()

    hit = index.get_cached_schema(tool_id=tool_id, tool_version=tool_version, fn_id=fn_id)
    assert hit is None
