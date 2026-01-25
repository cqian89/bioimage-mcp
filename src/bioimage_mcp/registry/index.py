from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from bioimage_mcp.registry.diagnostics import ManifestDiagnostic


class RegistryIndex:
    def __init__(self, conn: sqlite3.Connection, *, owns_conn: bool = False):
        self._conn = conn
        self._owns_conn = owns_conn

    def close(self) -> None:
        if self._owns_conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def upsert_tool(
        self,
        *,
        tool_id: str,
        name: str,
        description: str,
        tool_version: str,
        env_id: str,
        manifest_path: str,
        installed: bool,
        available: bool,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO tools(
                tool_id,
                tool_version,
                env_id,
                description,
                manifest_path,
                installed,
                available
            )
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tool_id) DO UPDATE SET
              tool_version=excluded.tool_version,
              env_id=excluded.env_id,
              description=excluded.description,
              manifest_path=excluded.manifest_path,
              installed=excluded.installed,
              available=excluded.available
            """,
            (
                tool_id,
                tool_version,
                env_id,
                json.dumps({"name": name, "description": description}),
                manifest_path,
                int(installed),
                int(available),
            ),
        )
        self._conn.commit()

    def upsert_function(
        self,
        *,
        fn_id: str,
        tool_id: str,
        name: str,
        description: str,
        tags: list[str],
        inputs: list[dict],
        outputs: list[dict],
        params_schema: dict,
        introspection_source: str | None = None,
        module: str | None = None,
        io_pattern: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO functions(
                fn_id,
                tool_id,
                name,
                description,
                tags_json,
                inputs_json,
                outputs_json,
                params_schema_json,
                introspection_source,
                module,
                io_pattern
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fn_id) DO UPDATE SET
              tool_id=excluded.tool_id,
              name=excluded.name,
              description=excluded.description,
              tags_json=excluded.tags_json,
              inputs_json=excluded.inputs_json,
              outputs_json=excluded.outputs_json,
              params_schema_json=excluded.params_schema_json,
              introspection_source=excluded.introspection_source,
              module=excluded.module,
              io_pattern=excluded.io_pattern
            """,
            (
                fn_id,
                tool_id,
                name,
                description,
                json.dumps(tags),
                json.dumps(inputs),
                json.dumps(outputs),
                json.dumps(params_schema),
                introspection_source,
                module,
                io_pattern,
            ),
        )
        self._conn.commit()

    def record_diagnostic(self, diagnostic: ManifestDiagnostic) -> None:
        self._conn.execute(
            "INSERT INTO diagnostics(manifest_path, tool_id, errors_json) VALUES(?, ?, ?)",
            (str(diagnostic.path), diagnostic.tool_id, json.dumps(diagnostic.errors)),
        )
        self._conn.commit()

    def clear_diagnostics(self) -> None:
        self._conn.execute("DELETE FROM diagnostics")
        self._conn.commit()

    def list_tools(self, *, after_tool_id: str | None, limit: int) -> list[dict]:
        if after_tool_id:
            rows = self._conn.execute(
                "SELECT tool_id, tool_version, description "
                "FROM tools WHERE tool_id > ? "
                "ORDER BY tool_id LIMIT ?",
                (after_tool_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT tool_id, tool_version, description FROM tools ORDER BY tool_id LIMIT ?",
                (limit,),
            ).fetchall()

        tools: list[dict] = []
        for row in rows:
            desc = json.loads(row["description"])
            tools.append(
                {
                    "tool_id": row["tool_id"],
                    "name": desc.get("name", row["tool_id"]),
                    "description": desc.get("description", ""),
                    "tool_version": row["tool_version"],
                }
            )
        return tools

    def list_functions(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT fn_id, tool_id, name, description, inputs_json, outputs_json, "
            "module, io_pattern, introspection_source FROM functions ORDER BY fn_id"
        ).fetchall()
        return [
            {
                "fn_id": row["fn_id"],
                "tool_id": row["tool_id"],
                "name": row["name"],
                "description": row["description"],
                "inputs": json.loads(row["inputs_json"]),
                "outputs": json.loads(row["outputs_json"]),
                "module": row["module"],
                "io_pattern": row["io_pattern"],
                "introspection_source": row["introspection_source"],
            }
            for row in rows
        ]

    def get_tool(self, tool_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT tool_id, tool_version, description FROM tools WHERE tool_id = ?", (tool_id,)
        ).fetchone()
        if row is None:
            return None
        desc = json.loads(row["description"])
        return {
            "tool_id": row["tool_id"],
            "name": desc.get("name", row["tool_id"]),
            "description": desc.get("description", ""),
            "tool_version": row["tool_version"],
        }

    def get_functions_for_tool(self, tool_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT fn_id, tool_id, name, description, tags_json "
            "FROM functions WHERE tool_id = ? ORDER BY fn_id",
            (tool_id,),
        ).fetchall()
        return [
            {
                "fn_id": r["fn_id"],
                "tool_id": r["tool_id"],
                "name": r["name"],
                "description": r["description"],
                "tags": json.loads(r["tags_json"]),
            }
            for r in rows
        ]

    def get_function(self, fn_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT fn_id, params_schema_json, introspection_source FROM functions WHERE fn_id = ?",
            (fn_id,),
        ).fetchone()
        if row is None:
            return None
        result = {
            "fn_id": row["fn_id"],
            "schema": json.loads(row["params_schema_json"]),
        }
        if row["introspection_source"]:
            result["introspection_source"] = row["introspection_source"]
        return result

    def iter_search_functions(
        self,
        *,
        query: str,
        after_fn_id: str | None,
        batch_size: int,
    ) -> list[dict]:
        normalized = " ".join(query.split())
        q = f"%{normalized.replace(' ', '%')}%"
        if query:
            where = "(fn_id LIKE ? OR name LIKE ? OR description LIKE ? OR tags_json LIKE ?)"
            params: list[object] = [q, q, q, q]
        else:
            where = "1=1"
            params = []

        if after_fn_id:
            where = f"fn_id > ? AND {where}"
            params = [after_fn_id, *params]

        sql = (
            "SELECT fn_id, tool_id, name, description, tags_json, inputs_json, outputs_json "
            f"FROM functions WHERE {where} ORDER BY fn_id LIMIT ?"
        )
        params.append(batch_size)
        rows = self._conn.execute(sql, params).fetchall()

        results: list[dict] = []
        for r in rows:
            results.append(
                {
                    "fn_id": r["fn_id"],
                    "tool_id": r["tool_id"],
                    "name": r["name"],
                    "description": r["description"],
                    "tags": json.loads(r["tags_json"]),
                    "inputs": json.loads(r["inputs_json"]),
                    "outputs": json.loads(r["outputs_json"]),
                }
            )
        return results

    # Schema cache methods for meta.describe protocol (T000g, T000g2)

    def get_cached_schema(
        self,
        *,
        tool_id: str,
        tool_version: str,
        fn_id: str,
    ) -> dict | None:
        """Get cached params_schema if it exists and version matches.

        Returns None if no cache entry exists or if tool_version has changed
        (indicating cache invalidation is needed).
        """
        row = self._conn.execute(
            """
            SELECT params_schema_json, introspection_source, tool_version
            FROM schema_cache
            WHERE tool_id = ? AND fn_id = ?
            """,
            (tool_id, fn_id),
        ).fetchone()

        if row is None:
            return None

        # Invalidate cache if tool version changed
        if row["tool_version"] != tool_version:
            return None

        return {
            "params_schema": json.loads(row["params_schema_json"]),
            "introspection_source": row["introspection_source"],
        }

    def upsert_schema_cache(
        self,
        *,
        tool_id: str,
        tool_version: str,
        fn_id: str,
        params_schema: dict,
        introspection_source: str,
    ) -> None:
        """Cache a params_schema obtained via meta.describe."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO schema_cache(
                tool_id, tool_version, fn_id,
                params_schema_json, introspection_source, introspected_at
            )
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(tool_id, fn_id) DO UPDATE SET
              tool_version=excluded.tool_version,
              params_schema_json=excluded.params_schema_json,
              introspection_source=excluded.introspection_source,
              introspected_at=excluded.introspected_at
            """,
            (
                tool_id,
                tool_version,
                fn_id,
                json.dumps(params_schema),
                introspection_source,
                now,
            ),
        )
        self._conn.commit()

    def invalidate_schema_cache(self, *, tool_id: str) -> None:
        """Invalidate all cached schemas for a tool (e.g., on version change)."""
        self._conn.execute(
            "DELETE FROM schema_cache WHERE tool_id = ?",
            (tool_id,),
        )
        self._conn.commit()

    def prune_stale_functions(self, valid_fn_ids: set[str]) -> int:
        """Delete functions not in the valid set.

        Args:
            valid_fn_ids: Set of fn_ids that should be kept.

        Returns:
            Number of deleted rows.
        """
        if not valid_fn_ids:
            # If no valid functions provided, delete all
            cursor = self._conn.execute("DELETE FROM functions")
        else:
            placeholders = ",".join("?" for _ in valid_fn_ids)
            cursor = self._conn.execute(
                f"DELETE FROM functions WHERE fn_id NOT IN ({placeholders})",
                tuple(valid_fn_ids),
            )
        deleted = cursor.rowcount
        self._conn.commit()
        return deleted

    def prune_stale_tools(self, valid_tool_ids: set[str]) -> int:
        """Delete tools not in the valid set.

        Args:
            valid_tool_ids: Set of tool_ids that should be kept.

        Returns:
            Number of deleted rows.
        """
        if not valid_tool_ids:
            # If no valid tools provided, delete all
            cursor = self._conn.execute("DELETE FROM tools")
        else:
            placeholders = ",".join("?" for _ in valid_tool_ids)
            cursor = self._conn.execute(
                f"DELETE FROM tools WHERE tool_id NOT IN ({placeholders})",
                tuple(valid_tool_ids),
            )
        deleted = cursor.rowcount
        self._conn.commit()
        return deleted


class _HierarchyNode:
    def __init__(
        self,
        name: str,
        full_path: str,
        node_type: str,
        *,
        fn_id: str | None = None,
        summary: str | None = None,
        inputs: list[dict] | None = None,
        outputs: list[dict] | None = None,
    ) -> None:
        self.name = name
        self.full_path = full_path
        self.type = node_type
        self.fn_id = fn_id
        self.summary = summary
        self.inputs = inputs
        self.outputs = outputs
        self.children: dict[str, _HierarchyNode] = {}


class ToolIndex:
    """Hierarchical index for tool discovery."""

    def __init__(self, functions: list[dict]) -> None:
        self._functions = functions
        self._root = _HierarchyNode("", "", "root")
        self._path_index: dict[str, _HierarchyNode] = {"": self._root}

    def build_hierarchy(self) -> None:
        for fn in self._functions:
            fn_id = str(fn["fn_id"])
            tool_id = fn.get("tool_id")
            env_name = self._env_name(fn_id, tool_id)
            segments = fn_id.split(".") if fn_id else []
            if env_name and segments and segments[0] != env_name:
                segments = [env_name, *segments]

            if not segments:
                continue

            self._insert_path(
                segments,
                fn_id,
                fn.get("description"),
                fn.get("inputs"),
                fn.get("outputs"),
            )

    def list_children(
        self, path: str | None, *, auto_expand: bool = True
    ) -> tuple[list[dict], str | None]:
        node = self._resolve_path(path)
        if node is None:
            return [], None

        expanded_from = None
        if auto_expand and path:
            while node.type != "function":
                children = list(node.children.values())
                if len(children) != 1:
                    break
                node = children[0]
                if expanded_from is None:
                    expanded_from = path

        if node.type == "function":
            nodes = [node]
        else:
            nodes = list(node.children.values())

        payloads = [self._to_payload(n) for n in nodes]
        payloads.sort(key=lambda entry: entry["full_path"])
        return payloads, expanded_from

    def flatten_tools(self, path: str | None) -> list[dict]:
        node = self._resolve_path(path)
        if node is None:
            return []

        collected: list[_HierarchyNode] = []
        self._collect_functions(node, collected)
        payloads = [self._to_payload(n) for n in collected]
        payloads.sort(key=lambda entry: entry["full_path"])
        return payloads

    def _collect_functions(self, node: _HierarchyNode, collected: list[_HierarchyNode]) -> None:
        if node.type == "function":
            collected.append(node)
            return
        for child in sorted(node.children.values(), key=lambda n: n.full_path):
            self._collect_functions(child, collected)

    def _resolve_path(self, path: str | None) -> _HierarchyNode | None:
        if path is None or path == "":
            return self._root
        return self._path_index.get(path)

    def _insert_path(
        self,
        segments: list[str],
        fn_id: str,
        summary: str | None,
        inputs: list[dict] | None = None,
        outputs: list[dict] | None = None,
    ) -> None:
        node = self._root
        for idx, segment in enumerate(segments):
            is_last = idx == len(segments) - 1
            node_type = self._node_type(idx, is_last)
            full_path = ".".join(segments[: idx + 1])
            existing = node.children.get(segment)
            if existing is None:
                existing = _HierarchyNode(segment, full_path, node_type)
                node.children[segment] = existing
                self._path_index[full_path] = existing

            if is_last:
                existing.fn_id = fn_id
                existing.summary = summary
                existing.inputs = inputs
                existing.outputs = outputs
            node = existing

    @staticmethod
    def _node_type(depth: int, is_last: bool) -> str:
        if is_last:
            return "function"
        if depth == 0:
            return "environment"
        if depth == 1:
            return "package"
        return "module"

    @staticmethod
    def _env_name(fn_id: str, tool_id: str | None) -> str:
        if tool_id and tool_id.startswith("tools."):
            return tool_id.split(".", 1)[1]
        if tool_id and "." in tool_id and tool_id.split(".", 1)[0] == "tools":
            return tool_id.split(".", 1)[1]
        return fn_id.split(".", 1)[0]

    def _to_payload(self, node: _HierarchyNode) -> dict:
        payload = {
            "id": node.full_path,
            "name": node.name,
            "type": node.type,
            "summary": node.summary,
            "has_children": bool(node.children),
        }

        if node.children:
            total = 0
            by_type: dict[str, int] = {}

            def count_recursive(n: _HierarchyNode):
                nonlocal total
                for child in n.children.values():
                    total += 1
                    by_type[child.type] = by_type.get(child.type, 0) + 1
                    count_recursive(child)

            # Contract T033: Non-leaf nodes should include children.total and children.by_type.
            # Wait, is total the count of immediate children or all descendants?
            # schemas.py says: "Child count statistics for non-leaf nodes."
            # Usually 'children' refers to immediate children in a hierarchy listing.
            # Let's see what the tests expect.

            # Re-reading T033: "Each non-leaf node has children.total > 0".
            # I'll use immediate children for now.
            total = len(node.children)
            for child in node.children.values():
                by_type[child.type] = by_type.get(child.type, 0) + 1

            payload["children"] = {
                "total": total,
                "by_type": by_type,
            }

        if node.type == "function":
            # Contract T034: Function nodes should include io.inputs and io.outputs summaries.
            inputs = []
            if node.inputs:
                for inp in node.inputs:
                    inputs.append(
                        {
                            "name": inp.get("name"),
                            "type": inp.get("artifact_type"),
                            "required": inp.get("required", True),
                        }
                    )

            outputs = []
            if node.outputs:
                for out in node.outputs:
                    outputs.append({"name": out.get("name"), "type": out.get("artifact_type")})

            payload["io"] = {"inputs": inputs, "outputs": outputs}
            # Keep fn_id for backward compatibility if needed, but the new schema uses 'id'
            payload["fn_id"] = node.fn_id or node.full_path

        # Add full_path for pagination logic in DiscoveryService
        payload["full_path"] = node.full_path

        return payload
