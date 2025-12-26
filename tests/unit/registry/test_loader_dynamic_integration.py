"""Tests for automatic dynamic discovery during manifest loading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from bioimage_mcp.registry.dynamic.models import FunctionMetadata
from bioimage_mcp.registry.loader import load_manifest_file


def test_load_manifest_file_calls_discover_functions_with_dynamic_sources(
    tmp_path: Path,
) -> None:
    """Load manifest with dynamic_sources should automatically discover functions."""
    # Arrange: Create manifest file with dynamic_sources
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        """
manifest_version: "0.0"
tool_id: tools.test
tool_version: "0.0.0"
env_id: bioimage-mcp-test
entrypoint: test.entrypoint
platforms_supported: [linux-64]
functions: []
dynamic_sources:
  - adapter: python_api
    prefix: skimage
    modules: [skimage.filters]
""".lstrip()
    )

    # Mock discovered function metadata
    mock_function = FunctionMetadata(
        fn_id="skimage.gaussian",
        name="gaussian",
        module="skimage.filters",
        qualified_name="skimage.filters.gaussian",
        source_adapter="python_api",
        description="Gaussian blur",
        tags=[],
    )

    # Act & Assert: Mock discover_functions and verify it's called
    with patch(
        "bioimage_mcp.registry.loader.discover_functions",
        return_value=[mock_function],
    ) as mock_discover:
        manifest, diagnostic = load_manifest_file(manifest_path)

        # Should successfully load manifest
        assert diagnostic is None
        assert manifest is not None

        # Should call discover_functions with the manifest
        mock_discover.assert_called_once()
        call_args = mock_discover.call_args
        assert call_args[0][0].tool_id == "tools.test"  # First arg is manifest

        # Should add discovered functions to manifest.functions
        assert len(manifest.functions) == 1
        assert manifest.functions[0].fn_id == "skimage.gaussian"
        assert manifest.functions[0].tool_id == "tools.test"
        assert manifest.functions[0].name == "gaussian"
        assert manifest.functions[0].introspection_source == "python_api"


def test_load_manifest_file_skips_discovery_without_dynamic_sources(
    tmp_path: Path,
) -> None:
    """Load manifest without dynamic_sources should not call discover_functions."""
    # Arrange: Create manifest file WITHOUT dynamic_sources
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        """
manifest_version: "0.0"
tool_id: tools.test
tool_version: "0.0.0"
env_id: bioimage-mcp-test
entrypoint: test.entrypoint
platforms_supported: [linux-64]
functions:
  - fn_id: test.manual
    tool_id: tools.test
    name: manual
    description: Manual function
    tags: []
    inputs: []
    outputs: []
    params_schema:
      type: object
""".lstrip()
    )

    # Act & Assert: Mock discover_functions and verify it's NOT called
    with patch("bioimage_mcp.registry.loader.discover_functions") as mock_discover:
        manifest, diagnostic = load_manifest_file(manifest_path)

        # Should successfully load manifest
        assert diagnostic is None
        assert manifest is not None

        # Should NOT call discover_functions
        mock_discover.assert_not_called()

        # Should only have the manual function
        assert len(manifest.functions) == 1
        assert manifest.functions[0].fn_id == "test.manual"
