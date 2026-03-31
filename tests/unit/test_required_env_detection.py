from __future__ import annotations

import subprocess

import tests.conftest as repo_conftest


def test_is_env_available_uses_detected_manager(monkeypatch):
    calls: list[list[str]] = []

    monkeypatch.setattr(
        repo_conftest,
        "detect_env_manager",
        lambda: ("micromamba", "/tmp/micromamba", "1.0"),
        raising=False,
    )

    def fake_run(cmd, capture_output, text, timeout):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(repo_conftest.subprocess, "run", fake_run)

    assert repo_conftest._is_env_available("bioimage-mcp-microsam", {}) is True
    assert calls == [
        ["/tmp/micromamba", "run", "-n", "bioimage-mcp-microsam", "python", "-c", "print('ok')"]
    ]
