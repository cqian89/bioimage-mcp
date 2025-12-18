from __future__ import annotations

import sqlite3
from typing import Any

from bioimage_mcp.api.pagination import decode_cursor, encode_cursor, resolve_limit
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.index import RegistryIndex
from bioimage_mcp.registry.search import any_tag_matches, io_type_matches


class DiscoveryService:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._index = RegistryIndex(conn)

    # Convenience methods used by tests and loader.
    def upsert_tool(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._index.upsert_tool(**kwargs)

    def upsert_function(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._index.upsert_function(**kwargs)

    def clear_diagnostics(self) -> None:
        self._index.clear_diagnostics()

    def record_diagnostic(self, diagnostic) -> None:  # type: ignore[no-untyped-def]
        self._index.record_diagnostic(diagnostic)

    def list_tools(self, *, limit: int | None, cursor: str | None) -> dict[str, Any]:
        config = load_config()
        resolved_limit = resolve_limit(limit, config)

        after: str | None = None
        if cursor:
            after = str(decode_cursor(cursor).get("last_tool_id") or "")
            after = after or None

        tools = self._index.list_tools(after_tool_id=after, limit=resolved_limit)
        next_cursor = None
        if tools:
            next_cursor = encode_cursor({"last_tool_id": tools[-1]["tool_id"]})

        return {"tools": tools, "next_cursor": next_cursor}

    def describe_tool(self, tool_id: str) -> dict[str, Any]:
        tool = self._index.get_tool(tool_id)
        if tool is None:
            raise KeyError(tool_id)
        functions = self._index.get_functions_for_tool(tool_id)
        return {"tool": tool, "functions": functions}

    def search_functions(
        self,
        *,
        query: str,
        tags: list[str] | None = None,
        io_in: str | None = None,
        io_out: str | None = None,
        limit: int | None,
        cursor: str | None,
    ) -> dict[str, Any]:
        config = load_config()
        resolved_limit = resolve_limit(limit, config)

        after: str | None = None
        if cursor:
            after = str(decode_cursor(cursor).get("last_fn_id") or "")
            after = after or None

        collected: list[dict] = []
        scan_after = after
        batch_size = max(resolved_limit, 50)
        while len(collected) < resolved_limit:
            batch = self._index.iter_search_functions(
                query=query, after_fn_id=scan_after, batch_size=batch_size
            )
            if not batch:
                break

            for row in batch:
                if not any_tag_matches(row["tags"], tags):
                    continue
                if not io_type_matches(row["inputs"], io_in):
                    continue
                if not io_type_matches(row["outputs"], io_out):
                    continue
                collected.append(
                    {
                        "fn_id": row["fn_id"],
                        "tool_id": row["tool_id"],
                        "name": row["name"],
                        "description": row["description"],
                        "tags": row["tags"],
                    }
                )
                if len(collected) >= resolved_limit:
                    break

            scan_after = batch[-1]["fn_id"]

        next_cursor = None
        if collected:
            next_cursor = encode_cursor({"last_fn_id": collected[-1]["fn_id"]})

        return {"functions": collected, "next_cursor": next_cursor}

    def describe_function(self, fn_id: str) -> dict[str, Any]:
        payload = self._index.get_function(fn_id)
        if payload is None:
            raise KeyError(fn_id)
        return payload
