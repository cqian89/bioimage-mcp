from __future__ import annotations

import sqlite3
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
