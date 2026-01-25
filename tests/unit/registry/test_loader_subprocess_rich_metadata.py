from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from bioimage_mcp.registry.loader import load_manifest_file


@pytest.fixture
def mock_manifest(tmp_path):
    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "test.tool",
        "tool_version": "1.0.0",
        "name": "Test Tool",
        "description": "Test tool description",
        "env_id": "bioimage-mcp-test",
        "entrypoint": "entrypoint.py",
        "dynamic_sources": [
            {
                "adapter": "scipy",
                "prefix": "scipy",
                "modules": ["scipy.ndimage"],
            }
        ],
        "functions": [],
    }
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.dump(manifest_data))
    return manifest_path


def test_loader_subprocess_rich_metadata(mock_manifest):
    # Mock execute_tool to return a rich meta.list response
    mock_response = {
        "ok": True,
        "result": {
            "functions": [
                {
                    "fn_id": "scipy.ndimage.gaussian_filter",
                    "name": "gaussian_filter",
                    "module": "scipy.ndimage",
                    "summary": "Multidimensional Gaussian filter.",
                    "description": "Multidimensional Gaussian filter.\nDetailed description here.",
                    "io_pattern": "image_to_image",
                    "parameters": {
                        "sigma": {
                            "name": "sigma",
                            "type": "number",
                            "description": "Standard deviation for Gaussian kernel.",
                            "default": 1.0,
                            "required": False,
                        }
                    },
                    "returns": "ndarray",
                    "source_adapter": "scipy_ndimage",
                }
            ],
            "tool_version": "1.0.0",
            "introspection_source": "dynamic_discovery",
        },
    }

    # We need to patch execute_tool in bioimage_mcp.registry.loader
    # Patch discover_functions to raise ValueError("Unknown adapter") to trigger subprocess fallback
    with (
        patch("bioimage_mcp.registry.loader.execute_tool") as mock_execute,
        patch(
            "bioimage_mcp.registry.loader.discover_functions",
            side_effect=ValueError("Unknown adapter"),
        ),
    ):
        mock_execute.return_value = (mock_response, "logs", 0)

        manifest, diag = load_manifest_file(mock_manifest)

        assert manifest is not None
        assert len(manifest.functions) == 1

        fn = manifest.functions[0]
        # Tool ID prefix is applied by loader
        assert fn.fn_id == "test.tool.scipy.ndimage.gaussian_filter"
        assert "sigma" in fn.params_schema["properties"]
        assert fn.params_schema["properties"]["sigma"]["type"] == "number"
        assert fn.params_schema["properties"]["sigma"]["default"] == 1.0

        # Source adapter is prefixed with subprocess:
        assert fn.introspection_source == "subprocess:scipy_ndimage"
        assert fn.description == "Multidimensional Gaussian filter.\nDetailed description here."
