from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from bioimage_mcp.bootstrap import list as list_mod


@pytest.fixture
def mock_registry_two_tools(tmp_path, monkeypatch):
    # Setup sandbox home
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create two minimal manifests
    manifest_root = tmp_path / "tools"
    manifest_root.mkdir()

    tools = {
        "tools.base": "0.1.0",
        "tools.trackpy": "0.2.0",
    }

    for tool_id, version in tools.items():
        tool_root = manifest_root / tool_id
        tool_root.mkdir()
        manifest_data = {
            "manifest_version": "1.0",
            "tool_id": tool_id,
            "tool_version": version,
            "env_id": f"bioimage-mcp-{tool_id}",
            "entrypoint": "main.py",
            "name": f"Name {tool_id}",
            "description": f"Description {tool_id}",
            "functions": [],
        }
        manifest_file = tool_root / "manifest.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest_data, f)

    # Mock load_config to return tmp_path as tool_manifest_roots
    mock_config = MagicMock()
    mock_config.tool_manifest_roots = [manifest_root]
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)

    # Clear manifest cache to ensure we load the mock ones
    monkeypatch.setattr("bioimage_mcp.registry.loader._MANIFEST_CACHE", {})

    # Clear CLI caches to avoid interference
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.get_cli_cache_dir", lambda: tmp_path / "cache")

    return manifest_root


def test_list_tools_filtering_exact(mock_registry_two_tools, monkeypatch, capsys):
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: None)

    # 1. Exact match
    exit_code = list_mod.list_tools(json_output=True, tool="tools.trackpy")
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["id"] == "trackpy"


def test_list_tools_filtering_short(mock_registry_two_tools, monkeypatch, capsys):
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: None)

    # 2. Short name match
    exit_code = list_mod.list_tools(json_output=True, tool="base")
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["id"] == "base"


def test_list_tools_filtering_no_match(mock_registry_two_tools, monkeypatch, capsys):
    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: None)

    # 3. No match
    exit_code = list_mod.list_tools(json_output=True, tool="nonexistent")
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    assert len(payload["tools"]) == 0
