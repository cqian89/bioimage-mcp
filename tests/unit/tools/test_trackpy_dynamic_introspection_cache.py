from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml
from bioimage_mcp_trackpy.entrypoint import handle_meta_list


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
