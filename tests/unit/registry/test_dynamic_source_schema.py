"""Unit tests for DynamicSource schema (T001)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from bioimage_mcp.registry.manifest_schema import DynamicSource, ToolManifest


class TestDynamicSourceSchema:
    """Test DynamicSource model and integration with ToolManifest."""

    def test_dynamic_source_minimal(self) -> None:
        """Test DynamicSource with minimal required fields."""
        source = DynamicSource(
            adapter="skimage",
            prefix="skimage",
            modules=["skimage.filters"],
        )

        assert source.adapter == "skimage"
        assert source.prefix == "skimage"
        assert source.modules == ["skimage.filters"]
        assert source.include_patterns == ["*"]
        assert source.exclude_patterns == ["_*", "test_*"]

    def test_dynamic_source_custom_patterns(self) -> None:
        """Test DynamicSource with custom include/exclude patterns."""
        source = DynamicSource(
            adapter="phasorpy",
            prefix="phasor",
            modules=["phasorpy.phasor"],
            include_patterns=["plot_*", "compute_*"],
            exclude_patterns=["_*", "deprecated_*"],
        )

        assert source.include_patterns == ["plot_*", "compute_*"]
        assert source.exclude_patterns == ["_*", "deprecated_*"]

    def test_dynamic_source_multiple_modules(self) -> None:
        """Test DynamicSource with multiple modules."""
        source = DynamicSource(
            adapter="scipy_ndimage",
            prefix="scipy.ndimage",
            modules=["scipy.ndimage.filters", "scipy.ndimage.morphology"],
        )

        assert len(source.modules) == 2
        assert "scipy.ndimage.filters" in source.modules
        assert "scipy.ndimage.morphology" in source.modules

    def test_tool_manifest_with_dynamic_sources(self) -> None:
        """Test ToolManifest can include dynamic_sources field."""
        manifest_data = {
            "manifest_version": "0.0",
            "tool_id": "tools.base",
            "tool_version": "0.1.0",
            "env_id": "bioimage-mcp-base",
            "entrypoint": "bioimage_mcp_base.entrypoint",
            "manifest_path": Path("/fake/path"),
            "manifest_checksum": "abc123",
            "dynamic_sources": [
                {
                    "adapter": "skimage",
                    "prefix": "skimage",
                    "modules": ["skimage.filters"],
                }
            ],
        }

        manifest = ToolManifest(**manifest_data)
        assert len(manifest.dynamic_sources) == 1
        assert manifest.dynamic_sources[0].adapter == "skimage"

    def test_tool_manifest_dynamic_sources_defaults_to_empty(self) -> None:
        """Test ToolManifest dynamic_sources defaults to empty list."""
        manifest_data = {
            "manifest_version": "0.0",
            "tool_id": "tools.base",
            "tool_version": "0.1.0",
            "env_id": "bioimage-mcp-base",
            "entrypoint": "bioimage_mcp_base.entrypoint",
            "manifest_path": Path("/fake/path"),
            "manifest_checksum": "abc123",
        }

        manifest = ToolManifest(**manifest_data)
        assert manifest.dynamic_sources == []

    def test_dynamic_source_requires_adapter(self) -> None:
        """Test DynamicSource fails without adapter field."""
        with pytest.raises(ValidationError):
            DynamicSource(
                prefix="skimage",
                modules=["skimage.filters"],
            )

    def test_dynamic_source_requires_prefix(self) -> None:
        """Test DynamicSource fails without prefix field."""
        with pytest.raises(ValidationError):
            DynamicSource(
                adapter="skimage",
                modules=["skimage.filters"],
            )

    def test_dynamic_source_requires_modules(self) -> None:
        """Test DynamicSource fails without modules field."""
        with pytest.raises(ValidationError):
            DynamicSource(
                adapter="skimage",
                prefix="skimage",
            )
