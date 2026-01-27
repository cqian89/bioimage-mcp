"""
Unit tests for SkimageAdapter manifest configuration.
"""

from unittest.mock import patch

import yaml

from bioimage_mcp.registry.loader import load_manifest_file
from bioimage_mcp.registry.manifest_schema import Function


def test_skimage_adapter_discovery_via_manifest(tmp_path):
    """Test that SkimageAdapter is used when configured in manifest."""
    # Create temp manifest
    manifest_path = tmp_path / "manifest.yaml"
    manifest_data = {
        "manifest_version": "0.0",
        "tool_id": "tools.test",
        "tool_version": "0.1.0",
        "name": "Test Tool",
        "description": "Test Tool",
        "env_id": "bioimage-mcp-test",
        "entrypoint": "test_entrypoint",
        "dynamic_sources": [
            {
                "adapter": "skimage",
                "prefix": "skimage",
                "modules": ["skimage.filters"],
            }
        ],
    }
    manifest_path.write_text(yaml.dump(manifest_data))

    mock_function = Function(
        fn_id="test.skimage.filters.gaussian",
        tool_id="tools.test",
        name="gaussian",
        description="Apply Gaussian filter to image.",
    )

    with patch(
        "bioimage_mcp.registry.loader.DiscoveryEngine.discover", return_value=([mock_function], [])
    ):
        manifest, diag = load_manifest_file(manifest_path)

        assert manifest is not None
        assert diag is None

        # Check for discovered function
        function_ids = [f.fn_id for f in manifest.functions]
        assert "test.skimage.filters.gaussian" in function_ids
