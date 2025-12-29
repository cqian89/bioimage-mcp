from __future__ import annotations

import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


def test_list_tools_paginates_by_cursor() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    for env_name in ["a", "b", "c"]:
        tool_id = f"tools.{env_name}"
        service.upsert_tool(
            tool_id=tool_id,
            name=env_name,
            description=env_name,
            tool_version="0.0.0",
            env_id="bioimage-mcp-base",
            manifest_path=f"/abs/{env_name}.yaml",
            available=True,
            installed=True,
        )
        service.upsert_function(
            fn_id=f"{env_name}.pkg.fn",
            tool_id=tool_id,
            name=f"Fn {env_name}",
            description="",
            tags=[],
            inputs=[],
            outputs=[],
            params_schema={},
        )

    page1 = service.list_tools(limit=2, cursor=None)
    assert [t["full_path"] for t in page1["tools"]] == ["a", "b"]
    assert page1["next_cursor"]

    page2 = service.list_tools(limit=2, cursor=page1["next_cursor"])
    assert [t["full_path"] for t in page2["tools"]] == ["c"]
    conn.close()


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

    page = service.search_functions(keywords="fn", tags=["b"], limit=10, cursor=None)
    assert [f["fn_id"] for f in page["functions"]] == ["fn.two"]
    conn.close()


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

    page = service.search_functions(keywords="fn", io_in="BioImageRef", limit=10, cursor=None)
    assert [f["fn_id"] for f in page["functions"]] == ["fn.in"]

    page2 = service.search_functions(keywords="fn", io_out="LogRef", limit=10, cursor=None)
    assert [f["fn_id"] for f in page2["functions"]] == ["fn.out"]
    conn.close()
