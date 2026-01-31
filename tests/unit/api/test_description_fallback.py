from __future__ import annotations
import sqlite3
from unittest.mock import patch, MagicMock
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema
from bioimage_mcp.registry.manifest_schema import ToolManifest, Function, Port


def test_description_fallback_avoids_stuttering():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    # 1. Setup a tool and function in DB
    service.upsert_tool(
        tool_id="test.tool",
        name="Test Tool",
        description="Test",
        tool_version="0.1.0",
        env_id="bioimage-mcp-test",
        manifest_path="/nonexistent/test.yaml",
        available=True,
        installed=True,
    )

    # We'll use a mocked manifest to trigger the manifest logic in describe_function
    fn = Function(
        fn_id="test.fn",
        tool_id="test.tool",
        name="Test Fn",
        description="Test description",
        inputs=[
            Port(name="image", artifact_type="BioImageRef"),  # no description
            Port(name="input", artifact_type="BioImageRef"),  # no description
            Port(name="data", artifact_type="BioImageRef"),  # no description
            Port(name="specific", artifact_type="BioImageRef"),  # no description
        ],
        outputs=[
            Port(name="output", artifact_type="BioImageRef"),  # no description
            Port(name="result", artifact_type="BioImageRef"),  # no description
            Port(name="image", artifact_type="BioImageRef"),  # no description
            Port(name="data", artifact_type="BioImageRef"),  # no description
        ],
    )

    mock_manifest = MagicMock(spec=ToolManifest)
    mock_manifest.tool_id = "test.tool"
    mock_manifest.tool_version = "0.1.0"
    mock_manifest.env_id = "bioimage-mcp-test"
    mock_manifest.functions = [fn]
    mock_manifest.manifest_path = MagicMock()

    with patch("bioimage_mcp.api.discovery.load_manifests", return_value=([mock_manifest], [])):
        with patch("bioimage_mcp.api.discovery.load_config"):
            # We need to make sure the fn is in DB too so describe_function finds the node
            service.upsert_function(
                id="test.fn",
                tool_id="test.tool",
                name="Test Fn",
                description="Test",
                tags=[],
                inputs=[],
                outputs=[],
                params_schema={},
            )

            described = service.describe_function(id="test.fn")

            inputs = described["inputs"]
            outputs = described["outputs"]

            # Check inputs
            assert inputs["image"]["description"] == "Input image"
            assert inputs["input"]["description"] == "Primary input"
            assert inputs["data"]["description"] == "Input data"
            assert inputs["specific"]["description"] == "specific input"

            # Check outputs
            assert outputs["output"]["description"] == "Primary output"
            assert outputs["result"]["description"] == "Primary result"
            assert outputs["image"]["description"] == "Output image"
            assert outputs["data"]["description"] == "Output data"

    conn.close()
