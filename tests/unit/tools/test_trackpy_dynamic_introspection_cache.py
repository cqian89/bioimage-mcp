from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml
from bioimage_mcp_trackpy.entrypoint import handle_meta_list


import os
from pathlib import Path


@pytest.fixture
def mock_trackpy_manifest_path(tmp_path):
    manifest_dir = tmp_path / "tools" / "trackpy"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "manifest.yaml"

    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "tools.trackpy",
        "tool_version": "0.1.0",
        "env_id": "bioimage-mcp-trackpy",
        "entrypoint": "bioimage_mcp_trackpy/entrypoint.py",
        "dynamic_sources": [
            {
                "adapter": "trackpy",
                "prefix": "trackpy.",
                "modules": ["trackpy"],
            }
        ],
    }
    manifest_path.write_text(yaml.dump(manifest_data))
    return manifest_path


@patch("bioimage_mcp_trackpy.entrypoint.TRACKPY_TOOL_ROOT")
@patch("bioimage_mcp_trackpy.dynamic_discovery.introspect_module")
@patch("pathlib.Path.home")
def test_trackpy_handle_meta_list_project_root_heuristics(
    mock_home, mock_introspect, mock_tool_root, mock_trackpy_manifest_path, tmp_path
):
    """Test real project_root detection via CWD and env var."""
    mock_home.return_value = tmp_path / "home"
    mock_tool_root.__truediv__.return_value = mock_trackpy_manifest_path

    # Setup project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    envs_dir = project_root / "envs"
    envs_dir.mkdir()
    lockfile = envs_dir / "bioimage-mcp-trackpy.lock.yml"
    lockfile.write_text("lockfile content")

    # Setup mock introspection
    mock_introspect.return_value = [
        {"fn_id": "tp.test", "name": "test", "io_pattern": "image_to_table", "module": "trackpy"}
    ]

    # 1. Test CWD heuristic
    deep_dir = project_root / "a" / "b"
    deep_dir.mkdir(parents=True)

    old_cwd = os.getcwd()
    os.chdir(deep_dir)
    try:
        # First call: cache miss, should write cache because project_root found via CWD
        result = handle_meta_list({})
        assert result["ok"] is True
        assert mock_introspect.call_count == 1

        cache_file = (
            mock_home.return_value
            / ".bioimage-mcp"
            / "cache"
            / "dynamic"
            / "tools.trackpy"
            / "introspection_cache.json"
        )
        assert cache_file.exists()

        # Second call: cache hit
        handle_meta_list({})
        assert mock_introspect.call_count == 1
    finally:
        os.chdir(old_cwd)

    # 2. Test Env Var override
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    os.chdir(external_dir)
    try:
        # Change lockfile to force re-introspection if it finds project_root
        lockfile.write_text("new content")

        # Without env var, it won't find project_root from external_dir
        # And manifest_path is in tmp_path/tools/trackpy, it won't find project_root at tmp_path/project
        result_no_env = handle_meta_list({})
        assert result_no_env["ok"] is True
        # Should NOT write cache (or rather, use empty hash), so it might introspect again
        # Actually, discover_functions uses lockfile_hash="" if project_root not found.
        # IntrospectionCache.put/get will use "" as lockfile_hash.
        # But wait, discover_functions only uses cache if lockfile_hash is truthy?
        # Let's check src/bioimage_mcp/registry/dynamic/discovery.py
        # line 63: if cache and lockfile_hash:
        # So it BYPASSES cache if lockfile_hash is empty. Correct.

        # Set env var
        with patch.dict(os.environ, {"BIOIMAGE_MCP_PROJECT_ROOT": str(project_root)}):
            handle_meta_list({})
            # Should have found project_root via env var.
            # It's a new lockfile content, so it should introspect.
            # mock_introspect.call_count was already incremented by result_no_env
            current_count = mock_introspect.call_count
            assert current_count == 3  # 1 (CWD) + 1 (no env) + 1 (env first)

            # Next call with env var should hit cache
            handle_meta_list({})
            assert mock_introspect.call_count == current_count

    finally:
        os.chdir(old_cwd)


@patch("bioimage_mcp_trackpy.entrypoint.TRACKPY_TOOL_ROOT")
@patch("bioimage_mcp_trackpy.dynamic_discovery.introspect_module")
@patch("pathlib.Path.home")
def test_trackpy_handle_meta_list_cache_reuse(
    mock_home, mock_introspect, mock_tool_root, mock_trackpy_manifest_path, tmp_path
):
    """Test trackpy cache hit/miss + invalidation driven by lockfile hash."""
    mock_home.return_value = tmp_path / "home"
    mock_tool_root.resolve.return_value = mock_trackpy_manifest_path.parent
    # Ensure TRACKPY_TOOL_ROOT / "manifest.yaml" points to our mock
    mock_tool_root.__truediv__.return_value = mock_trackpy_manifest_path

    # Setup project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    envs_dir = project_root / "envs"
    envs_dir.mkdir()
    lockfile = envs_dir / "bioimage-mcp-trackpy.lock.yml"
    lockfile.write_text("initial lockfile content")

    # Setup mock introspection return
    mock_introspect.return_value = [
        {
            "fn_id": "trackpy.locate",
            "name": "locate",
            "summary": "Locate features in image",
            "module": "trackpy",
            "io_pattern": "image_to_table",
        }
    ]

    # Patch _find_project_root to use our temp setup
    with patch("bioimage_mcp_trackpy.entrypoint._find_project_root") as mock_find:
        mock_find.return_value = project_root

        # 1. First call - should be a cache miss
        result1 = handle_meta_list({})
        assert result1["ok"] is True

        assert mock_introspect.call_count == 1
        assert len(result1["result"]["functions"]) == 1
        assert result1["result"]["introspection_source"] == "dynamic_discovery"
        assert result1["result"]["functions"][0]["fn_id"] == "trackpy.locate"

        # 2. Second call - should be a cache hit (lockfile unchanged)
        result2 = handle_meta_list({})
        assert result2["ok"] is True
        assert mock_introspect.call_count == 1  # Still 1
        assert len(result2["result"]["functions"]) == 1
        assert result1["result"]["functions"] == result2["result"]["functions"]

        # 3. Change lockfile - should be a cache miss
        lockfile.write_text("updated lockfile content")
        result3 = handle_meta_list({})
        assert result3["ok"] is True
        assert mock_introspect.call_count == 2  # Incremented
        assert len(result3["result"]["functions"]) == 1
        assert result3["result"]["functions"][0]["fn_id"] == "trackpy.locate"


@patch("bioimage_mcp_trackpy.entrypoint.TRACKPY_TOOL_ROOT")
@patch("bioimage_mcp_trackpy.dynamic_discovery.introspect_module")
@patch("pathlib.Path.home")
def test_trackpy_handle_meta_list_canonical_shape(
    mock_home, mock_introspect, mock_tool_root, mock_trackpy_manifest_path, tmp_path
):
    """Test trackpy meta.list result shape remains canonical."""
    mock_home.return_value = tmp_path / "home"
    mock_tool_root.__truediv__.return_value = mock_trackpy_manifest_path

    mock_introspect.return_value = [
        {
            "fn_id": "trackpy.batch",
            "name": "batch",
            "summary": "Batch processing",
            "module": "trackpy",
            "io_pattern": "image_to_table",
        }
    ]

    with patch("bioimage_mcp_trackpy.entrypoint._find_project_root") as mock_find:
        mock_find.return_value = tmp_path

        result = handle_meta_list({})
        assert result["ok"] is True
        res = result["result"]
        assert "functions" in res
        assert "tool_version" in res
        assert "introspection_source" in res

        fn = res["functions"][0]
        assert "fn_id" in fn
        assert "name" in fn
        assert "module" in fn
        assert "summary" in fn
        assert "io_pattern" in fn
