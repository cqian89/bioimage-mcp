from __future__ import annotations

import json

from bioimage_mcp.bootstrap import doctor as doctor_mod
from bioimage_mcp.bootstrap.checks import CheckResult


def test_doctor_prints_ready_when_all_checks_pass(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        doctor_mod,
        "run_checks",
        lambda: [CheckResult(name="python", ok=True, remediation=[])] * 8,
    )

    exit_code = doctor_mod.doctor(json_output=False)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "READY" in out


def test_doctor_prints_remediation_when_checks_fail(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        doctor_mod,
        "run_checks",
        lambda: [CheckResult(name="python", ok=False, remediation=["Install Python 3.13+"])]
        + [CheckResult(name="ok", ok=True, remediation=[])] * 7,
    )

    exit_code = doctor_mod.doctor(json_output=False)
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "NOT READY" in out
    assert "Install Python 3.13+" in out


def test_doctor_json_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        doctor_mod,
        "run_checks",
        lambda: [CheckResult(name="python", ok=True, remediation=[])] * 8,
    )

    exit_code = doctor_mod.doctor(json_output=True)
    out = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(out)
    assert payload["ready"] is True
    assert payload["checks"][0]["name"]
    assert payload["checks"][0]["ok"] is True
