from __future__ import annotations

import os
from unittest.mock import patch

from bioimage_mcp.registry.cache_version import (
    CACHE_SCHEMA_VERSION,
    _compute_critical_source_hash,
    get_cache_version_key,
)


def test_cache_schema_version():
    assert CACHE_SCHEMA_VERSION == "3"


def test_get_cache_version_key_standard():
    # Clear cache before test
    get_cache_version_key.cache_clear()

    with patch("importlib.metadata.version") as mock_version:
        mock_version.return_value = "0.1.0"
        with patch.dict(os.environ, {"BIOIMAGE_MCP_DEV_CACHE_CHECK": "0"}):
            key = get_cache_version_key()
            assert key == "3-0.1.0"
            mock_version.assert_called_once_with("bioimage-mcp")


def test_get_cache_version_key_editable():
    get_cache_version_key.cache_clear()

    from importlib.metadata import PackageNotFoundError

    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        with patch.dict(os.environ, {"BIOIMAGE_MCP_DEV_CACHE_CHECK": "0"}):
            key = get_cache_version_key()
            assert key == "3-editable"


def test_get_cache_version_key_dev_check():
    get_cache_version_key.cache_clear()

    with patch("importlib.metadata.version") as mock_version:
        mock_version.return_value = "0.1.0"
        with patch.dict(os.environ, {"BIOIMAGE_MCP_DEV_CACHE_CHECK": "1"}):
            key = get_cache_version_key()
            # Key should have 3 parts: schema-version-hash
            parts = key.split("-")
            assert len(parts) == 3
            assert parts[0] == "3"
            assert parts[1] == "0.1.0"
            assert len(parts[2]) == 12  # hash length from implementation


def test_compute_critical_source_hash():
    # This might depend on the actual files existing, but we can verify it returns a string
    h = _compute_critical_source_hash()
    assert isinstance(h, str)
    assert len(h) == 12


def test_lru_cache_behavior():
    get_cache_version_key.cache_clear()

    with patch("importlib.metadata.version") as mock_version:
        mock_version.return_value = "0.1.0"
        with patch.dict(os.environ, {"BIOIMAGE_MCP_DEV_CACHE_CHECK": "0"}):
            key1 = get_cache_version_key()
            key2 = get_cache_version_key()

            assert key1 == key2
            # Should only be called once due to lru_cache
            mock_version.assert_called_once()
