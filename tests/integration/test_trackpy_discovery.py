"""Integration test for trackpy out-of-process discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.registry.loader import _discover_via_subprocess, load_manifest_file


@pytest.fixture
def trackpy_manifest():
    """Load the trackpy manifest for testing."""
    manifest_path = Path("tools/trackpy/manifest.yaml")
    manifest, diag = load_manifest_file(manifest_path)
    # Note: load_manifest_file will now trigger discovery, which might fail
    # if dependencies aren't right, but we want to test the raw subprocess call.
    assert manifest is not None
    return manifest


@pytest.mark.requires_env("bioimage-mcp-trackpy")
@pytest.mark.integration
def test_discover_via_subprocess_returns_trackpy_functions(trackpy_manifest):
    """Verify _discover_via_subprocess returns many trackpy functions including core ones."""
    functions = _discover_via_subprocess(trackpy_manifest)

    # Should discover many functions (broad v0.7 API coverage)
    assert len(functions) >= 100, f"Expected >=100 functions, got {len(functions)}"

    # Core functions should be present
    fn_ids = {f.fn_id for f in functions}
    # Note: env prefix might be added by the loader, but _discover_via_subprocess returns raw IDs
    core_fns = {"trackpy.locate", "trackpy.link", "trackpy.batch"}
    missing = core_fns - fn_ids
    assert not missing, f"Missing core functions: {missing}"


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
