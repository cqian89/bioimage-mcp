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
    called = {"install": None}

    def fake_install(
        *, tools: list[str] | None = None, profile: str | None = None, force: bool = False
    ) -> int:
        called["install"] = (tools, profile, force)
        return 0

    monkeypatch.setattr("bioimage_mcp.bootstrap.install.install", fake_install)

    # Test profile
    assert cli.main(["install", "--profile", "gpu"]) == 0
    assert called["install"] == (None, "gpu", False)

    # Test tools
    assert cli.main(["install", "cellpose", "tttrlib"]) == 0
    assert called["install"] == (["cellpose", "tttrlib"], None, False)

    # Test force
    assert cli.main(["install", "--force"]) == 0
    assert called["install"] == (None, None, True)

    # Test mutual exclusivity
    assert cli.main(["install", "microsam", "--profile", "cpu"]) == 0
    assert called["install"] == (["microsam"], "cpu", False)

    assert cli.main(["install", "cellpose", "--profile", "cpu"]) == 1


def test_discover_available_tools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    (envs_dir / "bioimage-mcp-base.yaml").write_text("name: base")
    (envs_dir / "bioimage-mcp-cellpose.yaml").write_text("name: cellpose")
    (envs_dir / "not-a-tool.yaml").write_text("name: not-a-tool")

    from bioimage_mcp.bootstrap.install import discover_available_tools

    tools = discover_available_tools()

    assert "base" in tools
    assert "cellpose" in tools
    assert "not-a-tool" not in tools
    assert tools["base"] == envs_dir / "bioimage-mcp-base.yaml"


def test_install_logic_skips_existing(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    envs_dir = tmp_path / "envs"
    envs_dir.mkdir()
    (envs_dir / "bioimage-mcp-base.yaml").write_text("name: base")

    # Mock env manager
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager", lambda: ("conda", "conda", "1.0")
    )

    # Mock _env_exists to return True
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._env_exists", lambda exe, name: True)

    called_install = []

    def fake_install_env(exe, manager, name, file):
        called_install.append(name)
        return True

    monkeypatch.setattr("bioimage_mcp.bootstrap.install._install_env", fake_install_env)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._install_pip_deps", lambda *args: True)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install._ensure_tool_manifest_roots", lambda: None)
    monkeypatch.setattr("bioimage_mcp.bootstrap.install.shutil.which", lambda *_: None)

    from bioimage_mcp.bootstrap.install import install

    # Install without force should update existing env
    result = install(profile="minimal")
    assert result == 0
    captured = capsys.readouterr()
    assert "base already installed; updating" in captured.out
    assert "bioimage-mcp-base" in called_install

    # Install with force
    result = install(profile="minimal", force=True)
    assert result == 0
    assert "bioimage-mcp-base" in called_install
