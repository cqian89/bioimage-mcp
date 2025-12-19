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
                introspection_source
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fn_id) DO UPDATE SET
              tool_id=excluded.tool_id,
              name=excluded.name,
              description=excluded.description,
              tags_json=excluded.tags_json,
              inputs_json=excluded.inputs_json,
              outputs_json=excluded.outputs_json,
              params_schema_json=excluded.params_schema_json,
              introspection_source=excluded.introspection_source
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
        q = f"%{query}%"
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
