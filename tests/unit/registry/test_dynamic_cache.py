"""Tests for introspection caching with lockfile invalidation.

This module tests the IntrospectionCache class that caches adapter discovery
results and invalidates the cache when the environment lockfile changes.
"""

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from bioimage_mcp.registry.dynamic.cache import IntrospectionCache
from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


@pytest.fixture
def sample_function_metadata():
    """Sample function metadata for testing."""
    return [
        FunctionMetadata(
            name="gaussian_blur",
            module="skimage.filters",
            qualified_name="skimage.filters.gaussian",
            fn_id="skimage-filters.gaussian_blur",
            source_adapter="python-introspector",
            description="Apply Gaussian filter",
            io_pattern=IOPattern.IMAGE_TO_IMAGE,
            tags=["filter", "blur"],
        ),
        FunctionMetadata(
            name="sobel",
            module="skimage.filters",
            qualified_name="skimage.filters.sobel",
            fn_id="skimage-filters.sobel",
            source_adapter="python-introspector",
            description="Sobel edge detection",
            io_pattern=IOPattern.IMAGE_TO_IMAGE,
            tags=["filter", "edge"],
        ),
    ]


@pytest.fixture
def cache_dir(tmp_path):
    """Temporary cache directory."""
    cache_path = tmp_path / ".bioimage-mcp" / "cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


class TestIntrospectionCache:
    """Tests for IntrospectionCache class."""

    def test_cache_hit_returns_cached_result(self, cache_dir, sample_function_metadata):
        """Cache hit: should return cached result without running discovery.

        When cached results exist for a given adapter/prefix/lockfile_hash,
        the cache should return those results immediately.
        """
        cache = IntrospectionCache(cache_dir)
        adapter_name = "python-introspector"
        prefix = "skimage-filters"
        lockfile_hash = "abc123"

        # Store results in cache
        cache.put(adapter_name, prefix, lockfile_hash, sample_function_metadata)

        # Retrieve from cache
        cached_results = cache.get(adapter_name, prefix, lockfile_hash)

        # Should return the same results
        assert cached_results is not None
        assert len(cached_results) == 2
        assert cached_results[0].name == "gaussian_blur"
        assert cached_results[1].name == "sobel"

    def test_cache_miss_returns_none(self, cache_dir):
        """Cache miss: should return None when no cached result exists.

        When no cached results exist for the given key, the cache should
        return None, indicating that discovery needs to run.
        """
        cache = IntrospectionCache(cache_dir)
        adapter_name = "python-introspector"
        prefix = "skimage-filters"
        lockfile_hash = "abc123"

        # Try to retrieve from empty cache
        cached_results = cache.get(adapter_name, prefix, lockfile_hash)

        # Should return None (cache miss)
        assert cached_results is None

    def test_lockfile_invalidation_returns_none(self, cache_dir, sample_function_metadata):
        """Lockfile invalidation: should ignore cache when lockfile hash changes.

        When the lockfile hash changes (indicating environment has been updated),
        the cache should treat this as a cache miss even if results exist for
        the old lockfile hash.
        """
        cache = IntrospectionCache(cache_dir)
        adapter_name = "python-introspector"
        prefix = "skimage-filters"
        old_lockfile_hash = "abc123"
        new_lockfile_hash = "def456"

        # Store results with old lockfile hash
        cache.put(adapter_name, prefix, old_lockfile_hash, sample_function_metadata)

        # Try to retrieve with new lockfile hash
        cached_results = cache.get(adapter_name, prefix, new_lockfile_hash)

        # Should return None (cache invalidated due to lockfile change)
        assert cached_results is None

    def test_cache_stores_multiple_adapters_independently(
        self, cache_dir, sample_function_metadata
    ):
        """Cache should store results for different adapters independently.

        Different adapters with the same prefix should not interfere with
        each other's cached results.
        """
        cache = IntrospectionCache(cache_dir)
        adapter1 = "python-introspector"
        adapter2 = "fiji-introspector"
        prefix = "filters"
        lockfile_hash = "abc123"

        # Store results for adapter1
        cache.put(adapter1, prefix, lockfile_hash, sample_function_metadata)

        # Retrieve for adapter2 (should be cache miss)
        cached_results = cache.get(adapter2, prefix, lockfile_hash)

        # Should return None (different adapter)
        assert cached_results is None

    def test_cache_stores_multiple_prefixes_independently(
        self, cache_dir, sample_function_metadata
    ):
        """Cache should store results for different prefixes independently.

        Different prefixes with the same adapter should not interfere with
        each other's cached results.
        """
        cache = IntrospectionCache(cache_dir)
        adapter = "python-introspector"
        prefix1 = "skimage-filters"
        prefix2 = "skimage-morphology"
        lockfile_hash = "abc123"

        # Store results for prefix1
        cache.put(adapter, prefix1, lockfile_hash, sample_function_metadata)

        # Retrieve for prefix2 (should be cache miss)
        cached_results = cache.get(adapter, prefix2, lockfile_hash)

        # Should return None (different prefix)
        assert cached_results is None

    def test_cache_persistence_across_instances(self, cache_dir, sample_function_metadata):
        """Cache should persist results across different IntrospectionCache instances.

        Results stored by one cache instance should be retrievable by another
        instance using the same cache directory.
        """
        adapter_name = "python-introspector"
        prefix = "skimage-filters"
        lockfile_hash = "abc123"

        # Store with first cache instance
        cache1 = IntrospectionCache(cache_dir)
        cache1.put(adapter_name, prefix, lockfile_hash, sample_function_metadata)

        # Retrieve with second cache instance
        cache2 = IntrospectionCache(cache_dir)
        cached_results = cache2.get(adapter_name, prefix, lockfile_hash)

        # Should return the same results
        assert cached_results is not None
        assert len(cached_results) == 2
        assert cached_results[0].name == "gaussian_blur"
