from __future__ import annotations

import os
import time

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect

pytestmark = pytest.mark.skipif(
    os.getenv("BIOIMAGE_MCP_RUN_PERF") != "1",
    reason="perf test (set BIOIMAGE_MCP_RUN_PERF=1 to run)",
)


def test_discovery_queries_are_reasonably_fast(monkeypatch, tmp_path) -> None:
    """Sanity check for discovery query latency.

    Thresholds are intentionally conservative and the test is skipped by default.
    """

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
        default_pagination_limit=20,
        max_pagination_limit=200,
    )
    monkeypatch.setattr("bioimage_mcp.api.discovery.load_config", lambda: config)

    conn = connect(config)
    service = DiscoveryService(conn)

    service.upsert_tool(
        tool_id="perf.tool",
        name="perf",
        description="perf",
        tool_version="0.0.0",
        env_id="bioimage-mcp-base",
        manifest_path=str(tmp_path / "tools" / "manifest.yaml"),
        available=True,
        installed=True,
    )

    for idx in range(500):
        service.upsert_function(
            fn_id=f"perf.fn_{idx:04d}",
            tool_id="perf.tool",
            name=f"Perf Function {idx}",
            description="Synthetic function for perf testing",
            tags=["perf", "synthetic"],
            inputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
            outputs=[{"name": "image", "artifact_type": "BioImageRef", "required": True}],
            params_schema={},
        )

    start = time.perf_counter()
    tools_page = service.list_tools(limit=20, cursor=None)
    tools_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    functions_page = service.search_functions(query="perf", limit=50, cursor=None)
    search_elapsed = time.perf_counter() - start

    assert tools_page["tools"]
    assert functions_page["functions"]

    assert tools_elapsed < 2.0
    assert search_elapsed < 2.0
