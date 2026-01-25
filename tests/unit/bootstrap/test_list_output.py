from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import yaml

from bioimage_mcp.bootstrap import list as list_mod


@pytest.fixture
def mock_registry(tmp_path, monkeypatch):
    # Create a minimal manifest
    manifest_root = tmp_path / "tools"
    manifest_root.mkdir()

    manifest_data = {
        "manifest_version": "1.0",
        "tool_id": "test-tool",
        "tool_version": "1.2.3",
        "env_id": "bioimage-mcp-test",
        "entrypoint": "main.py",
        "functions": [
            {
                "fn_id": "test.func",
                "tool_id": "test-tool",
                "name": "Test Func",
                "description": "Test description",
                "introspection_source": "python_api",
            }
        ],
    }

    manifest_file = manifest_root / "test-tool.yaml"
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
    assert "Introspection" in out
    assert "test-tool" in out
    assert "1.2.3" in out
    assert "✓ installed" in out
    assert "1" in out  # function count
    assert "python_api" in out


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
    assert "python_api" in tool["introspection_source"]


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
