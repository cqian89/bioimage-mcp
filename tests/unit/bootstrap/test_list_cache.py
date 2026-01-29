from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.bootstrap import list as list_mod


@pytest.fixture
def mock_setup(tmp_path, monkeypatch):
    # Setup sandbox home
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create a minimal manifest
    manifest_root = tmp_path / "tools"
    manifest_root.mkdir()
    tool_root = manifest_root / "test-tool"
    tool_root.mkdir()

    manifest_file = tool_root / "manifest.yaml"
    manifest_file.write_text(
        "manifest_version: '1.0'\ntool_id: test-tool\nenv_id: bioimage-mcp-test_env\nfunctions: []\ntool_version: 1.0.0"
    )

    # Mock load_config
    mock_config = MagicMock()
    mock_config.tool_manifest_roots = [manifest_root]
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)

    # Mock detect_env_manager
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "micromamba_exe"))

    return manifest_file


def test_list_tools_cache_hit_logic(mock_setup, monkeypatch, capsys):
    manifest_file = mock_setup

    # Track calls to _get_installed_envs and load_manifests
    # Note: we need to patch them where they are USED in list_tools

    get_envs_calls = []

    def mock_get_envs(exe):
        get_envs_calls.append(exe)
        return {"test_env"}

    monkeypatch.setattr(list_mod, "_get_installed_envs", mock_get_envs)

    original_load = list_mod.load_manifests
    load_calls = []

    def mock_load(roots):
        load_calls.append(roots)
        # Return a real ToolManifest object so it can be sorted
        from bioimage_mcp.registry.manifest_schema import ToolManifest

        m = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="1.0.0",
            env_id="bioimage-mcp-test_env",
            entrypoint="main.py",
            name="Test",
            description="Test",
            functions=[],
            manifest_path=manifest_file,
            manifest_checksum="abc",
        )
        return [m], []

    monkeypatch.setattr(list_mod, "load_manifests", mock_load)

    # 1. First call (cold)
    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(get_envs_calls) == 1
    assert len(load_calls) == 1

    # Verify cache files created
    cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "cli"
    assert (cache_dir / "installed_envs.json").exists()
    assert (cache_dir / "list_tools.json").exists()

    capsys.readouterr()  # Clear buffer

    # 2. Second call (warm)
    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(get_envs_calls) == 1  # Should still be 1
    assert len(load_calls) == 1  # Should still be 1

    # 3. Invalidation: change manifest
    # Update manifest file to trigger mtime change
    import time

    time.sleep(0.1)  # Ensure mtime changes
    manifest_file.write_text(
        "manifest_version: '1.0'\ntool_id: test-tool\nenv_id: bioimage-mcp-test_env\nfunctions: []\ntool_version: 1.0.1"
    )

    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(get_envs_calls) == 1  # Envs still cached
    assert len(load_calls) == 2  # Manifests reloaded

    # 4. Invalidation: change envs (by clearing envs cache)
    (cache_dir / "installed_envs.json").unlink()

    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(get_envs_calls) == 2  # Envs re-queried
    assert len(load_calls) == 3  # Tools re-queried because envs_hash changed/was missing


def test_list_tools_disable_cache_env_var(mock_setup, monkeypatch):
    monkeypatch.setenv("BIOIMAGE_MCP_DISABLE_LIST_CACHE", "1")
    monkeypatch.setattr(Path, "home", lambda: mock_setup.parent.parent.parent)

    get_envs_calls = []

    def mock_get_envs(exe):
        get_envs_calls.append(exe)
        return {"test_env"}

    monkeypatch.setattr(list_mod, "_get_installed_envs", mock_get_envs)

    load_calls = []

    def mock_load(roots):
        load_calls.append(roots)
        return [], []

    monkeypatch.setattr(list_mod, "load_manifests", mock_load)

    list_mod.list_tools(json_output=True)
    assert len(get_envs_calls) == 1
    assert len(load_calls) == 1

    list_mod.list_tools(json_output=True)
    assert len(get_envs_calls) == 2
    assert len(load_calls) == 2


def test_list_tools_dynamic_cache_fallback(mock_setup, monkeypatch):
    manifest_file = mock_setup

    # Track calls to load_manifests
    load_calls = []

    def mock_load(roots):
        load_calls.append(roots)
        from bioimage_mcp.registry.manifest_schema import Function, ToolManifest

        m = ToolManifest(
            manifest_version="1.0",
            tool_id="test-tool",
            tool_version="1.0.0",
            env_id="bioimage-mcp-test_env",
            entrypoint="main.py",
            name="Test",
            description="Test",
            functions=[
                Function(
                    fn_id="test-tool.test_fn",
                    tool_id="test-tool",
                    name="test_fn",
                    description="test",
                    introspection_source="dynamic_discovery",
                )
            ],
            manifest_path=manifest_file,
            manifest_checksum="abc",
        )
        return [m], []

    monkeypatch.setattr(list_mod, "load_manifests", mock_load)
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda exe: {"bioimage-mcp-test_env"})

    # 1. Cold path: populates list_tools.json
    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(load_calls) == 1

    # 2. Warm path, but dynamic cache missing (never created yet)
    # The fix should detect missing introspection_cache.json and fall through
    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(load_calls) == 2

    # 3. Create dynamic cache
    dynamic_cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / "test-tool"
    dynamic_cache_dir.mkdir(parents=True, exist_ok=True)
    (dynamic_cache_dir / "introspection_cache.json").write_text("{}")

    # 4. Warm path, dynamic cache exists -> Cache HIT
    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(load_calls) == 2  # Still 2

    # 5. Delete dynamic cache -> Cache MISS (repair/regeneration path)
    (dynamic_cache_dir / "introspection_cache.json").unlink()
    exit_code = list_mod.list_tools(json_output=True)
    assert exit_code == 0
    assert len(load_calls) == 3
