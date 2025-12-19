from __future__ import annotations

import json
from pathlib import Path

from bioimage_mcp.registry.schema_cache import SchemaCache


def test_schema_cache_invalidate_tool_removes_versions(tmp_path: Path) -> None:
    cache_path = tmp_path / "state" / "schema_cache.json"
    cache = SchemaCache(cache_path)

    cache.set(
        tool_id="tools.base",
        tool_version="0.1.0",
        fn_id="base.gaussian",
        params_schema={"type": "object", "properties": {}},
        introspection_source="manual",
    )
    cache.set(
        tool_id="tools.base",
        tool_version="0.2.0",
        fn_id="base.sobel",
        params_schema={"type": "object", "properties": {}},
        introspection_source="manual",
    )
    cache.set(
        tool_id="tools.other",
        tool_version="1.0.0",
        fn_id="other.fn",
        params_schema={"type": "object", "properties": {}},
        introspection_source="manual",
    )

    cache.invalidate_tool(tool_id="tools.base")

    data = json.loads(cache_path.read_text())
    tools = data.get("tools", {})
    assert "tools.base@0.1.0" not in tools
    assert "tools.base@0.2.0" not in tools
    assert "tools.other@1.0.0" in tools
