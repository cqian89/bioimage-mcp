import sqlite3

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.storage.sqlite import init_schema


def _seed_hierarchy(service: DiscoveryService) -> None:
    service.upsert_tool(
        tool_id="tools.base",
        name="Base",
        description="Base tool pack",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path="/abs/base.yaml",
        available=True,
        installed=True,
    )
    service.upsert_tool(
        tool_id="tools.cellpose",
        name="Cellpose",
        description="Cellpose tool pack",
        tool_version="0.0.0",
        env_id="bioimage-mcp-cellpose",
        manifest_path="/abs/cellpose.yaml",
        available=True,
        installed=True,
    )

    service.upsert_function(
        id="base.skimage.filters.gaussian",
        tool_id="tools.base",
        name="Gaussian",
        description="Gaussian blur",
        tags=["filter"],
        inputs=[],
        outputs=[],
        params_schema={},
    )
    service.upsert_function(
        id="base.skimage.filters.sobel",
        tool_id="tools.base",
        name="Sobel",
        description="Sobel filter",
        tags=["filter"],
        inputs=[],
        outputs=[],
        params_schema={},
    )
    service.upsert_function(
        id="base.phasorpy.phasor.phasor_calibrate",
        tool_id="tools.base",
        name="Phasor Calibrate",
        description="Calibrate phasors",
        tags=["phasor"],
        inputs=[],
        outputs=[],
        params_schema={},
    )
    service.upsert_function(
        id="cellpose.core.segment",
        tool_id="tools.cellpose",
        name="Segment",
        description="Cell segmentation",
        tags=["cellpose"],
        inputs=[],
        outputs=[],
        params_schema={},
    )


def test_list_tools_returns_environment_nodes() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    _seed_hierarchy(service)

    page = service.list_tools(limit=20, cursor=None)

    assert {"items", "next_cursor", "expanded_from"}.issubset(page.keys())
    names = {node["name"] for node in page["items"]}
    assert {"base", "cellpose"}.issubset(names)
    assert all(node["type"] == "environment" for node in page["items"])
    conn.close()


def test_list_tools_path_returns_packages() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    _seed_hierarchy(service)

    page = service.list_tools(path="base", limit=20, cursor=None)

    names = {node["name"] for node in page["items"]}
    assert {"skimage", "phasorpy"}.issubset(names)
    assert all(node["type"] == "package" for node in page["items"])
    conn.close()


def test_list_tools_module_path_returns_functions() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    _seed_hierarchy(service)

    page = service.list_tools(path="base.skimage.filters", limit=20, cursor=None)

    fn_ids = {node["id"] for node in page["items"]}
    assert "base.skimage.filters.gaussian" in fn_ids
    assert "base.skimage.filters.sobel" in fn_ids
    assert all(node["type"] == "function" for node in page["items"])
    assert page["expanded_from"] is None
    conn.close()


def test_list_tools_auto_expands_single_child_paths() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    _seed_hierarchy(service)

    page = service.list_tools(path="cellpose", limit=20, cursor=None)

    assert page["expanded_from"] == "cellpose"
    assert len(page["items"]) == 1
    assert page["items"][0]["id"] == "cellpose.core.segment"
    assert page["items"][0]["type"] == "function"
    conn.close()


def test_list_tools_flatten_returns_functions() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    _seed_hierarchy(service)

    page = service.list_tools(path="base", flatten=True, limit=20, cursor=None)

    fn_ids = {node["id"] for node in page["items"]}
    assert "base.skimage.filters.gaussian" in fn_ids
    assert "base.skimage.filters.sobel" in fn_ids
    assert "base.phasorpy.phasor.phasor_calibrate" in fn_ids
    assert all(node["type"] == "function" for node in page["items"])
    assert page["expanded_from"] is None
    conn.close()


def test_list_tools_flatten_paginates() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    service = DiscoveryService(conn)
    _seed_hierarchy(service)

    first = service.list_tools(path="base", flatten=True, limit=1, cursor=None)
    assert len(first["items"]) == 1
    assert first["next_cursor"] is not None

    first_path = first["items"][0]["id"]
    second = service.list_tools(path="base", flatten=True, limit=1, cursor=first["next_cursor"])

    assert len(second["items"]) == 1
    assert second["items"][0]["id"] > first_path
    conn.close()
