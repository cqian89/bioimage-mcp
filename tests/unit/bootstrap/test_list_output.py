from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.bootstrap import list as list_mod


@pytest.fixture
def mock_db(tmp_path, monkeypatch):
    db_path = tmp_path / "registry.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE tools (tool_id TEXT PRIMARY KEY, env_id TEXT, description TEXT, installed INTEGER)"
    )
    conn.execute(
        "CREATE TABLE functions (fn_id TEXT PRIMARY KEY, tool_id TEXT, name TEXT, description TEXT)"
    )
    conn.commit()

    # Mock load_config to return tmp_path as artifact_store_root
    mock_config = MagicMock()
    mock_config.artifact_store_root = tmp_path
    monkeypatch.setattr("bioimage_mcp.bootstrap.list.load_config", lambda: mock_config)

    return conn, db_path


def test_list_tools_table_output(mock_db, monkeypatch, capsys) -> None:
    conn, _ = mock_db
    conn.execute(
        "INSERT INTO tools VALUES (?, ?, ?, ?)",
        ("cellpose", "bioimage-mcp-cellpose", json.dumps({"name": "Cellpose"}), 1),
    )
    conn.execute(
        "INSERT INTO functions VALUES (?, ?, ?, ?)",
        ("cellpose.segment", "cellpose", "Segment", "Segment images"),
    )
    conn.commit()

    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: {"bioimage-mcp-cellpose"})

    exit_code = list_mod.list_tools(json_output=False)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Tool" in out
    assert "cellpose" in out
    assert "✓ installed" in out
    assert "1" in out  # function count


def test_list_tools_json_output(mock_db, monkeypatch, capsys) -> None:
    conn, _ = mock_db
    conn.execute(
        "INSERT INTO tools VALUES (?, ?, ?, ?)",
        ("cellpose", "bioimage-mcp-cellpose", json.dumps({"name": "Cellpose"}), 1),
    )
    conn.commit()

    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: set())  # Missing env

    exit_code = list_mod.list_tools(json_output=True)
    out = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(out)
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["id"] == "cellpose"
    assert payload["tools"][0]["status"] == "partial"


def test_list_tools_empty(mock_db, monkeypatch, capsys) -> None:
    exit_code = list_mod.list_tools(json_output=False)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "No tools found in registry." in out


def test_list_tools_mixed_status(mock_db, monkeypatch, capsys) -> None:
    conn, _ = mock_db
    # 1. Installed
    conn.execute("INSERT INTO tools VALUES (?, ?, ?, ?)", ("t1", "e1", "{}", 1))
    # 2. Partial (env missing)
    conn.execute("INSERT INTO tools VALUES (?, ?, ?, ?)", ("t2", "e2", "{}", 1))
    # 3. Unavailable (not installed in DB)
    conn.execute("INSERT INTO tools VALUES (?, ?, ?, ?)", ("t3", "e3", "{}", 0))
    conn.commit()

    monkeypatch.setattr(list_mod, "detect_env_manager", lambda: ("micromamba", "exe", "1.0"))
    monkeypatch.setattr(list_mod, "_get_installed_envs", lambda _: {"e1"})

    list_mod.list_tools(json_output=False)
    out = capsys.readouterr().out

    assert "t1" in out and "✓ installed" in out
    assert "t2" in out and "⚠ partial" in out
    assert "t3" in out and "✗ unavailable" in out
