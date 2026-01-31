from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.registry.engine import DiscoveryEngine
from bioimage_mcp.registry.manifest_schema import ToolManifest
from bioimage_mcp.registry.static.inspector import StaticCallable, StaticParameter


@pytest.fixture
def manifest(tmp_path: Path) -> ToolManifest:
    return ToolManifest(
        manifest_version="1.0",
        tool_id="test-tool",
        tool_version="0.1.0",
        env_id="bioimage-mcp-test",
        entrypoint="test.py",
        manifest_path=tmp_path / "manifest.yaml",
        manifest_checksum="abc",
    )


def test_params_schema_has_x_native_type(manifest: ToolManifest) -> None:
    engine = DiscoveryEngine()

    # Mock static callable
    sc = StaticCallable(
        name="segment",
        qualified_name="test.segment",
        parameters=[StaticParameter(name="model", annotation="ObjectRef")],
    )

    # Mock runtime entry with ObjectRef port
    runtime_entry = {"name": "segment", "inputs": [{"name": "model", "artifact_type": "ObjectRef"}]}

    runtime_map = {"test-tool.test.segment": runtime_entry}

    fn = engine._process_callable(manifest, sc, MagicMock(prefix="test"), None, runtime_map)

    assert fn is not None
    props = fn.params_schema["properties"]
    assert "model" in props
    assert props["model"]["x-native-type"] == "object"


def test_params_schema_x_native_type_from_hints(manifest: ToolManifest) -> None:
    engine = DiscoveryEngine()

    sc = StaticCallable(
        name="segment",
        qualified_name="test.segment",
        parameters=[StaticParameter(name="model", annotation="ObjectRef")],
    )

    # Mock runtime entry with ObjectRef port and hints
    runtime_entry = {
        "name": "segment",
        "inputs": [{"name": "model", "artifact_type": "ObjectRef"}],
        "hints": {
            "inputs": {
                "model": {
                    "native_type": "cellpose.models.Cellpose",
                    "type": "ObjectRef",
                    "required": True,
                    "description": "model",
                }
            }
        },
    }

    runtime_map = {"test-tool.test.segment": runtime_entry}

    fn = engine._process_callable(manifest, sc, MagicMock(prefix="test"), None, runtime_map)

    assert fn is not None
    props = fn.params_schema["properties"]
    assert props["model"]["x-native-type"] == "cellpose.models.Cellpose"
