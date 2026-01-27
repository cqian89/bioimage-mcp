"""
Unit tests for PhasorPy adapter manifest configuration.
"""

from pathlib import Path
from unittest.mock import patch

import yaml

from bioimage_mcp.registry.loader import load_manifest_file
from bioimage_mcp.registry.manifest_schema import Function


def test_phasorpy_adapter_discovery_via_manifest(tmp_path):
    """Test that PhasorPy adapter is used when configured in manifest."""
    # Create temp manifest
    manifest_path = tmp_path / "manifest.yaml"
    manifest_data = {
        "manifest_version": "0.0",
        "tool_id": "test.tool",
        "tool_version": "0.1.0",
        "name": "Test Tool",
        "description": "Test Tool",
        "env_id": "bioimage-mcp-test",
        "entrypoint": "test_entrypoint",
        "dynamic_sources": [
            {
                "adapter": "phasorpy",
                "prefix": "phasorpy",
                "modules": ["phasorpy.phasor", "phasorpy.io"],
            }
        ],
    }
    manifest_path.write_text(yaml.dump(manifest_data))

    mock_function = Function(
        fn_id="test.tool.phasorpy.phasor.phasor_from_signal",
        tool_id="test.tool",
        name="phasor_from_signal",
        description="Convert signal to phasor coordinates.",
    )

    with patch(
        "bioimage_mcp.registry.loader.DiscoveryEngine.discover", return_value=([mock_function], [])
    ):
        manifest, diag = load_manifest_file(manifest_path)

        assert manifest is not None
        assert diag is None

        # Check for discovered function
        function_ids = [f.fn_id for f in manifest.functions]
        assert "test.tool.phasorpy.phasor.phasor_from_signal" in function_ids


def test_base_manifest_contains_phasorpy_config():
    """Test that tools/base/manifest.yaml contains correct PhasorPy adapter configuration."""
    manifest_path = Path(__file__).parent.parent.parent.parent / "tools" / "base" / "manifest.yaml"

    assert manifest_path.exists(), f"Base manifest not found at {manifest_path}"

    with open(manifest_path) as f:
        manifest_data = yaml.safe_load(f)

    # Check that dynamic_sources exists
    assert "dynamic_sources" in manifest_data
    dynamic_sources = manifest_data["dynamic_sources"]

    # Find phasorpy adapter config
    phasorpy_config = None
    for source in dynamic_sources:
        if source.get("adapter") == "phasorpy":
            phasorpy_config = source
            break

    assert phasorpy_config is not None, "PhasorPy adapter not found in dynamic_sources"

    # Verify adapter name
    assert phasorpy_config["adapter"] == "phasorpy"

    # Verify prefix
    assert phasorpy_config["prefix"] == "phasorpy"

    # Verify modules list
    expected_modules = [
        "phasorpy.phasor",
        "phasorpy.lifetime",
        "phasorpy.plot",
        "phasorpy.filter",
        "phasorpy.cursor",
        "phasorpy.component",
    ]
    assert phasorpy_config["modules"] == expected_modules, (
        f"Expected modules {expected_modules}, got {phasorpy_config['modules']}"
    )

    # Verify include/exclude patterns (if present)
    if "include_patterns" in phasorpy_config:
        assert "*" in phasorpy_config["include_patterns"]

    if "exclude_patterns" in phasorpy_config:
        assert "_*" in phasorpy_config["exclude_patterns"]
        assert "test_*" in phasorpy_config["exclude_patterns"]
