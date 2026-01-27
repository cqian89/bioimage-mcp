"""Integration test for trackpy out-of-process discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.registry.loader import load_manifest_file
from bioimage_mcp.registry.engine import DiscoveryEngine


@pytest.fixture
def trackpy_manifest():
    """Load the trackpy manifest for testing."""
    manifest_path = Path("tools/trackpy/manifest.yaml")
    # load_manifest_file now triggers discovery via DiscoveryEngine internally
    manifest, diag = load_manifest_file(manifest_path)
    assert manifest is not None
    return manifest


@pytest.mark.requires_env("bioimage-mcp-trackpy")
@pytest.mark.integration
def test_discovery_returns_trackpy_functions(trackpy_manifest):
    """Verify DiscoveryEngine returns many trackpy functions including core ones."""
    # The manifest already has functions if load_manifest_file succeeded
    functions = trackpy_manifest.functions

    # Should discover many functions (broad v0.7 API coverage)
    assert len(functions) >= 100, f"Expected >=100 functions, got {len(functions)}"

    # Core functions should be present
    fn_ids = {f.fn_id for f in functions}
    # DiscoveryEngine prefixes with the env name (trackpy) if configured so in manifest or by default
    # But let's check what's actually produced.
    core_fns = {"trackpy.locate", "trackpy.link", "trackpy.batch"}
    missing = core_fns - fn_ids
    assert not missing, f"Missing core functions: {missing}. Found: {list(fn_ids)[:5]}"


@pytest.mark.requires_env("bioimage-mcp-trackpy")
@pytest.mark.integration
def test_mcp_list_and_describe_include_trackpy(mcp_test_client):
    """Verify MCP list/describe exposes trackpy after subprocess discovery."""
    # list: find trackpy.locate and trackpy.link
    # The hierarchy path starts with the env name (trackpy)
    list_result = mcp_test_client.list_tools(path="trackpy", flatten=True, limit=200)
    items = list_result.get("items", [])
    fn_ids = {i.get("id") or i.get("fn_id") for i in items}
    print(f"Discovered IDs count under 'trackpy': {len(fn_ids)}")

    assert "trackpy.locate" in fn_ids
    assert "trackpy.link" in fn_ids

    # describe: schema exists
    describe_locate = mcp_test_client.describe_function("trackpy.locate")
    assert "params_schema" in describe_locate
    assert "diameter" in (describe_locate.get("params_schema") or {}).get("properties", {})
