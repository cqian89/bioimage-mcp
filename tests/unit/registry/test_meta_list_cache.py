from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from bioimage_mcp.registry.dynamic.meta_list_cache import MetaListCache


@pytest.fixture
def cache_dir(tmp_path):
    """Temporary cache directory."""
    cache_path = tmp_path / "cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def test_meta_list_cache_hit_miss(cache_dir):
    """Basic hit/miss test."""
    cache = MetaListCache(cache_dir)
    lh = "lock-1"
    mc = "manifest-1"
    results = [{"id": "f1", "name": "func1"}]

    # Miss
    assert cache.get(lh, mc) is None

    # Put
    cache.put(lh, mc, results)

    # Hit
    assert cache.get(lh, mc) == results


def test_meta_list_cache_version_invalidation(cache_dir):
    """Test that changing cache version key invalidates the cache."""
    cache = MetaListCache(cache_dir)
    lh = "lock-1"
    mc = "manifest-1"
    results = [{"id": "f1", "name": "func1"}]

    # 1. Put with version V1
    with patch("bioimage_mcp.registry.dynamic.meta_list_cache.get_cache_version_key") as mock_vkey:
        mock_vkey.return_value = "V1"
        cache.put(lh, mc, results)
        assert cache.get(lh, mc) == results

    # 2. Try to get with version V2 (should be miss)
    with patch("bioimage_mcp.registry.dynamic.meta_list_cache.get_cache_version_key") as mock_vkey:
        mock_vkey.return_value = "V2"
        assert cache.get(lh, mc) is None

    # 3. Put with V2 and verify V1 still exists in file
    with patch("bioimage_mcp.registry.dynamic.meta_list_cache.get_cache_version_key") as mock_vkey:
        mock_vkey.return_value = "V2"
        cache.put(lh, mc, results)
        assert cache.get(lh, mc) == results

    with open(cache_dir / "meta_list_cache.json") as f:
        data = json.load(f)
        assert "V1" in data
        assert "V2" in data
        assert f"{lh}:{mc}" in data["V1"]
        assert f"{lh}:{mc}" in data["V2"]


def test_meta_list_cache_migration_from_old_format(cache_dir):
    """Test that old format (no version key) is handled as a miss."""
    lh = "lock-1"
    mc = "manifest-1"
    results = [{"id": "f1", "name": "func1"}]

    # Manually create old format cache file
    old_data = {f"{lh}:{mc}": results}
    cache_file = cache_dir / "meta_list_cache.json"
    with open(cache_file, "w") as f:
        json.dump(old_data, f)

    cache = MetaListCache(cache_dir)

    # Should be a miss because it expects a version key at top level
    with patch("bioimage_mcp.registry.dynamic.meta_list_cache.get_cache_version_key") as mock_vkey:
        mock_vkey.return_value = "V1"
        assert cache.get(lh, mc) is None

    # Put with V1 should now add V1 alongside
    with patch("bioimage_mcp.registry.dynamic.meta_list_cache.get_cache_version_key") as mock_vkey:
        mock_vkey.return_value = "V1"
        cache.put(lh, mc, results)
        assert cache.get(lh, mc) == results

    with open(cache_file) as f:
        data = json.load(f)
        assert "V1" in data
        assert f"{lh}:{mc}" in data  # Old data still there
