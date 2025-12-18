from __future__ import annotations

import pytest

from bioimage_mcp.api.pagination import decode_cursor, encode_cursor, resolve_limit
from bioimage_mcp.config.schema import Config


def test_encode_decode_cursor_roundtrip() -> None:
    cursor = encode_cursor({"last": "abc", "n": 3})
    assert decode_cursor(cursor) == {"last": "abc", "n": 3}


def test_decode_cursor_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        decode_cursor("not-a-real-cursor")


def test_resolve_limit_enforces_config_bounds(tmp_path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
        default_pagination_limit=5,
        max_pagination_limit=10,
    )

    assert resolve_limit(None, config) == 5
    assert resolve_limit(1, config) == 1
    assert resolve_limit(999, config) == 10
