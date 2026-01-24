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


def test_doctor_ready_with_warnings(monkeypatch, capsys) -> None:
    # Scenario: Required checks pass, but an optional check (conda_lock) fails
    monkeypatch.setattr(
        doctor_mod,
        "run_checks",
        lambda: [
            CheckResult(name="python", ok=True),
            CheckResult(
                name="conda_lock",
                ok=False,
                required=False,
                remediation=["Install conda-lock"],
            ),
        ],
    )

    exit_code = doctor_mod.doctor(json_output=False)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "READY" in out
    assert "WARNINGS" in out
    assert "conda_lock" in out
    assert "Install conda-lock" in out


def test_doctor_json_ready_with_optional_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        doctor_mod,
        "run_checks",
        lambda: [
            CheckResult(name="python", ok=True),
            CheckResult(
                name="conda_lock",
                ok=False,
                required=False,
                remediation=["Install conda-lock"],
            ),
        ],
    )

    exit_code = doctor_mod.doctor(json_output=True)
    out = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(out)
    assert payload["ready"] is True
    # Find the conda_lock check
    conda_lock_check = next(c for c in payload["checks"] if c["name"] == "conda_lock")
    assert conda_lock_check["ok"] is False
    assert conda_lock_check["required"] is False
