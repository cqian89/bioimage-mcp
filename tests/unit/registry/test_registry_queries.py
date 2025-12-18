from __future__ import annotations

import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


def test_list_tools_paginates_by_cursor() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    for tool_id in ["a", "b", "c"]:
        service.upsert_tool(
            tool_id=tool_id,
            name=tool_id,
            description=tool_id,
            tool_version="0.0.0",
            env_id="bioimage-mcp-base",
            manifest_path=f"/abs/{tool_id}.yaml",
            available=True,
            installed=True,
        )

    page1 = service.list_tools(limit=2, cursor=None)
    assert [t["tool_id"] for t in page1["tools"]] == ["a", "b"]
    assert page1["next_cursor"]

    page2 = service.list_tools(limit=2, cursor=page1["next_cursor"])
    assert [t["tool_id"] for t in page2["tools"]] == ["c"]


def test_search_functions_filters_by_tag() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools",
        name="tools",
        description="tools",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/tools.yaml",
        available=True,
        installed=True,
    )

    service.upsert_function(
        fn_id="fn.one",
        tool_id="tools",
        name="One",
        description="alpha",
        tags=["a"],
        inputs=[],
        outputs=[],
        params_schema={},
    )
    service.upsert_function(
        fn_id="fn.two",
        tool_id="tools",
        name="Two",
        description="beta",
        tags=["b"],
        inputs=[],
        outputs=[],
        params_schema={},
    )

    page = service.search_functions(query="", tags=["b"], limit=10, cursor=None)
    assert [f["fn_id"] for f in page["functions"]] == ["fn.two"]


def test_search_functions_filters_by_io_types() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools",
        name="tools",
        description="tools",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/tools.yaml",
        available=True,
        installed=True,
    )

    service.upsert_function(
        fn_id="fn.in",
        tool_id="tools",
        name="In",
        description="",
        tags=[],
        inputs=[{"name": "x", "artifact_type": "BioImageRef", "required": True}],
        outputs=[],
        params_schema={},
    )
    service.upsert_function(
        fn_id="fn.out",
        tool_id="tools",
        name="Out",
        description="",
        tags=[],
        inputs=[],
        outputs=[{"name": "y", "artifact_type": "LogRef", "required": True}],
        params_schema={},
    )

    page = service.search_functions(query="", io_in="BioImageRef", limit=10, cursor=None)
    assert [f["fn_id"] for f in page["functions"]] == ["fn.in"]

    page2 = service.search_functions(query="", io_out="LogRef", limit=10, cursor=None)
    assert [f["fn_id"] for f in page2["functions"]] == ["fn.out"]
