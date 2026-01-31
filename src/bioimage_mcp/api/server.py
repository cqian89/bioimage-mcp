from __future__ import annotations

from typing import Any

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.api.serializers import RunResponseSerializer, DescribeResponseSerializer
from bioimage_mcp.sessions.manager import SessionManager

try:
    from mcp.server.fastmcp import Context, FastMCP  # type: ignore
except ImportError as exc:  # noqa: BLE001
    print(f"DEBUG: Failed to import mcp: {exc}")

    # Allow importing this module without mcp installed (e.g. for lightweight tests),
    # but create_server will fail if called.
    class Context:  # type: ignore
        session: Any

    class FastMCP:  # type: ignore
        def __init__(self, name: str, **kwargs):
            pass

        def tool(self):
            def decorator(f):
                return f

            return decorator


def get_session_identifier(ctx) -> str:
    """Get stable session identifier from MCP context.

    The MCP Python SDK v1.25.0+ does not provide a `.id` attribute on ServerSession.
    This helper provides a stable identifier using:
    1. If ctx.session has an .id attribute (backward compat for tests), use it
    2. SSE query param 'session_id' if available
    3. Fallback to f"session_{id(ctx.session)}" for stdio transport

    Args:
        ctx: MCP Context object with session information

    Returns:
        A stable session identifier string
    """
    # Backward compatibility: if session has .id attribute, use it directly
    if hasattr(ctx.session, "id"):
        return ctx.session.id

    # Try SSE transport session_id from query params first
    if hasattr(ctx, "request_context") and ctx.request_context:
        if hasattr(ctx.request_context, "query_params"):
            query_params = ctx.request_context.query_params
            if query_params and query_params.get("session_id"):
                return query_params["session_id"]

    # Fallback to memory-based identifier for stdio transport
    return f"session_{id(ctx.session)}"


def create_server(
    discovery: DiscoveryService,
    *,
    execution: ExecutionService,
    interactive: InteractiveExecutionService,
    artifacts: ArtifactsService,
    session_manager: SessionManager,
):
    """Create an MCP server instance.

    The concrete MCP SDK API is imported lazily to keep unit tests light.
    """
    # Check if we have the real FastMCP
    # If FastMCP was defined in this module (the dummy class), it will have this module's name.
    if FastMCP.__module__ == __name__:
        raise RuntimeError("MCP SDK not available; install `mcp` to use serve")

    mcp = FastMCP("bioimage-mcp")

    @mcp.tool()
    def list(
        path: str | None = None,
        paths: list[str] | None = None,
        flatten: bool | None = None,
        cursor: str | None = None,
        limit: int | None = None,
        types: list[str] | None = None,
        include_counts: bool = True,
        session_id: str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """List catalog nodes (environments, packages, modules, functions)."""
        if not session_id and ctx and ctx.session:
            session_id = get_session_identifier(ctx)

        active_fn_ids: list[str] = []
        if session_id:
            session_manager.ensure_session(session_id)
            active_fn_ids = session_manager.store.get_active_functions(session_id)
        return discovery.list_tools(
            path=path,
            paths=paths,
            flatten=flatten,
            limit=limit,
            cursor=cursor,
            types=types,
            include_counts=include_counts,
            active_fn_ids=active_fn_ids,
        )

    @mcp.tool()
    def describe(
        id: str | None = None,
        ids: list[str] | None = None,
        verbosity: str = "minimal",
    ) -> dict[str, Any]:
        """Get full details for a function or catalog node.

        Args:
            verbosity: Response detail level ('minimal', 'standard', or 'full').
                       Defaults to 'minimal' for token-efficient LLM interaction.
        """
        result = discovery.describe_function(id=id, ids=ids)
        serializer = DescribeResponseSerializer()
        return serializer.serialize(result, verbosity=verbosity)

    @mcp.tool()
    def search(
        query: str | None = None,
        keywords: list[str] | None = None,
        tags: list[str] | None = None,
        io_in: str | None = None,
        io_out: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        session_id: str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Search for functions by natural language query, keywords, or I/O types."""
        if not session_id and ctx and ctx.session:
            session_id = get_session_identifier(ctx)

        active_fn_ids: list[str] = []
        if session_id:
            session_manager.ensure_session(session_id)
            active_fn_ids = session_manager.store.get_active_functions(session_id)
        return discovery.search_functions(
            query=query,
            keywords=keywords,
            tags=tags,
            io_in=io_in,
            io_out=io_out,
            limit=limit,
            cursor=cursor,
            active_fn_ids=active_fn_ids,
        )

    @mcp.tool()
    def status(run_id: str) -> dict[str, Any]:
        """Poll the status of a background run."""
        return execution.get_run_status(run_id)

    @mcp.tool()
    def run(
        id: str,
        inputs: dict[str, Any],
        params: dict[str, Any] | None = None,
        session_id: str | None = None,
        ordinal: int | None = None,
        dry_run: bool = False,
        verbosity: str = "minimal",
        timeout_seconds: int | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Execute a function within a session.

        If session_id is not provided, uses the current MCP connection's session ID.

        Args:
            verbosity: Response detail level ('minimal', 'standard', or 'full').
                       Defaults to 'minimal' for token-efficient LLM interaction.
        """
        if not session_id and ctx and ctx.session:
            session_id = get_session_identifier(ctx)

        if not session_id:
            raise ValueError("session_id must be provided or available in context")

        if params is None:
            params = {}

        session_manager.ensure_session(session_id)

        result = interactive.call_tool(
            session_id=session_id,
            fn_id=id,
            inputs=inputs,
            params=params,
            ordinal=ordinal,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
        )

        # Build base result dict (includes all data from interactive service)
        base_result = {
            "run_id": result.get("run_id", "none"),
            "status": result.get("status"),
            "outputs": result.get("outputs", {}),
            "warnings": result.get("warnings", []),
            "log_ref": result.get("log_ref"),
            "workflow_record": result.get("workflow_record"),
        }
        if "dry_run" in result:
            base_result["dry_run"] = result["dry_run"]
        if result.get("error"):
            base_result["error"] = result["error"]

        # Apply verbosity-aware serialization
        serializer = RunResponseSerializer()
        response = serializer.serialize(base_result, id=id, verbosity=verbosity)

        return response

    @mcp.tool()
    def artifact_info(
        ref_id: str,
        text_preview_bytes: int | None = None,
        include_image_preview: bool = False,
        image_preview_size: int = 256,
        channels: int | list[int] | None = None,
        projection: str | dict = "max",
        slice_indices: dict | None = None,
    ) -> dict[str, Any]:
        """Get full metadata and optional text preview for an artifact."""
        return artifacts.artifact_info(
            ref_id,
            text_preview_bytes=text_preview_bytes,
            include_image_preview=include_image_preview,
            image_preview_size=image_preview_size,
            channels=channels,
            projection=projection,
            slice_indices=slice_indices,
        )

    @mcp.tool()
    def session_export(
        session_id: str | None = None,
        dest_path: str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Export session to a reproducible workflow artifact.

        If session_id is not provided, uses the current MCP connection's session ID.
        """
        if not session_id and ctx and ctx.session:
            session_id = get_session_identifier(ctx)

        if not session_id:
            raise ValueError("session_id must be provided or available in context")

        return interactive.export_session(session_id, dest_path=dest_path)

    @mcp.tool()
    def session_replay(
        workflow_ref: dict[str, Any],
        inputs: dict[str, str],
        params_overrides: dict[str, dict[str, Any]] | None = None,
        step_overrides: dict[str, dict[str, Any]] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Replay a workflow from an exported record."""
        return interactive.replay_session(
            workflow_ref=workflow_ref,
            inputs=inputs,
            params_overrides=params_overrides,
            step_overrides=step_overrides,
            dry_run=dry_run,
        )

    return mcp
