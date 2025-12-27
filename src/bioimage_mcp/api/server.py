from __future__ import annotations

from typing import Any

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
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

    def get_session(ctx: Context) -> Any:
        """Helper to get the current session from the request context."""
        if not ctx.session:
            raise RuntimeError("No session context available")
        return session_manager.ensure_session(get_session_identifier(ctx))

    # --- Implementation helpers for testing ---
    def _filter_tools_impl(tools_result: dict, active_ids: list[str]) -> dict:
        # Filter tools: only include tools that contain at least one active function.
        allowed_tool_ids = set()
        for fn_id in active_ids:
            try:
                # We try describe_function first, but if it lacks tool_id (as observed),
                # we fall back to search_functions.
                desc = discovery.describe_function(fn_id)
                if desc and "tool_id" in desc:
                    allowed_tool_ids.add(desc["tool_id"])
                else:
                    # Fallback: search for the function to get its tool_id
                    search_res = discovery.search_functions(query=fn_id, limit=5, cursor=None)
                    if search_res and search_res.get("functions"):
                        for f in search_res["functions"]:
                            if f["fn_id"] == fn_id:
                                allowed_tool_ids.add(f["tool_id"])
                                break
            except Exception:
                pass

        tools_result["tools"] = [
            t for t in tools_result["tools"] if t["tool_id"] in allowed_tool_ids
        ]
        return tools_result

    def _filter_functions_impl(functions_result: dict, active_ids: list[str]) -> dict:
        allowed_fn_ids = set(active_ids)
        functions_result["functions"] = [
            f for f in functions_result["functions"] if f["fn_id"] in allowed_fn_ids
        ]
        return functions_result

    async def _activate_functions_impl(ctx: Context, fn_ids: list[str]) -> dict[str, Any]:
        if not ctx or not ctx.session:
            raise RuntimeError("Session context required for activation")

        session_id = get_session_identifier(ctx)
        session_manager.ensure_session(session_id)
        session_manager.store.replace_active_functions(session_id, fn_ids)

        await ctx.session.send_tool_list_changed()
        return {"session_id": session_id, "active": fn_ids}

    async def _deactivate_functions_impl(ctx: Context) -> dict[str, Any]:
        if not ctx or not ctx.session:
            raise RuntimeError("Session context required for deactivation")

        session_id = get_session_identifier(ctx)
        session_manager.ensure_session(session_id)
        session_manager.store.replace_active_functions(session_id, [])

        await ctx.session.send_tool_list_changed()
        return {"session_id": session_id, "active": []}

    @mcp.tool()
    def list_tools(
        cursor: str | None = None,
        limit: int | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        tools_result = discovery.list_tools(limit=limit, cursor=cursor)

        if ctx and ctx.session:
            session_id = get_session_identifier(ctx)
            session_manager.ensure_session(session_id)
            active_ids = session_manager.store.get_active_functions(session_id)
            if active_ids:
                return _filter_tools_impl(tools_result, active_ids)

        return tools_result

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
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        result = discovery.search_functions(
            query=query,
            tags=tags,
            io_in=io_in,
            io_out=io_out,
            cursor=cursor,
            limit=limit,
        )

        if ctx and ctx.session:
            session_id = get_session_identifier(ctx)
            session_manager.ensure_session(session_id)
            active_ids = session_manager.store.get_active_functions(session_id)
            if active_ids:
                return _filter_functions_impl(result, active_ids)

        return result

    @mcp.tool()
    async def activate_functions(fn_ids: list[str], ctx: Context | None = None) -> dict[str, Any]:
        """Activate a specific set of functions for the current session."""
        if ctx is None:
            raise RuntimeError("Context missing")
        return await _activate_functions_impl(ctx, fn_ids)

    @mcp.tool()
    async def deactivate_functions(ctx: Context | None = None) -> dict[str, Any]:
        """Deactivate all function filters (restore full access) for the current session."""
        if ctx is None:
            raise RuntimeError("Context missing")
        return await _deactivate_functions_impl(ctx)

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
    def call_tool(
        fn_id: str,
        inputs: dict[str, Any],
        params: dict[str, Any],
        session_id: str | None = None,
        ordinal: int | None = None,
        dry_run: bool = False,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Execute a tool call within a session.

        If session_id is not provided, uses the current MCP connection's session ID.
        """
        if not session_id and ctx and ctx.session:
            session_id = get_session_identifier(ctx)

        if not session_id:
            # We could create a new session here, or raise an error.
            # The interactive service expects a session_id.
            # If called via stdio without explicit session_id and no client session context,
            # we should probably fail or let ensure_session handle it (but ensure_session needs ID).
            # For now, let's assume we need a session ID.
            raise ValueError("session_id must be provided or available in context")

        return interactive.call_tool(
            session_id=session_id,
            fn_id=fn_id,
            inputs=inputs,
            params=params,
            ordinal=ordinal,
            dry_run=dry_run,
        )

    @mcp.tool()
    def get_artifact(ref_id: str) -> dict[str, Any]:
        return artifacts.get_artifact(ref_id)

    @mcp.tool()
    def export_artifact(ref_id: str, dest_path: str) -> dict[str, Any]:
        return artifacts.export_artifact(ref_id, dest_path)

    @mcp.tool()
    def export_session(session_id: str | None = None, ctx: Context | None = None) -> dict[str, Any]:
        """Export session to a reproducible workflow artifact.

        If session_id is not provided, uses the current MCP connection's session ID.
        """
        if not session_id and ctx and ctx.session:
            session_id = get_session_identifier(ctx)

        if not session_id:
            raise ValueError("session_id must be provided or available in context")

        return interactive.export_session(session_id)

    @mcp.tool()
    def resume_session(session_id: str) -> dict[str, Any]:
        """Resume an existing session.

        Returns the session details, including the session_id and active functions.
        """
        try:
            session = session_manager.get_session(session_id)
        except KeyError:
            raise ValueError(f"Session {session_id} not found")

        active_fns = session_manager.store.get_active_functions(session_id)

        return {
            "session_id": session.session_id,
            "status": session.status,
            "created_at": session.created_at,
            "last_activity_at": session.last_activity_at,
            "active_functions": active_fns,
        }

    return mcp
