from __future__ import annotations

import subprocess

from bioimage_mcp.bootstrap.env_manager import _get_version, detect_env_manager


def test_get_version_returns_none_on_exception(monkeypatch) -> None:
    def raise_error(*args, **kwargs):
        raise OSError("Command failed")

    monkeypatch.setattr("subprocess.run", raise_error)

    result = _get_version("/fake/path")
    assert result is None


def test_get_version_returns_first_line_of_stdout(monkeypatch) -> None:
    def mock_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="mamba 2.0.0\nextra", stderr="")

    monkeypatch.setattr("subprocess.run", mock_run)

    result = _get_version("/usr/bin/mamba")
    assert result == "mamba 2.0.0"


def test_get_version_returns_none_for_empty_output(monkeypatch) -> None:
    def mock_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", mock_run)

    result = _get_version("/usr/bin/mamba")
    assert result is None


def test_detect_env_manager_prefers_micromamba(monkeypatch) -> None:
    def mock_which(name):
        # All managers available
        return f"/usr/bin/{name}" if name in ("micromamba", "mamba", "conda") else None

    monkeypatch.setattr("shutil.which", mock_which)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.env_manager._get_version",
        lambda x: "1.0.0",
    )

    result = detect_env_manager()
    assert result is not None
    assert result[0] == "micromamba"  # First in preference order


def test_detect_env_manager_falls_back_to_conda(monkeypatch) -> None:
    def mock_which(name):
        return "/usr/bin/conda" if name == "conda" else None

    monkeypatch.setattr("shutil.which", mock_which)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.env_manager._get_version",
        lambda x: "4.12.0",
    )

    result = detect_env_manager()
    assert result is not None
    assert result[0] == "conda"


def test_detect_env_manager_returns_none_when_nothing_found(monkeypatch) -> None:
    def mock_which(name):
        return None

    monkeypatch.setattr("shutil.which", mock_which)

    result = detect_env_manager()
    assert result is None


def test_detect_env_manager_uses_mamba_if_micromamba_missing(monkeypatch) -> None:
    def mock_which(name):
        return f"/usr/bin/{name}" if name in ("mamba", "conda") else None

    monkeypatch.setattr("shutil.which", mock_which)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.env_manager._get_version",
        lambda x: "2.0.0",
    )

    result = detect_env_manager()
    assert result is not None
    assert result[0] == "mamba"
