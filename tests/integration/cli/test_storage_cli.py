from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


import os


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[3]
    env["PYTHONPATH"] = str(repo_root / "src")
    return subprocess.run(
        [sys.executable, "-m", "bioimage_mcp.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture
def config_file(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    (artifact_root / "state").mkdir()
    (artifact_root / "objects").mkdir()

    config_content = f"""
artifact_store_root: {artifact_root}
tool_manifest_roots: []
storage:
  quota_bytes: 1000
  retention_days: 7
"""
    config_path.write_text(config_content)
    return config_path


def test_cli_storage_status(config_file, monkeypatch):
    """T024: Integration test for `storage status` CLI"""
    monkeypatch.setenv("BIOIMAGE_MCP_CONFIG", str(config_file))

    result = run_cli(["--debug", "storage", "status"])
    print(result.stderr)
    assert result.returncode == 0

    assert "Storage Usage" in result.stdout
    assert "active" in result.stdout


def test_cli_storage_prune(config_file, monkeypatch):
    """T025: Integration test for `storage prune` CLI"""
    monkeypatch.setenv("BIOIMAGE_MCP_CONFIG", str(config_file))

    result = run_cli(["storage", "prune", "--dry-run"])
    assert result.returncode == 0
    assert "Prune Result" in result.stdout
    assert "DRY RUN" in result.stdout
