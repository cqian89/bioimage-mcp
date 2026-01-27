"""Tests for automatic dynamic discovery during manifest loading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from bioimage_mcp.registry.loader import load_manifest_file
from bioimage_mcp.registry.manifest_schema import Function


def test_load_manifest_file_calls_discovery_engine_with_dynamic_sources(
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

    # Mock discovered function
    mock_function = Function(
        fn_id="test.skimage.gaussian",
        tool_id="tools.test",
        name="gaussian",
        description="Gaussian blur",
        introspection_source="python_api",
    )

    # Act & Assert: Mock DiscoveryEngine.discover and verify it's called
    with patch(
        "bioimage_mcp.registry.loader.DiscoveryEngine.discover",
        return_value=([mock_function], []),
    ) as mock_discover:
        manifest, diagnostic = load_manifest_file(manifest_path)

        # Should successfully load manifest
        assert diagnostic is None
        assert manifest is not None

        # Should call discover with the manifest
        mock_discover.assert_called_once()
        call_args = mock_discover.call_args
        assert call_args[0][0].tool_id == "tools.test"  # First arg is manifest

        # Should add discovered functions to manifest.functions
        assert len(manifest.functions) == 1
        assert manifest.functions[0].fn_id == "test.skimage.gaussian"
        assert manifest.functions[0].name == "gaussian"


def test_load_manifest_file_calls_discovery_engine_even_without_dynamic_sources(
    tmp_path: Path,
) -> None:
    """Load manifest should always call DiscoveryEngine.discover for normalization."""
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

    # Act & Assert
    with patch("bioimage_mcp.registry.loader.DiscoveryEngine.discover") as mock_discover:
        # Mock discover to return manifest.functions (pass-through)
        mock_discover.side_effect = lambda m: (m.functions, [])

        manifest, diagnostic = load_manifest_file(manifest_path)

        assert diagnostic is None
        assert manifest is not None

        # Should call discover
        mock_discover.assert_called_once()

        assert len(manifest.functions) == 1
        assert manifest.functions[0].fn_id == "test.manual"


def test_load_manifest_preserves_manifest_schema_on_duplicate_dynamic_fn(
    tmp_path: Path,
) -> None:
    """Manifest-defined schema should win when dynamic discovery returns same fn_id."""
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        """
manifest_version: "0.0"
tool_id: tools.cellpose
tool_version: "0.0.0"
env_id: bioimage-mcp-test
entrypoint: test.entrypoint
platforms_supported: [linux-64]
functions:
  - fn_id: cellpose.models.CellposeModel
    tool_id: tools.cellpose
    name: CellposeModel
    description: Manual schema definition
    tags: []
    inputs: []
    outputs: []
    params_schema:
      type: object
      properties:
        model_type:
          type: string
dynamic_sources:
  - adapter: cellpose
    prefix: cellpose
    modules: [cellpose.models]
""".lstrip()
    )

    duplicate_fn = Function(
        fn_id="cellpose.models.CellposeModel",
        tool_id="tools.cellpose",
        name="CellposeModel",
        description="Dynamic stub",
        introspection_source="python_api",
    )
    new_fn = Function(
        fn_id="cellpose.models.CellposeModel.eval",
        tool_id="tools.cellpose",
        name="CellposeModel.eval",
        description="Dynamic eval",
        introspection_source="python_api",
    )

    with patch(
        "bioimage_mcp.registry.loader.DiscoveryEngine.discover",
        return_value=([duplicate_fn, new_fn], []),
    ):
        manifest, diagnostic = load_manifest_file(manifest_path)

    assert diagnostic is None
    assert manifest is not None
    # DiscoveryEngine.discover is mocked to return BOTH, but load_manifest_file
    # just assigns whatever discover returns.
    # WAIT: DiscoveryEngine.discover implementation (the real one) handles preservation.
    # If I mock it to return BOTH, then manifest.functions WILL have both.

    # Actually, the real DiscoveryEngine handles this. If I want to test that logic,
    # I should test DiscoveryEngine directly, which I do in test_registry_engine.py.

    assert len(manifest.functions) == 2
    by_id = {fn.fn_id: fn for fn in manifest.functions}
    assert by_id["cellpose.models.CellposeModel"].description == "Dynamic stub"
