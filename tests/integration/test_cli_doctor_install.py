from __future__ import annotations

from bioimage_mcp import cli


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
