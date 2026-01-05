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
    assert [t["full_path"] for t in page1["items"]] == ["a", "b"]
    assert page1["next_cursor"]

    page2 = service.list_tools(limit=2, cursor=page1["next_cursor"])
    assert [t["full_path"] for t in page2["items"]] == ["c"]
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
    assert [f["id"] for f in page["results"]] == ["fn.two"]
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
    assert [f["id"] for f in page["results"]] == ["fn.in"]

    page2 = service.search_functions(keywords="fn", io_out="LogRef", limit=10, cursor=None)
    assert [f["id"] for f in page2["results"]] == ["fn.out"]
    conn.close()


def test_prune_stale_functions_removes_unlisted() -> None:
    """Test that prune_stale_functions removes functions not in the valid set."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.base",
        name="base",
        description="base",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/base.yaml",
        available=True,
        installed=True,
    )

    # Insert 3 functions
    for fn_name in ["keep1", "keep2", "stale"]:
        service.upsert_function(
            fn_id=f"base.{fn_name}",
            tool_id="tools.base",
            name=fn_name,
            description=f"{fn_name} function",
            tags=[],
            inputs=[],
            outputs=[],
            params_schema={},
        )

    # Verify all 3 are present
    initial = service.list_tools(flatten=True)
    assert len(initial["items"]) == 3

    # Prune, keeping only 2
    deleted = service.prune_stale_functions({"base.keep1", "base.keep2"})
    assert deleted == 1

    # Verify only 2 remain
    after = service.list_tools(flatten=True)
    fn_ids = [t["id"] for t in after["items"]]
    assert "base.keep1" in fn_ids
    assert "base.keep2" in fn_ids
    assert "base.stale" not in fn_ids
    conn.close()


def test_prune_stale_tools_removes_unlisted() -> None:
    """Test that prune_stale_tools removes tools not in the valid set."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)

    # Insert 3 tools
    for name in ["keep1", "keep2", "stale"]:
        tool_id = f"tools.{name}"
        service.upsert_tool(
            tool_id=tool_id,
            name=name,
            description=name,
            tool_version="0.0.0",
            env_id="bioimage-mcp-base",
            manifest_path=f"/abs/{name}.yaml",
            available=True,
            installed=True,
        )
        service.upsert_function(
            fn_id=f"{name}.fn",
            tool_id=tool_id,
            name=f"Fn {name}",
            description="",
            tags=[],
            inputs=[],
            outputs=[],
            params_schema={},
        )

    # Prune, keeping only 2 tools
    deleted = service.prune_stale_tools({"tools.keep1", "tools.keep2"})
    assert deleted == 1
    conn.close()


def test_prune_with_empty_set_removes_all() -> None:
    """Test that pruning with empty set removes all entries."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    service.upsert_tool(
        tool_id="tools.test",
        name="test",
        description="test",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/test.yaml",
        available=True,
        installed=True,
    )
    service.upsert_function(
        fn_id="test.fn",
        tool_id="tools.test",
        name="fn",
        description="",
        tags=[],
        inputs=[],
        outputs=[],
        params_schema={},
    )

    # Prune with empty set should remove all
    deleted_fn = service.prune_stale_functions(set())
    deleted_tool = service.prune_stale_tools(set())

    assert deleted_fn == 1
    assert deleted_tool == 1

    result = service.list_tools(flatten=True)
    assert len(result["items"]) == 0
    conn.close()
