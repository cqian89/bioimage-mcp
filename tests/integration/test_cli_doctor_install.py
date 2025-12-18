from __future__ import annotations

from pathlib import Path

import yaml

from bioimage_mcp import cli


def test_configure_creates_config_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    from bioimage_mcp.bootstrap.configure import configure

    result = configure()
    assert result == 0

    config_path = tmp_path / ".bioimage-mcp" / "config.yaml"
    assert config_path.exists()

    with open(config_path) as f:
        data = yaml.safe_load(f)
    assert "artifact_store_root" in data
    assert "tool_manifest_roots" in data


def test_configure_returns_early_if_config_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    # Create config directory and file first
    config_dir = tmp_path / ".bioimage-mcp"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("existing: true")

    from bioimage_mcp.bootstrap.configure import configure

    result = configure()
    assert result == 0

    # Verify original content was not overwritten
    with open(config_dir / "config.yaml") as f:
        data = yaml.safe_load(f)
    assert data == {"existing": True}


def test_cli_wires_doctor(monkeypatch) -> None:
    called = {"doctor": False}

    def fake_doctor(*, json_output: bool) -> int:
        called["doctor"] = True
        assert json_output is True
        return 0

    monkeypatch.setattr("bioimage_mcp.bootstrap.doctor.doctor", fake_doctor)

    assert cli.main(["doctor", "--json"]) == 0
    assert called["doctor"] is True


def test_cli_wires_install(monkeypatch) -> None:
    called = {"install": False}

    def fake_install(*, profile: str) -> int:
        called["install"] = True
        assert profile == "cpu"
        return 0

    monkeypatch.setattr("bioimage_mcp.bootstrap.install.install", fake_install)

    assert cli.main(["install", "--profile", "cpu"]) == 0
    assert called["install"] is True
