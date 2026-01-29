from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml
from bioimage_mcp_base.entrypoint import handle_meta_list

from bioimage_mcp.registry.dynamic.models import FunctionMetadata, IOPattern


@pytest.fixture
def mock_manifest_path(tmp_path):
    manifest_dir = tmp_path / "tools" / "base"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "manifest.yaml"

    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "tools.base",
        "tool_version": "0.2.0",
        "env_id": "bioimage-mcp-base",
        "entrypoint": "bioimage_mcp_base/entrypoint.py",
        "dynamic_sources": [
            {"adapter": "mock_adapter", "prefix": "base.mock.", "modules": ["mock_module"]}
        ],
    }
    manifest_path.write_text(yaml.dump(manifest_data))
    return manifest_path


@patch("bioimage_mcp_base.entrypoint.BASE_DIR")
@patch("bioimage_mcp.registry.dynamic.discovery.discover_functions")
@patch("pathlib.Path.home")
def test_handle_meta_list_wiring(
    mock_home, mock_discover, mock_base_dir, mock_manifest_path, tmp_path
):
    """Test A: handle_meta_list passes cache + project_root to discover_functions."""
    mock_home.return_value = tmp_path / "home"
    mock_base_dir.parent = mock_manifest_path.parent
    mock_discover.return_value = []

    # Create project root indicators
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "envs").mkdir()

    with patch("bioimage_mcp_base.entrypoint._find_project_root") as mock_find:
        mock_find.return_value = project_root

        result = handle_meta_list({})

        if not result["ok"]:
            pytest.fail(f"handle_meta_list failed: {result.get('error')}")

        assert result["ok"] is True
        mock_discover.assert_called_once()

        # Check arguments passed to discover_functions
        _args, kwargs = mock_discover.call_args
        assert "cache" in kwargs
        assert "project_root" in kwargs
        assert kwargs["project_root"] == project_root

        from bioimage_mcp.registry.dynamic.cache import IntrospectionCache

        assert isinstance(kwargs["cache"], IntrospectionCache)
        assert (
            kwargs["cache"].cache_dir
            == tmp_path / "home" / ".bioimage-mcp" / "cache" / "dynamic" / "tools.base"
        )


def test_handle_meta_list_cache_reuse(mock_manifest_path, tmp_path):
    """Test B: cache hit/miss + invalidation driven by lockfile hash."""
    # Setup project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    envs_dir = project_root / "envs"
    envs_dir.mkdir()
    lockfile = envs_dir / "bioimage-mcp-base.lock.yml"
    lockfile.write_text("initial lockfile content")

    # Setup mock adapter
    discover_count = 0

    class MockAdapter:
        def discover(self, config):
            nonlocal discover_count
            discover_count += 1
            return [
                FunctionMetadata(
                    fn_id="base.mock.test",
                    name="test",
                    module="mock_module",
                    qualified_name="mock_module.test",
                    description="mock test function",
                    parameters={},
                    returns="None",
                    io_pattern=IOPattern.GENERIC,
                    source_adapter="mock_adapter",
                )
            ]

    adapter_registry = {"mock_adapter": MockAdapter()}

    # Patch BASE_DIR and _find_project_root to use our temp setup
    with (
        patch("bioimage_mcp_base.entrypoint.BASE_DIR") as mock_base_dir,
        patch("bioimage_mcp_base.entrypoint._find_project_root") as mock_find,
        patch("pathlib.Path.home") as mock_home,
        patch("bioimage_mcp.registry.dynamic.adapters.ADAPTER_REGISTRY", adapter_registry),
    ):
        mock_base_dir.parent = mock_manifest_path.parent
        mock_find.return_value = project_root
        mock_home.return_value = tmp_path / "home"  # Cache will be under here

        # 1. First call - should be a cache miss (cache empty)
        result1 = handle_meta_list({})
        if not result1["ok"]:
            pytest.fail(f"handle_meta_list failed (1): {result1.get('error')}")
        assert result1["ok"] is True
        assert discover_count == 1
        assert len(result1["result"]["functions"]) == 1

        # 2. Second call - should be a cache hit (lockfile unchanged)
        result2 = handle_meta_list({})
        if not result2["ok"]:
            pytest.fail(f"handle_meta_list failed (2): {result2.get('error')}")
        assert result2["ok"] is True
        assert discover_count == 1  # Still 1
        assert len(result2["result"]["functions"]) == 1
        assert result1["result"]["functions"] == result2["result"]["functions"]

        # 3. Change lockfile - should be a cache miss
        lockfile.write_text("updated lockfile content")
        result3 = handle_meta_list({})
        if not result3["ok"]:
            pytest.fail(f"handle_meta_list failed (3): {result3.get('error')}")
        assert result3["ok"] is True
        assert discover_count == 2  # Incremented
        assert len(result3["result"]["functions"]) == 1

        # 4. Change manifest - should be a cache miss (T13.07)
        manifest_data = yaml.safe_load(mock_manifest_path.read_text())
        manifest_data["description"] = "new description"
        mock_manifest_path.write_text(yaml.dump(manifest_data))

        result4 = handle_meta_list({})
        assert result4["ok"] is True
        assert discover_count == 3  # Incremented
        assert len(result4["result"]["functions"]) == 1
