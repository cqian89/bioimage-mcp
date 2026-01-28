from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml

from bioimage_mcp.registry.loader import load_manifest_file
from bioimage_mcp.registry.static.inspector import StaticCallable, StaticModuleReport


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


def test_loader_runtime_fallback_rich_metadata(mock_manifest):
    # Mock DiscoveryEngine._runtime_list to return rich metadata
    mock_runtime_functions = [
        {
            "fn_id": "test.tool.scipy.gaussian_filter",
            "name": "gaussian_filter",
            "module": "scipy.ndimage",
            "params_schema": {
                "type": "object",
                "properties": {
                    "sigma": {
                        "type": "number",
                        "description": "Standard deviation for Gaussian kernel.",
                        "default": 1.0,
                    }
                },
                "required": [],
            },
            "tool_version": "1.0.0",
            "introspection_source": "subprocess:scipy_ndimage",
        }
    ]

    # Mock griffe inspector to return a function that will trigger fallback
    mock_report = StaticModuleReport(
        module_name="scipy.ndimage",
        callables=[
            StaticCallable(
                name="gaussian_filter",
                qualified_name="scipy.ndimage.gaussian_filter",
                parameters=[],
            )
        ],
    )

    with (
        # Optional for scipy; runtime list is used directly.
        patch("bioimage_mcp.registry.engine.inspect_module", return_value=mock_report),
        patch(
            "bioimage_mcp.registry.engine.DiscoveryEngine._runtime_list",
            return_value=mock_runtime_functions,
        ),
    ):
        manifest, diag = load_manifest_file(mock_manifest)

        assert manifest is not None
        assert len(manifest.functions) == 1

        fn = manifest.functions[0]
        # Tool ID prefix is applied by loader/engine
        assert fn.fn_id == "test.tool.scipy.gaussian_filter"
        assert "sigma" in fn.params_schema["properties"]
        assert fn.params_schema["properties"]["sigma"]["type"] == "number"
        assert fn.params_schema["properties"]["sigma"]["default"] == 1.0

        # Source adapter is prefixed with runtime:
        assert fn.introspection_source == "runtime:subprocess:scipy_ndimage"
