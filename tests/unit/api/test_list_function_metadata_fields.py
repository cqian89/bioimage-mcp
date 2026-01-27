from __future__ import annotations

import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import init_schema


def test_list_function_metadata_fields():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    service = DiscoveryService(conn)

    # 1. Upsert a tool
    service.upsert_tool(
        tool_id="cellpose",
        name="Cellpose",
        description="Cellpose tool",
        tool_version="2.0",
        env_id="bioimage-mcp-cellpose",
        manifest_path="/path/to/manifest.yaml",
        installed=True,
        available=True,
    )

    # 2. Upsert a function with module, io_pattern, introspection_source
    service.upsert_function(
        fn_id="cellpose.models",
        tool_id="cellpose",
        name="models",
        description="Cellpose models",
        tags=["segmentation"],
        inputs=[],
        outputs=[],
        params_schema={"type": "object", "properties": {}},
        module="cellpose.models",
        io_pattern="pure_constructor",
        introspection_source="python_api",
    )

    # 3. Call list_tools (which handles tools/list MCP command)
    result = service.list_tools(path="cellpose.models")

    assert "items" in result
    assert len(result["items"]) == 1
    node = result["items"][0]

    assert node["id"] == "cellpose.models"
    assert node["module"] == "cellpose.models"
    assert node["io_pattern"] == "pure_constructor"
    assert node["introspection_source"] == "python_api"


def test_list_describe_alignment(monkeypatch, tmp_path):
    artifacts_root = tmp_path / "artifacts"
    tools_root = tmp_path / "tools"
    tools_root.mkdir()

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    monkeypatch.setattr("bioimage_mcp.api.discovery.load_config", lambda: config)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    service = DiscoveryService(conn)
    fn_id = "cellpose.models"

    # 1. Create a dummy manifest and upsert tool
    manifest_path = tools_root / "cellpose" / "manifest.yaml"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        """
manifest_version: "1.0"
tool_id: cellpose
tool_version: "2.0"
name: Cellpose
env_id: bioimage-mcp-cellpose
entrypoint: entry.py
functions:
  - fn_id: cellpose.models
    tool_id: cellpose
    name: models
    description: models
    inputs: []
    outputs: []
    params_schema: {"type": "object", "properties": {}}

"""
    )

    from bioimage_mcp.registry.loader import _MANIFEST_CACHE

    _MANIFEST_CACHE.clear()

    from bioimage_mcp.registry.loader import load_manifests

    manifests, _ = load_manifests(config.tool_manifest_roots)

    service.upsert_tool(
        tool_id="cellpose",
        name="Cellpose",
        description="Cellpose tool",
        tool_version="2.0",
        env_id="cellpose-env",
        manifest_path=str(manifest_path),
        installed=True,
        available=True,
    )

    # 2. Upsert a function with introspection_source="ast"
    service.upsert_function(
        fn_id=fn_id,
        tool_id="cellpose",
        name="models",
        description="Cellpose models",
        tags=["segmentation"],
        inputs=[],
        outputs=[],
        params_schema={"type": "object", "properties": {}},
        module="cellpose.models",
        io_pattern="pure_constructor",
        introspection_source="ast",
    )

    # 3. Verify list shows "ast"
    res1 = service.list_tools(path=fn_id)
    assert res1["items"][0]["introspection_source"] == "ast"

    # 4. Mock execute_tool and hashes to return "python_api" enrichment
    def _fake_execute_tool(*args, **kwargs):
        return (
            {
                "ok": True,
                "result": {
                    "params_schema": {
                        "type": "object",
                        "properties": {"enriched": {"type": "boolean"}},
                    },
                    "tool_version": "2.0",
                    "introspection_source": "python_api",
                },
            },
            "ok",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.discovery.execute_tool", _fake_execute_tool)
    monkeypatch.setattr("bioimage_mcp.api.discovery._compute_env_lock_hash", lambda *a: "env")
    monkeypatch.setattr("bioimage_mcp.api.discovery._compute_source_hash", lambda *a, **k: "src")

    # 5. Call describe_function (triggers enrichment)
    desc = service.describe_function(fn_id)
    assert desc["meta"]["introspection_source"] == "python_api"

    # 6. Verify list now shows "python_api" (synchronized)
    res2 = service.list_tools(path=fn_id)
    assert res2["items"][0]["introspection_source"] == "python_api"
