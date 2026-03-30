from __future__ import annotations

import sqlite3
from pathlib import Path

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import init_schema


def _prepare_discovery(tmp_path: Path, monkeypatch) -> DiscoveryService:
    artifacts_root = tmp_path / "artifacts"
    tools_root = tmp_path / "tools"
    tools_root.mkdir()

    base_tool_dir = tools_root / "base"
    base_tool_dir.mkdir()
    manifest_path = base_tool_dir / "manifest.yaml"
    manifest_path.write_text(
        """
manifest_version: "1.0"
tool_id: tools.base
tool_version: "0.2.0"
name: Base Toolkit
env_id: bioimage-mcp-base
entrypoint: entry.py
functions:
  - id: base.skimage.filters.gaussian
    tool_id: tools.base
    name: gaussian
    description: gaussian filter
    inputs: []
    outputs: []
    params_schema: {"type": "object", "properties": {}}
"""
    )

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        schema_cache_path=artifacts_root / "state" / "schema_cache.json",
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    monkeypatch.setattr("bioimage_mcp.api.discovery.load_config", lambda: config)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    service = DiscoveryService(conn)

    from bioimage_mcp.registry.loader import _MANIFEST_CACHE

    _MANIFEST_CACHE.clear()

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


def test_describe_function_uses_db_cache(tmp_path: Path, monkeypatch) -> None:
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
                    "tool_version": "0.2.0",
                    "introspection_source": "python_api",
                },
            },
            "ok",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.discovery.execute_tool", _fake_execute_tool)
    monkeypatch.setattr(
        "bioimage_mcp.api.discovery._compute_env_lock_hash", lambda *args: "env-hash"
    )
    # Use a mutable container to allow changing source hash in test
    source_hash_container = {"value": "src-hash"}
    monkeypatch.setattr(
        "bioimage_mcp.api.discovery._compute_source_hash",
        lambda *args, **kwargs: source_hash_container["value"],
    )

    fn_id = "base.skimage.filters.gaussian"
    first = service.describe_function(id=fn_id)
    assert first["id"] == fn_id
    assert "params_schema" in first
    assert first["params_schema"]["properties"]["sigma"]["type"] == "number"
    assert len(calls) == 1
    assert calls[0]["command"] == "execute"
    assert calls[0]["id"] == "meta.describe"

    # Verify cache hit
    second = service.describe_function(id=fn_id)
    assert second["id"] == fn_id
    assert "params_schema" in second
    assert second["params_schema"]["properties"]["sigma"]["type"] == "number"
    assert len(calls) == 1

    # Verify invalidation on source hash change
    source_hash_container["value"] = "src-hash-v2"
    third = service.describe_function(id=fn_id)
    assert third["id"] == fn_id
    assert len(calls) == 2


def test_describe_function_supports_worker_response(tmp_path: Path, monkeypatch) -> None:
    service = _prepare_discovery(tmp_path, monkeypatch)

    calls = []

    def _fake_execute_tool(
        *, entrypoint: str, request: dict, env_id: str | None, timeout_seconds=None
    ):
        calls.append(request)
        return (
            {
                "ok": True,
                "outputs": {
                    "result": {
                        "params_schema": {
                            "type": "object",
                            "properties": {"sigma": {"type": "number"}},
                            "required": [],
                        },
                        "tool_version": "0.2.0",
                        "introspection_source": "python_api",
                    }
                },
            },
            "ok",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.discovery.execute_tool", _fake_execute_tool)
    monkeypatch.setattr(
        "bioimage_mcp.api.discovery._compute_env_lock_hash", lambda *args: "env-hash"
    )
    monkeypatch.setattr(
        "bioimage_mcp.api.discovery._compute_source_hash", lambda *args, **kwargs: "src-hash"
    )

    fn_id = "base.skimage.filters.gaussian"
    res = service.describe_function(id=fn_id)
    assert res["id"] == fn_id
    assert res["params_schema"]["properties"]["sigma"]["type"] == "number"
    assert res["params_schema"]["type"] == "object"
    assert len(calls) == 1

    # Verify caching
    res2 = service.describe_function(id=fn_id)
    assert res2["id"] == fn_id
    assert res2["params_schema"]["properties"]["sigma"]["type"] == "number"
    assert len(calls) == 1
