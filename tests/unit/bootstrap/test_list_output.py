from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from bioimage_mcp.bootstrap import list as list_mod


@pytest.fixture
def mock_registry(tmp_path, monkeypatch):
    # Setup sandbox home
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create a minimal manifest
    manifest_root = tmp_path / "tools"
    manifest_root.mkdir()
    tool_root = manifest_root / "test-tool"
    tool_root.mkdir()

    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "test-tool",
        "tool_version": "1.2.3",
        "env_id": "bioimage-mcp-test",
        "entrypoint": "main.py",
        "name": "Test Tool",
        "description": "A test tool",
        "functions": [
            {
                "id": "test.func",
                "tool_id": "test-tool",
                "name": "Test Func",
                "description": "Test description",
                "introspection_source": "python_api",
                "inputs": [
                    {
                        "name": "image",
                        "artifact_type": "BioImageRef",
                        "description": "Input image",
                    }
                ],
                "outputs": [
                    {
                        "name": "labels",
                        "artifact_type": "LabelImageRef",
                        "description": "Output labels",
                    }
                ],
                "params_schema": {"type": "object", "properties": {}},
            }
        ],
    }

    manifest_file = tool_root / "manifest.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(manifest_data, f)

    # Mock load_config to return tmp_path as tool_manifest_roots
    mock_config = MagicMock()
    mock_config.tool_manifest_roots = [manifest_root]
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)

    return manifest_root


def test_list_tools_table_output(mock_registry, monkeypatch, capsys) -> None:
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: {"bioimage-mcp-test"})

    exit_code = list_mod.list_tools(json_output=False)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Tool" in out
    assert "Version" in out
    assert "Status" in out
    assert "Functions" in out
    assert "test-tool" in out
    assert "1.2.3" in out
    assert "installed" in out
    assert "1" in out  # function count
    assert "└──" not in out


def test_list_tools_json_output(mock_registry, monkeypatch, capsys) -> None:
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: set())  # Missing env

    exit_code = list_mod.list_tools(json_output=True)
    out = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(out)
    assert len(payload["tools"]) == 1
    tool = payload["tools"][0]
    assert tool["id"] == "test-tool"
    assert tool["tool_version"] == "1.2.3"
    assert tool["status"] == "partial"
    assert "packages" in tool
    assert tool["packages"] == []


def test_list_tools_empty(monkeypatch, capsys, tmp_path) -> None:
    # Empty manifest root
    manifest_root = tmp_path / "empty"
    manifest_root.mkdir()

    mock_config = MagicMock()
    mock_config.tool_manifest_roots = [manifest_root]
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)

    exit_code = list_mod.list_tools(json_output=False)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "No tools found in registry." in out


def test_list_tools_lockfile_version(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # 1. Create envs/bioimage-mcp-cellpose.lock.yml
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    lock_data = {
        "version": 1,
        "package": [{"name": "cellpose", "version": "3.1.0", "platform": "linux-64"}],
    }
    lock_file = envs_dir / "bioimage-mcp-cellpose.lock.yml"
    with open(lock_file, "w") as f:
        yaml.dump(lock_data, f)

    # 2. Create manifest for cellpose
    manifest_root = tmp_path / "tools"
    manifest_root.mkdir()
    tool_root = manifest_root / "cellpose"
    tool_root.mkdir()
    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "tools.cellpose",
        "tool_version": "0.1.0",
        "env_id": "bioimage-mcp-cellpose",
        "entrypoint": "main.py",
        "name": "Cellpose",
        "description": "Cellpose tool",
        "functions": [
            {
                "id": "cellpose.models.run",
                "tool_id": "tools.cellpose",
                "name": "Run Cellpose",
                "description": "Run cellpose",
                "params_schema": {"type": "object", "properties": {}},
            }
        ],
    }
    with open(tool_root / "manifest.yaml", "w") as f:
        yaml.dump(manifest_data, f)

    # 3. Setup mocks
    mock_config = MagicMock()
    mock_config.tool_manifest_roots = [manifest_root]
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: {"bioimage-mcp-cellpose"})

    # Force platform for test reliability
    monkeypatch.setattr(list_mod, "_get_conda_platform", lambda: "linux-64")

    # 4. Run list_tools
    exit_code = list_mod.list_tools(json_output=True)
    out = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(out)
    tool = payload["tools"][0]
    assert tool["id"] == "cellpose"
    assert tool["library_version"] == "3.1.0"
    assert tool["packages"] == []


def test_list_tools_cache_invalidation_on_lockfile_change(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # 1. Create initial lockfile
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    lock_file = envs_dir / "bioimage-mcp-base.lock.yml"
    lock_data = {"version": 1, "package": [{"name": "scipy", "version": "1.14.1"}]}
    with open(lock_file, "w") as f:
        yaml.dump(lock_data, f)

    # 2. Create manifest for base
    manifest_root = tmp_path / "tools"
    manifest_root.mkdir()
    tool_root = manifest_root / "base"
    tool_root.mkdir()
    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "tools.base",
        "tool_version": "0.2.0",
        "env_id": "bioimage-mcp-base",
        "entrypoint": "main.py",
        "name": "Base",
        "description": "Base tools",
        "functions": [
            {
                "id": "base.scipy.test",
                "tool_id": "tools.base",
                "name": "test",
                "description": "test",
                "params_schema": {"type": "object", "properties": {}},
            }
        ],
    }
    with open(tool_root / "manifest.yaml", "w") as f:
        yaml.dump(manifest_data, f)

    # 3. Setup mocks
    mock_config = MagicMock()
    mock_config.tool_manifest_roots = [manifest_root]
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: {"bioimage-mcp-base"})

    # 4. First run - populates cache
    list_mod.list_tools(json_output=True)
    out1 = capsys.readouterr().out
    payload1 = json.loads(out1)
    packages1 = payload1["tools"][0]["packages"]
    assert packages1[0]["library_version"] == "1.14.1"

    # 5. Update lockfile version
    lock_data["package"][0]["version"] = "1.15.0"
    with open(lock_file, "w") as f:
        yaml.dump(lock_data, f)

    # 6. Second run - should show new version
    list_mod.list_tools(json_output=True)
    out2 = capsys.readouterr().out
    payload2 = json.loads(out2)
    packages2 = payload2["tools"][0]["packages"]
    assert packages2[0]["library_version"] == "1.15.0"


def test_list_tools_non_namespaced_ids(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # 1. Create manifest with non-namespaced function IDs
    manifest_root = tmp_path / "tools"
    manifest_root.mkdir()
    tool_root = manifest_root / "test-tool"
    tool_root.mkdir()
    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "test-tool",
        "tool_version": "1.2.3",
        "env_id": "bioimage-mcp-test",
        "entrypoint": "main.py",
        "name": "Test Tool",
        "description": "A test tool",
        "functions": [
            {
                "id": "alpha",  # No '.'
                "tool_id": "test-tool",
                "name": "Alpha",
                "description": "Alpha description",
                "params_schema": {"type": "object", "properties": {}},
            },
            {
                "id": "beta",  # No '.'
                "tool_id": "test-tool",
                "name": "Beta",
                "description": "Beta description",
                "params_schema": {"type": "object", "properties": {}},
            },
            {
                "id": "test-tool.gamma",  # With tool prefix but no sub-package
                "tool_id": "test-tool",
                "name": "Gamma",
                "description": "Gamma description",
                "params_schema": {"type": "object", "properties": {}},
            },
        ],
    }
    with open(tool_root / "manifest.yaml", "w") as f:
        yaml.dump(manifest_data, f)

    # 2. Setup mocks
    mock_config = MagicMock()
    mock_config.tool_manifest_roots = [manifest_root]
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: {"bioimage-mcp-test"})

    # 3. Run list_tools (JSON)
    exit_code = list_mod.list_tools(json_output=True)
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    tool = payload["tools"][0]

    # Non-base tools should not emit package rows
    assert tool["packages"] == []

    # 4. Run list_tools (Table)
    exit_code = list_mod.list_tools(json_output=False)
    out = capsys.readouterr().out
    assert exit_code == 0
    # Should not render package rows for non-base tools
    assert "└──" not in out
