from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from bioimage_mcp.api.pagination import decode_cursor, encode_cursor, resolve_limit
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.index import RegistryIndex
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.registry.manifest_schema import FunctionResponse
from bioimage_mcp.registry.schema_cache import SchemaCache
from bioimage_mcp.registry.search import any_tag_matches, io_type_matches
from bioimage_mcp.runtimes.executor import execute_tool


class DiscoveryService:
    def __init__(self, conn: sqlite3.Connection, *, owns_conn: bool = False):
        self._conn = conn
        self._owns_conn = owns_conn
        self._index = RegistryIndex(conn)

    def close(self) -> None:
        if self._owns_conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

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

        config = load_config()
        manifests, _diagnostics = load_manifests(config.tool_manifest_roots)
        manifest = next(
            (m for m in manifests if any(fn.fn_id == fn_id for fn in m.functions)),
            None,
        )
        if manifest is None:
            return payload

        function_def = next((fn for fn in manifest.functions if fn.fn_id == fn_id), None)
        if function_def is None:
            return payload

        inputs: dict[str, Any] = {}
        for port in function_def.inputs:
            description = port.description or f"{port.name} input"
            inputs[port.name] = {
                "type": port.artifact_type,
                "required": port.required,
                "description": description,
            }

        outputs: dict[str, Any] = {}
        for port in function_def.outputs:
            description = port.description or f"{port.name} output"
            outputs[port.name] = {
                "type": port.artifact_type,
                "description": description,
            }

        hints = function_def.hints.model_dump(exclude_none=True) if function_def.hints else None

        schema_cache_path = config.schema_cache_path or (
            config.artifact_store_root / "state" / "schema_cache.json"
        )
        cache = SchemaCache(schema_cache_path)
        cached = cache.get(
            tool_id=manifest.tool_id,
            tool_version=manifest.tool_version,
            fn_id=fn_id,
        )
        if cached:
            enriched = {
                "fn_id": fn_id,
                "schema": cached["params_schema"],
                "introspection_source": cached.get("introspection_source"),
                "inputs": inputs,
                "outputs": outputs,
                "hints": hints,
            }
            return FunctionResponse.model_validate(enriched).model_dump(
                exclude_none=True,
                by_alias=True,
            )

        entrypoint = manifest.entrypoint
        entry_path = Path(entrypoint)
        if not entry_path.is_absolute():
            candidate = manifest.manifest_path.parent / entry_path
            if candidate.exists():
                entrypoint = str(candidate)

        request = {
            "fn_id": "meta.describe",
            "params": {"target_fn": fn_id},
            "inputs": {},
            "work_dir": str(config.artifact_store_root / "work" / "describe"),
        }
        response, _log_text, _exit_code = execute_tool(
            entrypoint=entrypoint,
            request=request,
            env_id=manifest.env_id,
        )
        if not response.get("ok"):
            fallback = {
                **payload,
                "inputs": inputs,
                "outputs": outputs,
                "hints": hints,
            }
            return FunctionResponse.model_validate(fallback).model_dump(
                exclude_none=True,
                by_alias=True,
            )

        result = response.get("result") or {}
        params_schema = result.get("params_schema")
        if not isinstance(params_schema, dict):
            fallback = {
                **payload,
                "inputs": inputs,
                "outputs": outputs,
                "hints": hints,
            }
            return FunctionResponse.model_validate(fallback).model_dump(
                exclude_none=True,
                by_alias=True,
            )

        introspection_source = str(result.get("introspection_source") or "manual")
        cache.set(
            tool_id=manifest.tool_id,
            tool_version=manifest.tool_version,
            fn_id=fn_id,
            params_schema=params_schema,
            introspection_source=introspection_source,
        )
        enriched = {
            "fn_id": fn_id,
            "schema": params_schema,
            "introspection_source": introspection_source,
            "inputs": inputs,
            "outputs": outputs,
            "hints": hints,
        }
        return FunctionResponse.model_validate(enriched).model_dump(
            exclude_none=True,
            by_alias=True,
        )
