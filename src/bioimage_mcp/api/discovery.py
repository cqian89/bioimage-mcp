from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from bioimage_mcp.api.errors import not_found_error, validation_error
from bioimage_mcp.api.pagination import decode_cursor, encode_cursor, resolve_limit
from bioimage_mcp.artifacts.models import ARTIFACT_TYPES
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.index import RegistryIndex, ToolIndex
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.registry.manifest_schema import ToolManifest
from bioimage_mcp.registry.search import SearchIndex, any_tag_matches, io_type_matches
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.runtimes.meta_protocol import parse_meta_describe_result


def _find_project_root(start: Path) -> Path | None:
    curr = start
    for _ in range(5):
        if (curr / "envs").exists() or (curr / "pyproject.toml").exists():
            return curr
        curr = curr.parent
    return None


def _compute_env_lock_hash(project_root: Path | None, env_id: str) -> str | None:
    if project_root is None:
        return None
    lock_file = project_root / "envs" / f"{env_id}.lock.yml"
    if not lock_file.exists():
        return None
    try:
        import hashlib

        return hashlib.sha256(lock_file.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def _compute_source_hash(
    manifest: ToolManifest,
    *,
    module: str | None,
    callable_name: str | None,
    project_root: Path | None,
) -> str | None:
    if module is None or callable_name is None:
        return None

    from bioimage_mcp.registry.static.fingerprint import callable_fingerprint
    from bioimage_mcp.registry.static.inspector import inspect_module

    search_paths = [manifest.manifest_path.parent]
    if project_root and (project_root / "tools").exists():
        search_paths.append(project_root / "tools")

    try:
        report = inspect_module(module, search_paths)
        for c in report.callables:
            if c.name == callable_name:
                if c.source:
                    return callable_fingerprint(c.source)
                return None
    except Exception:
        return None
    return None


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

    def prune_stale_functions(self, valid_fn_ids: set[str]) -> int:
        """Delete functions not in the valid set."""
        return self._index.prune_stale_functions(valid_fn_ids)

    def prune_stale_tools(self, valid_tool_ids: set[str]) -> int:
        """Delete tools not in the valid set."""
        return self._index.prune_stale_tools(valid_tool_ids)

    def list_tools(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        flatten: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        types: list[str] | None = None,
        include_counts: bool = True,
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
            # Relax cursor validation slightly to handle optional parameters
            # if payload.get("paths") != normalized_paths or payload.get("flatten") != flatten_flag:
            #    raise ValueError("Cursor does not match request")
            after = str(payload.get("last_full_path") or "")
            after = after or None

        functions = self._index.list_functions()
        tool_index = ToolIndex(functions)
        tool_index.build_hierarchy()

        # Contract T035: Return error if path is invalid
        if normalized_paths:
            for p in normalized_paths:
                if tool_index._resolve_path(p) is None:
                    # Return a structured error response that our server.py or caller can handle
                    return {
                        "items": [],
                        "error": not_found_error(
                            message=f"Path not found: {p}",
                            path="/path",
                            expected="valid catalog node path",
                            hint="Use 'list' without a path to see available roots",
                        ).model_dump(),
                    }

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

        # Filter by types if requested
        if types:
            nodes = [node for node in nodes if node["type"] in types]

        if after:
            nodes = [node for node in nodes if node["full_path"] > after]

        page = nodes[:resolved_limit]
        next_cursor = None
        if len(nodes) > resolved_limit:
            next_cursor = encode_cursor(
                {
                    "last_full_path": page[-1]["full_path"],
                    "paths": normalized_paths,
                    "flatten": flatten_flag,
                }
            )

        # Remove full_path from final items as it's internal for pagination logic here
        # and we want to match CatalogNode schema
        items = []
        for n in page:
            item = {k: v for k, v in n.items() if k != "full_path" and k != "has_children"}
            if not include_counts and "children" in item:
                del item["children"]
            # Backward compatibility (T032)
            item["full_path"] = n["full_path"]
            item["has_children"] = n["has_children"]
            items.append(item)

        return {
            "items": items,
            "next_cursor": next_cursor,
            "expanded_from": expanded_from,
        }

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
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        # Validate: query and keywords are mutually exclusive
        if query is not None and keywords is not None:
            return {
                "results": [],
                "error": validation_error(
                    message="query and keywords are mutually exclusive",
                    path="query",
                    hint="Provide either 'query' (string) or 'keywords' (list), but not both.",
                ).model_dump(),
            }

        # Validate: at least one search criterion must be provided
        has_text_search = query is not None or keywords is not None
        has_filter = io_in is not None or io_out is not None or tags is not None

        if not has_text_search and not has_filter:
            return {
                "results": [],
                "error": validation_error(
                    message=(
                        "At least one search criterion required "
                        "(query, keywords, io_in, io_out, or tags)"
                    ),
                    path="query",
                    hint=(
                        "Provide 'query' (string), 'keywords' (list), "
                        "or filter by 'io_in', 'io_out', or 'tags'."
                    ),
                ).model_dump(),
            }

        config = load_config()
        resolved_limit = resolve_limit(limit, config)

        raw_keywords = keywords if keywords is not None else query

        if raw_keywords is None:
            keyword_list = []
        elif isinstance(raw_keywords, str):
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

        if has_text_search and not normalized_keywords:
            return {
                "results": [],
                "error": validation_error(
                    message="Keywords must not be empty",
                    path="query" if query is not None else "keywords",
                ).model_dump(),
            }

        offset = 0
        if cursor:
            payload = decode_cursor(cursor)
            if (
                payload.get("keywords") != normalized_keywords
                or payload.get("tags") != tags
                or payload.get("io_in") != io_in
                or payload.get("io_out") != io_out
            ):
                return {
                    "results": [],
                    "error": validation_error(
                        message="Cursor does not match request",
                        path="cursor",
                        hint=(
                            "The cursor was generated for a different search request. "
                            "Do not modify search parameters when paginating."
                        ),
                    ).model_dump(),
                }
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
                # T063: Add tags filtering
                if not any_tag_matches(row["tags"], tags):
                    continue
                # T062: Add io_in/io_out filtering
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
                        "inputs": row["inputs"],
                        "outputs": row["outputs"],
                    }
                )

            scan_after = batch[-1]["fn_id"]

        # T065: Add scoring and ranking
        if normalized_keywords:
            index = SearchIndex()
            ranked = index.rank(keywords=normalized_keywords, candidates=collected)
        else:
            # If no keywords (filter-only search), return all collected candidates with 0 score
            ranked = [
                {
                    **candidate,
                    "score": 0.0,
                    "match_count": 0,
                }
                for candidate in collected
            ]
            # Maintain deterministic ordering for filter-only results
            ranked.sort(key=lambda item: item["fn_id"])

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

        results = [
            {
                "id": entry["fn_id"],
                "type": "function",
                "name": entry.get("name", ""),
                "summary": entry.get("description", ""),
                "tags": entry.get("tags", []),
                # T064: Add I/O summaries to results
                "io": {
                    "inputs": [
                        {
                            "name": i.get("name"),
                            "type": i.get("artifact_type"),
                            "required": i.get("required", True),
                        }
                        for i in entry.get("inputs", [])
                    ],
                    "outputs": [
                        {
                            "name": o.get("name"),
                            "type": o.get("artifact_type"),
                        }
                        for o in entry.get("outputs", [])
                    ],
                },
                "score": float(entry["score"]),
                "match_count": int(entry["match_count"]),
            }
            for entry in page
        ]

        return {
            "results": results,
            "next_cursor": next_cursor,
        }

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
                    result = self.describe_function(fn_id=target_id)
                    if "error" in result:
                        errors[target_id] = result["error"]["message"]
                    else:
                        schemas[target_id] = result
                except KeyError:
                    errors[target_id] = f"Function not found: {target_id}"
            return {"schemas": schemas, "errors": errors}

        if fn_id is None:
            raise ValueError("fn_id is required when fn_ids is not provided")

        # Handle non-function nodes (T037, T046)
        functions = self._index.list_functions()
        tool_index = ToolIndex(functions)
        tool_index.build_hierarchy()
        node = tool_index._resolve_path(fn_id)

        if node is None:
            # Contract T038: Return NOT_FOUND error for invalid IDs
            return {
                "error": not_found_error(
                    message=f"ID not found: {fn_id}",
                    path="/id",
                    expected="valid function or node ID",
                    hint="Use 'search' or 'list' to find valid IDs",
                ).model_dump()
            }

        if node.type != "function":
            return tool_index._to_payload(node)

        # For function nodes
        payload = self._index.get_function(fn_id)
        if payload is None:
            # Should not happen if node was found, but for safety:
            return {
                "error": not_found_error(
                    message=f"Function metadata not found: {fn_id}",
                    path="/id",
                    expected="function with valid metadata in registry",
                    hint="Ensure the tool pack is correctly installed and indexed",
                ).model_dump()
            }

        config = load_config()
        manifests, _diagnostics = load_manifests(config.tool_manifest_roots)
        manifest = next(
            (m for m in manifests if any(fn.fn_id == fn_id for fn in m.functions)),
            None,
        )
        # If no manifest found, use what we have in DB
        function_def = None
        if manifest:
            function_def = next((fn for fn in manifest.functions if fn.fn_id == fn_id), None)

        inputs: dict[str, Any] = {}
        input_names = set()
        if function_def:
            for port in function_def.inputs:
                input_names.add(port.name)
                description = port.description or f"{port.name} input"
                inputs[port.name] = {
                    "type": port.artifact_type,
                    "required": port.required,
                    "description": description,
                    "hints": port.hints.model_dump(exclude_none=True)
                    if hasattr(port, "hints") and port.hints
                    else None,
                }
        else:
            # Fallback to DB inputs if manifest not available
            raw_inputs = self._index._conn.execute(
                "SELECT inputs_json FROM functions WHERE fn_id = ?", (fn_id,)
            ).fetchone()
            if raw_inputs:
                db_inputs = json.loads(raw_inputs[0])
                for port in db_inputs:
                    name = port.get("name")
                    input_names.add(name)
                    inputs[name] = {
                        "type": port.get("artifact_type"),
                        "required": port.get("required", True),
                        "description": port.get("description", ""),
                    }

        outputs: dict[str, Any] = {}
        if function_def:
            for port in function_def.outputs:
                description = port.description or f"{port.name} output"
                outputs[port.name] = {
                    "type": port.artifact_type,
                    "description": description,
                }
        else:
            # Fallback to DB outputs
            raw_outputs = self._index._conn.execute(
                "SELECT outputs_json FROM functions WHERE fn_id = ?", (fn_id,)
            ).fetchone()
            if raw_outputs:
                db_outputs = json.loads(raw_outputs[0])
                for port in db_outputs:
                    name = port.get("name")
                    outputs[name] = {
                        "type": port.get("artifact_type"),
                        "description": port.get("description", ""),
                    }

        hints = (
            function_def.hints.model_dump(exclude_none=True)
            if function_def and function_def.hints
            else None
        )

        params_schema = payload.get("schema", {})
        introspection_source = payload.get("introspection_source", "manual")
        callable_fingerprint = None

        # Get tool version for metadata block
        tool_id = payload.get("tool_id")
        tool = self._index.get_tool(tool_id)
        tool_version = tool["tool_version"] if tool else "unknown"

        # Try to get enriched schema from DB cache or via meta.describe.
        # Only do this when the tool's recorded manifest_path exists on disk.
        if manifest:
            tool_row = self._index._conn.execute(
                "SELECT manifest_path FROM tools WHERE tool_id = ?",
                (manifest.tool_id,),
            ).fetchone()
            db_manifest_path = tool_row[0] if tool_row else None

            if db_manifest_path and Path(db_manifest_path).exists():
                # Compute hashes for cache lookups and invalidation
                project_root = _find_project_root(manifest.manifest_path.parent)
                env_lock_hash = _compute_env_lock_hash(project_root, manifest.env_id)

                module = node.module or (function_def.module if function_def else None)
                callable_name = payload.get("name") or fn_id.split(".")[-1]
                source_hash = _compute_source_hash(
                    manifest,
                    module=module,
                    callable_name=callable_name,
                    project_root=project_root,
                )

                # Check DB cache first
                cached = self._index.get_cached_schema(
                    tool_id=manifest.tool_id,
                    tool_version=manifest.tool_version,
                    fn_id=fn_id,
                    env_lock_hash=env_lock_hash,
                    source_hash=source_hash,
                )
                if cached:
                    params_schema = cached["params_schema"]
                    introspection_source = cached.get("introspection_source", "manual")
                    callable_fingerprint = cached.get("source_hash")
                else:
                    entrypoint = manifest.entrypoint
                    entry_path = Path(entrypoint)
                    if not entry_path.is_absolute():
                        candidate = manifest.manifest_path.parent / entry_path
                        if candidate.exists():
                            entrypoint = str(candidate)

                    request = {
                        "command": "execute",
                        "ordinal": 0,
                        "fn_id": "meta.describe",
                        "params": {"target_fn": fn_id},
                        "inputs": {},
                        "work_dir": str(config.artifact_store_root / "work" / "describe"),
                    }
                    try:
                        response, _log_text, _exit_code = execute_tool(
                            entrypoint=entrypoint,
                            request=request,
                            env_id=manifest.env_id,
                        )
                        result = parse_meta_describe_result(response)
                        if result:
                            params_schema = result["params_schema"]
                            introspection_source = result["introspection_source"]
                            callable_fingerprint = result.get("callable_fingerprint")

                            # Cache the result with invalidation hashes
                            self._index.upsert_schema_cache(
                                tool_id=manifest.tool_id,
                                tool_version=manifest.tool_version,
                                fn_id=fn_id,
                                params_schema=params_schema,
                                introspection_source=introspection_source,
                                env_lock_hash=env_lock_hash,
                                callable_fingerprint=callable_fingerprint or source_hash,
                                source_hash=source_hash,
                            )
                    except Exception as exc:
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.warning(
                            "meta.describe call failed for %s: %s",
                            fn_id,
                            exc,
                        )
                        # Continue with manifest schema as fallback

                # Synchronize functions table so list/describe cannot diverge
                if cached or manifest:
                    row = self._index._conn.execute(
                        "SELECT name, description, tags_json, inputs_json, outputs_json, "
                        "module, io_pattern FROM functions WHERE fn_id = ?",
                        (fn_id,),
                    ).fetchone()
                    if row:
                        self._index.upsert_function(
                            fn_id=fn_id,
                            tool_id=manifest.tool_id,
                            name=row["name"],
                            description=row["description"],
                            tags=json.loads(row["tags_json"]),
                            inputs=json.loads(row["inputs_json"]),
                            outputs=json.loads(row["outputs_json"]),
                            params_schema=params_schema,
                            introspection_source=introspection_source,
                            module=row["module"],
                            io_pattern=row["io_pattern"],
                        )

        # Contract T036: params_schema contains NO artifact port keys
        if params_schema and "properties" in params_schema:
            properties = params_schema["properties"]
            port_names = input_names | set(outputs.keys())
            # Artifact types to exclude from params_schema
            artifact_types = set(ARTIFACT_TYPES.keys())

            filtered_properties = {}
            for k, v in properties.items():
                # Filter by name
                if k in port_names:
                    continue
                # Filter by type (T109)
                if isinstance(v, dict) and v.get("type") in artifact_types:
                    continue
                filtered_properties[k] = v

            params_schema["properties"] = filtered_properties
            if "required" in params_schema:
                params_schema["required"] = [
                    r
                    for r in params_schema["required"]
                    if r not in port_names
                    and (
                        not isinstance(properties.get(r), dict)
                        or properties.get(r).get("type") not in artifact_types
                    )
                ]

        return {
            "id": fn_id,
            "type": "function",
            "summary": node.summary or "",
            "inputs": inputs,
            "outputs": outputs,
            "params_schema": params_schema,
            "meta": {
                "tool_version": tool_version,
                "introspection_source": introspection_source,
                "callable_fingerprint": callable_fingerprint,
                "module": node.module,
            },
            "hints": hints,
        }
