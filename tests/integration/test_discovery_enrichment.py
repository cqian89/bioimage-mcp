from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import init_schema


def _prepare_discovery(tmp_path: Path, monkeypatch) -> DiscoveryService:
    artifacts_root = tmp_path / "artifacts"
    tools_root = Path(__file__).parent.parent.parent / "tools"
    schema_cache_path = artifacts_root / "state" / "schema_cache.json"

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        schema_cache_path=schema_cache_path,
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    monkeypatch.setattr("bioimage_mcp.api.discovery.load_config", lambda: config)

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    service = DiscoveryService(conn)

    manifests, _ = load_manifests(config.tool_manifest_roots)
    for manifest in manifests:
        service.upsert_tool(
            tool_id=manifest.tool_id,
            name=manifest.name,
            description=manifest.description,
            tool_version=manifest.tool_version,
            env_id=manifest.env_id,
            manifest_path=str(manifest.manifest_path),
            available=True,
            installed=True,
        )
        for fn in manifest.functions:
            service.upsert_function(
                fn_id=fn.fn_id,
                tool_id=fn.tool_id,
                name=fn.name,
                description=fn.description,
                tags=fn.tags,
                inputs=[p.model_dump() for p in fn.inputs],
                outputs=[p.model_dump() for p in fn.outputs],
                params_schema=fn.params_schema,
            )

    return service


def test_describe_function_uses_json_cache(tmp_path: Path, monkeypatch) -> None:
    service = _prepare_discovery(tmp_path, monkeypatch)

    calls: list[dict] = []

    def _fake_execute_tool(
        *, entrypoint: str, request: dict, env_id: str | None, timeout_seconds=None
    ):
        calls.append(request)
        return (
            {
                "ok": True,
                "result": {
                    "params_schema": {
                        "type": "object",
                        "properties": {"sigma": {"type": "number"}},
                        "required": [],
                    },
                    "tool_version": "0.1.0",
                    "introspection_source": "python_api",
                },
            },
            "ok",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.discovery.execute_tool", _fake_execute_tool)

    fn_id = "base.skimage.filters.gaussian"
    first = service.describe_function(fn_id)
    assert "schema" in first
    assert "params_schema" not in first
    assert first["id"] == fn_id
    assert first["params_schema"]["properties"]["sigma"]["type"] == "number"
    assert len(calls) == 1

    second = service.describe_function(fn_id)
    assert "schema" in second
    assert "params_schema" not in second
    assert second["id"] == fn_id
    assert second["params_schema"]["properties"]["sigma"]["type"] == "number"
    assert len(calls) == 1

    cache_path = tmp_path / "artifacts" / "state" / "schema_cache.json"
    assert cache_path.exists()
    cache_data = json.loads(cache_path.read_text())
    tool_key = "tools.base@0.1.0"
    assert tool_key in cache_data.get("tools", {})
    assert fn_id in cache_data["items"][tool_key]["results"]
