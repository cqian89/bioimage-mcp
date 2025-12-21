from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_install_rejects_invalid_profile() -> None:
    """Test that install raises ValueError for invalid profile."""
    from bioimage_mcp.bootstrap.install import install

    with pytest.raises(ValueError, match="profile must be cpu or gpu"):
        install(profile="invalid")


def test_install_raises_when_no_env_manager(monkeypatch) -> None:
    """Test that install raises RuntimeError when no env manager found."""
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: None,
    )

    from bioimage_mcp.bootstrap.install import install

    with pytest.raises(RuntimeError, match="No micromamba/conda/mamba found"):
        install(profile="cpu")


def test_install_raises_when_env_file_missing(tmp_path: Path, monkeypatch) -> None:
    """Test that install raises FileNotFoundError when env file is missing."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("mamba", "/usr/bin/mamba", "2.0"),
    )

    from bioimage_mcp.bootstrap.install import install

    with pytest.raises(FileNotFoundError, match="Missing env spec"):
        install(profile="cpu")


def test_install_calls_env_manager_with_correct_args(tmp_path: Path, monkeypatch) -> None:
    """Test that install calls the environment manager with correct arguments."""
    # Create the env files
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    base_env = envs_dir / "bioimage-mcp-base.yaml"
    base_env.write_text("name: bioimage-mcp-base\n")
    cellpose_env = envs_dir / "bioimage-mcp-cellpose.yaml"
    cellpose_env.write_text("name: bioimage-mcp-cellpose\n")

    monkeypatch.chdir(tmp_path)

    called_commands = []

    def mock_run(cmd, **kwargs):
        called_commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("mamba", "/usr/bin/mamba", "2.0"),
    )

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="cpu")

    assert result == 0
    assert len(called_commands) == 2
    for cmd in called_commands:
        assert cmd[0] == "/usr/bin/mamba"
        assert "env" in cmd
        assert "update" in cmd
        assert "--prune" in cmd
    assert any("bioimage-mcp-base" in cmd for cmd in called_commands)
    assert any("bioimage-mcp-cellpose" in cmd for cmd in called_commands)


def test_install_calls_micromamba_without_prune(tmp_path: Path, monkeypatch) -> None:
    """Test that install calls micromamba without the --prune flag."""
    # Create the env files
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    base_env = envs_dir / "bioimage-mcp-base.yaml"
    base_env.write_text("name: bioimage-mcp-base\n")
    cellpose_env = envs_dir / "bioimage-mcp-cellpose.yaml"
    cellpose_env.write_text("name: bioimage-mcp-cellpose\n")

    monkeypatch.chdir(tmp_path)

    called_commands = []

    def mock_run(cmd, **kwargs):
        called_commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager",
        lambda: ("micromamba", "/usr/bin/micromamba", "1.5.0"),
    )

    from bioimage_mcp.bootstrap.install import install

    result = install(profile="gpu")

    assert result == 0
    assert len(called_commands) == 4
    for cmd in called_commands:
        assert cmd[0] == "/usr/bin/micromamba"
        assert "--prune" not in cmd
    assert any("bioimage-mcp-base" in cmd for cmd in called_commands)
    assert any("bioimage-mcp-cellpose" in cmd for cmd in called_commands)
    assert any("remove" in cmd and "cpuonly" in cmd for cmd in called_commands)
    assert any("install" in cmd and "pytorch-cuda=11.8" in cmd for cmd in called_commands)
