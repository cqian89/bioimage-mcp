from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from bioimage_mcp.api.pagination import decode_cursor, encode_cursor, resolve_limit
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.index import RegistryIndex, ToolIndex
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.registry.manifest_schema import FunctionResponse
from bioimage_mcp.registry.schema_cache import SchemaCache
from bioimage_mcp.registry.search import SearchIndex, any_tag_matches, io_type_matches
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

    def list_tools(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        flatten: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        config = load_config()
        resolved_limit = resolve_limit(limit, config)
        flatten_flag = bool(flatten)

        normalized_paths: list[str] | None = []
        if path:
            normalized_paths.append(path)
        if paths:
            normalized_paths.extend(paths)
        if not normalized_paths:
            normalized_paths = None

        after: str | None = None
        if cursor:
            payload = decode_cursor(cursor)
            if payload.get("paths") != normalized_paths or payload.get("flatten") != flatten_flag:
                raise ValueError("Cursor does not match request")
            after = str(payload.get("last_full_path") or "")
            after = after or None

        functions = self._index.list_functions()
        tool_index = ToolIndex(functions)
        tool_index.build_hierarchy()

        expanded_from = None
        nodes: list[dict] = []
        if flatten_flag:
            if normalized_paths is None:
                nodes = tool_index.flatten_tools(None)
            else:
                for target in normalized_paths:
                    nodes.extend(tool_index.flatten_tools(target))
        else:
            if normalized_paths is None:
                nodes, expanded_from = tool_index.list_children(None, auto_expand=False)
            elif len(normalized_paths) == 1:
                nodes, expanded_from = tool_index.list_children(
                    normalized_paths[0], auto_expand=True
                )
            else:
                collected: list[dict] = []
                for target in normalized_paths:
                    child_nodes, _expanded = tool_index.list_children(target, auto_expand=True)
                    collected.extend(child_nodes)
                nodes = collected

        if nodes:
            deduped = {node["full_path"]: node for node in nodes}
            nodes = sorted(deduped.values(), key=lambda entry: entry["full_path"])

        if after:
            nodes = [node for node in nodes if node["full_path"] > after]

        page = nodes[:resolved_limit]
        next_cursor = None
        if page:
            next_cursor = encode_cursor(
                {
                    "last_full_path": page[-1]["full_path"],
                    "paths": normalized_paths,
                    "flatten": flatten_flag,
                }
            )

        return {"tools": page, "next_cursor": next_cursor, "expanded_from": expanded_from}

    def describe_tool(self, tool_id: str) -> dict[str, Any]:
        tool = self._index.get_tool(tool_id)
        if tool is None:
            raise KeyError(tool_id)
        functions = self._index.get_functions_for_tool(tool_id)
        return {"tool": tool, "functions": functions}

    def search_functions(
        self,
        *,
        keywords: list[str] | str | None = None,
        query: str | None = None,
        tags: list[str] | None = None,
        io_in: str | None = None,
        io_out: str | None = None,
        limit: int | None,
        cursor: str | None,
    ) -> dict[str, Any]:
        config = load_config()
        resolved_limit = resolve_limit(limit, config)

        raw_keywords = keywords if keywords is not None else query
        if raw_keywords is None:
            raise ValueError("keywords must not be empty")

        if isinstance(raw_keywords, str):
            keyword_list = [kw for kw in raw_keywords.split() if kw]
        else:
            keyword_list = [str(kw) for kw in raw_keywords]

        normalized_keywords: list[str] = []
        seen: set[str] = set()
        for keyword in keyword_list:
            cleaned = str(keyword).strip().lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized_keywords.append(cleaned)

        if not normalized_keywords:
            raise ValueError("keywords must not be empty")

        offset = 0
        if cursor:
            payload = decode_cursor(cursor)
            if (
                payload.get("keywords") != normalized_keywords
                or payload.get("tags") != tags
                or payload.get("io_in") != io_in
                or payload.get("io_out") != io_out
            ):
                raise ValueError("Cursor does not match request")
            offset = int(payload.get("offset") or 0)

        collected: list[dict] = []
        scan_after: str | None = None
        batch_size = 200
        while True:
            batch = self._index.iter_search_functions(
                query="", after_fn_id=scan_after, batch_size=batch_size
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
                        "name": row["name"],
                        "description": row["description"],
                        "tags": row["tags"],
                    }
                )

            scan_after = batch[-1]["fn_id"]

        index = SearchIndex()
        ranked = index.rank(keywords=normalized_keywords, candidates=collected)

        page = ranked[offset : offset + resolved_limit]
        next_cursor = None
        if offset + len(page) < len(ranked):
            next_cursor = encode_cursor(
                {
                    "offset": offset + len(page),
                    "keywords": normalized_keywords,
                    "tags": tags,
                    "io_in": io_in,
                    "io_out": io_out,
                }
            )

        functions = [
            {
                "fn_id": entry["fn_id"],
                "name": entry.get("name", ""),
                "description": entry.get("description", ""),
                "tags": entry.get("tags", []),
                "score": float(entry["score"]),
                "match_count": int(entry["match_count"]),
            }
            for entry in page
        ]

        return {"functions": functions, "next_cursor": next_cursor}

    def describe_function(
        self,
        fn_id: str | None = None,
        fn_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if fn_ids is not None:
            schemas: dict[str, Any] = {}
            errors: dict[str, str] = {}
            for target_id in fn_ids:
                try:
                    schemas[target_id] = self.describe_function(fn_id=target_id)
                except KeyError:
                    errors[target_id] = f"Function not found: {target_id}"
            return {"schemas": schemas, "errors": errors}

        if fn_id is None:
            raise ValueError("fn_id is required when fn_ids is not provided")

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
