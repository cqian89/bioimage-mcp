from __future__ import annotations

from typing import Any

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService


def create_server(
    discovery: DiscoveryService, *, execution: ExecutionService, artifacts: ArtifactsService
):
    """Create an MCP server instance.

    The concrete MCP SDK API is imported lazily to keep unit tests light.
    """

    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("MCP SDK not available; install `mcp` to use serve") from exc

    mcp = FastMCP("bioimage-mcp")

    @mcp.tool()
    def list_tools(cursor: str | None = None, limit: int | None = None) -> dict[str, Any]:
        return discovery.list_tools(limit=limit, cursor=cursor)

    @mcp.tool()
    def describe_tool(tool_id: str) -> dict[str, Any]:
        return discovery.describe_tool(tool_id)

    @mcp.tool()
    def search_functions(
        query: str,
        tags: list[str] | None = None,
        io_in: str | None = None,
        io_out: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        return discovery.search_functions(
            query=query,
            tags=tags,
            io_in=io_in,
            io_out=io_out,
            cursor=cursor,
            limit=limit,
        )

    @mcp.tool()
    def describe_function(fn_id: str) -> dict[str, Any]:
        return discovery.describe_function(fn_id)

    @mcp.tool()
    def run_workflow(steps: list[dict], run_opts: dict | None = None) -> dict[str, Any]:
        spec = {"steps": steps, "run_opts": run_opts or {}}
        return execution.run_workflow(spec)

    @mcp.tool()
    def get_run_status(run_id: str) -> dict[str, Any]:
        return execution.get_run_status(run_id)

    @mcp.tool()
    def get_artifact(ref_id: str) -> dict[str, Any]:
        return artifacts.get_artifact(ref_id)

    @mcp.tool()
    def export_artifact(ref_id: str, dest_path: str) -> dict[str, Any]:
        return artifacts.export_artifact(ref_id, dest_path)

    return mcp
