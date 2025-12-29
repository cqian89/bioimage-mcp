from __future__ import annotations

import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


def test_batch_describe_returns_schemas_and_errors() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.base",
        name="Built-ins",
        description="Built-in functions",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/manifest.yaml",
        available=True,
        installed=True,
    )

    fn_id_a = "base.bioimage_mcp_base.preprocess.gaussian"
    fn_id_b = "base.bioimage_mcp_base.preprocess.median"
    missing_id = "base.missing.function"

    service.upsert_function(
        fn_id=fn_id_a,
        tool_id="tools.base",
        name="Gaussian blur",
        description="Blur an image",
        tags=["image", "filter"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"sigma": {"type": "number"}}},
    )
    service.upsert_function(
        fn_id=fn_id_b,
        tool_id="tools.base",
        name="Median filter",
        description="Median filter",
        tags=["image", "filter"],
        inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
        outputs=[{"name": "output", "artifact_type": "BioImageRef", "required": True}],
        params_schema={"type": "object", "properties": {"radius": {"type": "number"}}},
    )

    result = service.describe_function(fn_ids=[fn_id_a, fn_id_b, missing_id])

    assert set(result.keys()) == {"schemas", "errors"}
    assert set(result["schemas"].keys()) == {fn_id_a, fn_id_b}
    assert set(result["errors"].keys()) == {missing_id}

    for fn_id, schema in result["schemas"].items():
        assert schema["fn_id"] == fn_id
        assert "schema" in schema
    assert isinstance(result["errors"][missing_id], str)
    assert result["errors"][missing_id]

    conn.close()
