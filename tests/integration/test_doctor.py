from __future__ import annotations

import json
import subprocess

import pytest

from bioimage_mcp.bootstrap.doctor import doctor


@pytest.mark.integration
def test_doctor_json_cli():
    """Runs bioimage-mcp doctor --json and validates the payload shape."""
    result = subprocess.run(
        ["bioimage-mcp", "doctor", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    # Output might contain logs before the JSON payload
    lines = result.stdout.strip().splitlines()
    assert len(lines) > 0
    payload = json.loads(lines[-1])

    assert "ready" in payload
    assert "checks" in payload
    assert "registry" in payload

    # Verify registry summary includes new fields
    registry = payload["registry"]
    assert "tool_count" in registry
    assert "function_count" in registry
    assert "engine_events" in registry

    # Verify checks include tool_environments
    check_names = [c["name"] for c in payload["checks"]]
    assert "tool_environments" in check_names


@pytest.mark.integration
def test_doctor_function_direct(monkeypatch):
    """Calls doctor() directly and validates registry + remediation fields."""
    from bioimage_mcp.bootstrap import checks
    from bioimage_mcp.bootstrap import doctor as doctor_mod

    # Mock a failure in tool_environments to verify remediation entry
    def mock_run_all_checks():
        # Get real checks first
        results = [
            checks.CheckResult(name="python", ok=True),
            checks.CheckResult(
                name="tool_environments",
                ok=False,
                required=True,
                remediation=["Run: bioimage-mcp install"],
            ),
        ]
        return results

    monkeypatch.setattr(doctor_mod, "run_all_checks", mock_run_all_checks)

    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        # doctor() returns 1 if not ready
        exit_code = doctor(json_output=True)

    assert exit_code == 1
    payload = json.loads(f.getvalue())

    assert payload["ready"] is False
    tool_env_check = next(c for c in payload["checks"] if c["name"] == "tool_environments")
    assert tool_env_check["ok"] is False
    assert "Run: bioimage-mcp install" in tool_env_check["remediation"]
