"""
Unit tests for dynamic discovery engine.

Tests the discovery.py module that coordinates adapter-based function discovery
from dynamic_sources in tool manifests.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern
from bioimage_mcp.registry.manifest_schema import DynamicSource, ToolManifest


class TestDiscoverFunctions:
    """Test cases for discover_functions orchestration."""

    def test_discover_functions_with_single_source(self):
        """discover_functions should call adapter for single dynamic source and return results."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create a mock adapter
        mock_adapter = Mock()
        mock_adapter.discover.return_value = [
            FunctionMetadata(
                name="test_func",
                module="test_module",
                qualified_name="test_module.test_func",
                fn_id="test-adapter.test_func",
                source_adapter="test-adapter",
                description="A test function",
                io_pattern=IOPattern.IMAGE_TO_IMAGE,
            )
        ]

        # Create a minimal manifest with one dynamic source
        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(
                    adapter="test-adapter",
                    prefix="test",
                    modules=["test_module"],
                )
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        # Call discover_functions with adapter registry
        adapter_registry = {"test-adapter": mock_adapter}
        results = discover_functions(manifest, adapter_registry)

        # Verify adapter was called with correct config
        assert mock_adapter.discover.call_count == 1
        call_args = mock_adapter.discover.call_args[0][0]
        assert call_args["adapter"] == "test-adapter"
        assert call_args["prefix"] == "test"
        assert call_args["modules"] == ["test_module"]

        # Verify results
        assert len(results) == 1
        assert results[0].fn_id == "test-adapter.test_func"
        assert results[0].source_adapter == "test-adapter"

    def test_discover_functions_with_multiple_sources(self):
        """discover_functions should call each adapter and aggregate results."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create two mock adapters
        adapter1 = Mock()
        adapter1.discover.return_value = [
            FunctionMetadata(
                name="func1",
                module="module1",
                qualified_name="module1.func1",
                fn_id="adapter1.func1",
                source_adapter="adapter1",
            )
        ]

        adapter2 = Mock()
        adapter2.discover.return_value = [
            FunctionMetadata(
                name="func2",
                module="module2",
                qualified_name="module2.func2",
                fn_id="adapter2.func2",
                source_adapter="adapter2",
            )
        ]

        # Create manifest with multiple dynamic sources
        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(adapter="adapter1", prefix="a1", modules=["module1"]),
                DynamicSource(adapter="adapter2", prefix="a2", modules=["module2"]),
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        # Call discover_functions with both adapters
        adapter_registry = {"adapter1": adapter1, "adapter2": adapter2}
        results = discover_functions(manifest, adapter_registry)

        # Verify both adapters were called
        assert adapter1.discover.call_count == 1
        assert adapter2.discover.call_count == 1

        # Verify results aggregated
        assert len(results) == 2
        fn_ids = {r.fn_id for r in results}
        assert fn_ids == {"adapter1.func1", "adapter2.func2"}

    def test_discover_functions_with_no_dynamic_sources(self):
        """discover_functions should return empty list when no dynamic_sources."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create manifest without dynamic sources
        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[],  # Empty
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        # Call discover_functions
        results = discover_functions(manifest, {})

        # Verify empty results
        assert results == []

    def test_discover_functions_raises_on_unknown_adapter(self):
        """discover_functions should raise error for unknown adapter type."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create manifest with unknown adapter
        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(
                    adapter="unknown-adapter",  # Not in registry
                    prefix="test",
                    modules=["test_module"],
                )
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        # Should raise error
        with pytest.raises(ValueError, match="Unknown adapter.*unknown-adapter"):
            discover_functions(manifest, {})


class TestCacheIntegration:
    """Test cases for cache integration in discover_functions."""

    def test_discover_uses_cache_on_hit(self, tmp_path):
        """discover_functions should return cached results when cache hit occurs."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create a mock adapter that should NOT be called
        mock_adapter = Mock()
        mock_adapter.discover.return_value = [
            FunctionMetadata(
                name="should_not_appear",
                module="wrong",
                qualified_name="wrong.should_not_appear",
                fn_id="test.should_not_appear",
                source_adapter="test-adapter",
            )
        ]

        # Create manifest with lockfile
        lockfile_path = tmp_path / "envs" / "bioimage-mcp-test.lock.yml"
        lockfile_path.parent.mkdir(parents=True)
        lockfile_path.write_text("dependencies:\n  - python=3.13\n")

        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(
                    adapter="test-adapter",
                    prefix="test",
                    modules=["test_module"],
                )
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        # Pre-populate cache
        import hashlib

        from bioimage_mcp.registry.dynamic.cache import IntrospectionCache

        cache_dir = tmp_path / ".bioimage-mcp" / "cache"
        cache = IntrospectionCache(cache_dir)
        lockfile_content = lockfile_path.read_text()
        lockfile_hash = hashlib.sha256(lockfile_content.encode()).hexdigest()[:16]

        cached_results = [
            FunctionMetadata(
                name="cached_func",
                module="test_module",
                qualified_name="test_module.cached_func",
                fn_id="test.cached_func",
                source_adapter="test-adapter",
            )
        ]
        composite_key = f"{lockfile_hash}:{manifest.manifest_checksum[:16]}"
        cache.put("test-adapter", "test", composite_key, cached_results)

        # Call discover_functions with cache and project_root
        adapter_registry = {"test-adapter": mock_adapter}
        results = discover_functions(manifest, adapter_registry, cache=cache, project_root=tmp_path)

        # Verify adapter was NOT called (cache hit)
        assert mock_adapter.discover.call_count == 0

        # Verify cached results returned
        assert len(results) == 1
        assert results[0].fn_id == "test.cached_func"

    def test_discover_calls_adapter_on_cache_miss(self, tmp_path):
        """discover_functions should call adapter when cache miss occurs."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create a mock adapter
        mock_adapter = Mock()
        mock_adapter.discover.return_value = [
            FunctionMetadata(
                name="fresh_func",
                module="test_module",
                qualified_name="test_module.fresh_func",
                fn_id="test.fresh_func",
                source_adapter="test-adapter",
            )
        ]

        # Create manifest with lockfile
        lockfile_path = tmp_path / "envs" / "bioimage-mcp-test.lock.yml"
        lockfile_path.parent.mkdir(parents=True)
        lockfile_path.write_text("dependencies:\n  - python=3.13\n")

        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(
                    adapter="test-adapter",
                    prefix="test",
                    modules=["test_module"],
                )
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        # Create empty cache
        from bioimage_mcp.registry.dynamic.cache import IntrospectionCache

        cache_dir = tmp_path / ".bioimage-mcp" / "cache"
        cache = IntrospectionCache(cache_dir)

        # Call discover_functions with cache and project_root
        adapter_registry = {"test-adapter": mock_adapter}
        results = discover_functions(manifest, adapter_registry, cache=cache, project_root=tmp_path)

        # Verify adapter WAS called (cache miss)
        assert mock_adapter.discover.call_count == 1

        # Verify fresh results returned
        assert len(results) == 1
        assert results[0].fn_id == "test.fresh_func"

    def test_discover_stores_results_in_cache(self, tmp_path):
        """discover_functions should store adapter results in cache after discovery."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create a mock adapter
        mock_adapter = Mock()
        discovered_results = [
            FunctionMetadata(
                name="new_func",
                module="test_module",
                qualified_name="test_module.new_func",
                fn_id="test.new_func",
                source_adapter="test-adapter",
            )
        ]
        mock_adapter.discover.return_value = discovered_results

        # Create manifest with lockfile
        lockfile_path = tmp_path / "envs" / "bioimage-mcp-test.lock.yml"
        lockfile_path.parent.mkdir(parents=True)
        lockfile_path.write_text("dependencies:\n  - python=3.13\n")

        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(
                    adapter="test-adapter",
                    prefix="test",
                    modules=["test_module"],
                )
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        # Create empty cache
        import hashlib

        from bioimage_mcp.registry.dynamic.cache import IntrospectionCache

        cache_dir = tmp_path / ".bioimage-mcp" / "cache"
        cache = IntrospectionCache(cache_dir)

        # Call discover_functions
        adapter_registry = {"test-adapter": mock_adapter}
        results = discover_functions(manifest, adapter_registry, cache=cache, project_root=tmp_path)

        # Verify results were stored in cache
        lockfile_content = lockfile_path.read_text()
        lockfile_hash = hashlib.sha256(lockfile_content.encode()).hexdigest()[:16]
        composite_key = f"{lockfile_hash}:{manifest.manifest_checksum[:16]}"
        cached_results = cache.get("test-adapter", "test", composite_key)

        assert cached_results is not None
        assert len(cached_results) == 1
        assert cached_results[0].fn_id == "test.new_func"

    def test_discover_invalidates_on_manifest_change(self, tmp_path):
        """discover_functions should trigger cache miss when manifest checksum changes."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        # Create a mock adapter
        mock_adapter = Mock()
        mock_adapter.discover.return_value = [
            FunctionMetadata(
                name="fresh_func",
                module="test_module",
                qualified_name="test_module.fresh_func",
                fn_id="test.fresh_func",
                source_adapter="test-adapter",
            )
        ]

        # Create manifest with lockfile
        lockfile_path = tmp_path / "envs" / "bioimage-mcp-test.lock.yml"
        lockfile_path.parent.mkdir(parents=True)
        lockfile_path.write_text("lockfile content")

        manifest_a = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(adapter="test-adapter", prefix="test", modules=["test_module"])
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="checksum_A",
        )

        # Pre-populate cache for checksum_A
        import hashlib
        from bioimage_mcp.registry.dynamic.cache import IntrospectionCache

        cache_dir = tmp_path / ".bioimage-mcp" / "cache"
        cache = IntrospectionCache(cache_dir)
        lockfile_hash = hashlib.sha256(lockfile_path.read_text().encode()).hexdigest()[:16]
        composite_key_a = f"{lockfile_hash}:checksum_A"

        cached_results = [
            FunctionMetadata(
                name="cached_func",
                module="test_module",
                qualified_name="test_module.cached_func",
                fn_id="test.cached_func",
                source_adapter="test-adapter",
            )
        ]
        cache.put("test-adapter", "test", composite_key_a, cached_results)

        # Call discover_functions with different manifest checksum (checksum_B)
        manifest_b = manifest_a.model_copy(update={"manifest_checksum": "checksum_B"})
        adapter_registry = {"test-adapter": mock_adapter}
        results = discover_functions(
            manifest_b, adapter_registry, cache=cache, project_root=tmp_path
        )

        # Verify adapter WAS called (cache miss due to checksum change)
        assert mock_adapter.discover.call_count == 1
        assert results[0].fn_id == "test.fresh_func"

        # Verify new cache entry created for checksum_B
        composite_key_b = f"{lockfile_hash}:checksum_B"
        cached_results_b = cache.get("test-adapter", "test", composite_key_b)
        assert cached_results_b is not None
        assert cached_results_b[0].fn_id == "test.fresh_func"

    def test_discover_functions_caches_without_lockfile(self, tmp_path):
        """discover_functions should cache results even when lockfile is missing."""
        from bioimage_mcp.registry.dynamic.discovery import discover_functions

        mock_adapter = Mock()
        mock_adapter.discover.return_value = [
            FunctionMetadata(
                name="func",
                module="m",
                qualified_name="m.f",
                fn_id="t.f",
                source_adapter="test-adapter",
            )
        ]

        manifest = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="0.1.0",
            env_id="bioimage-mcp-test",
            entrypoint="test_module",
            dynamic_sources=[
                DynamicSource(adapter="test-adapter", prefix="test", modules=["test_module"])
            ],
            manifest_path=Path("/fake/manifest.yaml"),
            manifest_checksum="abc123",
        )

        from bioimage_mcp.registry.dynamic.cache import IntrospectionCache

        cache_dir = tmp_path / ".bioimage-mcp" / "cache"
        cache = IntrospectionCache(cache_dir)

        # Call without project_root (so no lockfile found)
        adapter_registry = {"test-adapter": mock_adapter}
        results = discover_functions(manifest, adapter_registry, cache=cache, project_root=None)

        assert mock_adapter.discover.call_count == 1

        # Verify cache was written with 'no-lockfile' sentinel
        composite_key = f"no-lockfile:{manifest.manifest_checksum[:16]}"
        cached_results = cache.get("test-adapter", "test", composite_key)
        assert cached_results is not None
        assert cached_results[0].fn_id == "t.f"

        # Second call should hit cache
        mock_adapter.reset_mock()
        results2 = discover_functions(manifest, adapter_registry, cache=cache, project_root=None)
        assert mock_adapter.discover.call_count == 0
        assert results2 == results
