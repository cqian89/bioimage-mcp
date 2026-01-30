from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SchemaCache:
    """File-backed cache for enriched function schemas."""

    _SCHEMA_VERSION = "0.1"

    def __init__(self, path: Path):
        self._path = path

    def get(
        self,
        *,
        tool_id: str,
        tool_version: str,
        id: str | None = None,
        fn_id: str | None = None,
    ) -> dict[str, Any] | None:
        actual_id = id or fn_id
        if not actual_id:
            raise ValueError("id or fn_id is required")

        data = self._load()
        tool_key = f"{tool_id}@{tool_version}"
        entry = data.get("tools", {}).get(tool_key, {}).get("functions", {}).get(actual_id)
        if not isinstance(entry, dict):
            return None
        if "params_schema" not in entry:
            return None
        return entry

    def set(
        self,
        *,
        tool_id: str,
        tool_version: str,
        id: str | None = None,
        fn_id: str | None = None,
        params_schema: dict[str, Any],
        introspection_source: str,
    ) -> None:
        actual_id = id or fn_id
        if not actual_id:
            raise ValueError("id or fn_id is required")

        data = self._load()
        tools = data.setdefault("tools", {})
        tool_key = f"{tool_id}@{tool_version}"
        tool_entry = tools.setdefault(tool_key, {})
        functions = tool_entry.setdefault("functions", {})
        functions[actual_id] = {
            "params_schema": params_schema,
            "introspection_source": introspection_source,
            "introspected_at": datetime.now(UTC).isoformat(),
        }
        self._write(data)

    def invalidate_tool(self, *, tool_id: str) -> None:
        data = self._load()
        tools = data.get("tools", {})
        to_delete = [key for key in tools if key.startswith(f"{tool_id}@")]
        for key in to_delete:
            tools.pop(key, None)
        if to_delete:
            self._write(data)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"schema_version": self._SCHEMA_VERSION, "tools": {}}
        try:
            raw = self._path.read_text()
            data = json.loads(raw)
        except Exception:
            return {"schema_version": self._SCHEMA_VERSION, "tools": {}}
        if not isinstance(data, dict):
            return {"schema_version": self._SCHEMA_VERSION, "tools": {}}
        if data.get("schema_version") != self._SCHEMA_VERSION:
            return {"schema_version": self._SCHEMA_VERSION, "tools": {}}
        if "tools" not in data or not isinstance(data.get("tools"), dict):
            data["tools"] = {}
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, sort_keys=True))
