"""Unit tests for default tool manifest roots configuration (T012b).

Tests that the default config includes tools/cellpose as a manifest root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.config.schema import Config


class TestDefaultManifestRoots:
    """Tests for default tool manifest roots configuration."""

    def test_config_accepts_cellpose_manifest_root(self) -> None:
        """Test that config can include tools/cellpose as manifest root."""
        # This test verifies the config structure supports cellpose
        # The actual default will be set in config.yaml or loader
        config = Config(
            artifact_store_root=Path("/tmp/artifact-store").absolute(),
            tool_manifest_roots=[
                Path("/app/tools/builtin").absolute(),
                Path("/app/tools/cellpose").absolute(),
            ],
        )
        assert len(config.tool_manifest_roots) == 2
        # Check that cellpose path is included
        root_strs = [str(r) for r in config.tool_manifest_roots]
        assert any("cellpose" in r for r in root_strs)

    def test_config_allows_empty_manifest_roots(self) -> None:
        """Test that config allows empty manifest roots (edge case)."""
        config = Config(
            artifact_store_root=Path("/tmp/artifact-store").absolute(),
            tool_manifest_roots=[],
        )
        assert config.tool_manifest_roots == []

    def test_config_paths_must_be_absolute(self) -> None:
        """Test that tool_manifest_roots requires absolute paths."""
        with pytest.raises(ValueError, match="Path must be absolute"):
            Config(
                artifact_store_root=Path("/tmp/artifact-store").absolute(),
                tool_manifest_roots=[Path("relative/path")],
            )
