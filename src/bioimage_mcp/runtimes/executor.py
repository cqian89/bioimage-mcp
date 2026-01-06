from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from bioimage_mcp.bootstrap.env_manager import detect_env_manager


def _build_command(entrypoint: str, *, env_id: str | None) -> list[str]:
    entry_path = Path(entrypoint)

    manager = detect_env_manager() if env_id else None
    if manager:
        assert env_id is not None
        _name, exe, _version = manager
        if entry_path.exists() and entry_path.suffix == ".py":
            return [exe, "run", "-n", env_id, "python", str(entry_path)]
        return [exe, "run", "-n", env_id, "python", "-m", entrypoint]

    if entry_path.exists() and entry_path.suffix == ".py":
        return [sys.executable, str(entry_path)]
    return [sys.executable, "-m", entrypoint]


def execute_tool(
    *,
    entrypoint: str,
    request: dict,
    env_id: str | None,
    timeout_seconds: int | None = None,
) -> tuple[dict, str, int]:
    cmd = _build_command(entrypoint, env_id=env_id)

    env = os.environ.copy()
    allowlist_read = request.get("fs_allowlist_read")
    if allowlist_read is not None:
        env["BIOIMAGE_MCP_FS_ALLOWLIST_READ"] = json.dumps(allowlist_read)

    allowlist_write = request.get("fs_allowlist_write")
    if allowlist_write is not None:
        env["BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"] = json.dumps(allowlist_write)

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    try:
        stdout, stderr = proc.communicate(input=json.dumps(request), timeout=timeout_seconds)
        exit_code = int(proc.returncode or 0)
        timed_out = False
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        exit_code = 124
        timed_out = True

    stdout = (stdout or "").strip()
    stderr = (stderr or "").strip()

    log_parts: list[str] = []
    if timed_out:
        log_parts.append(f"TIMEOUT after {timeout_seconds}s")
    log_parts.extend([t for t in [stdout, stderr] if t])
    log_text = "\n".join(log_parts)

    if timed_out:
        return (
            {
                "ok": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": f"Tool execution exceeded timeout_seconds={timeout_seconds}",
                },
            },
            log_text,
            exit_code,
        )

    try:
        response = (
            json.loads(stdout) if stdout else {"ok": False, "error": {"message": "no output"}}
        )
    except json.JSONDecodeError:
        response = {"ok": False, "error": {"message": "invalid json"}}

    return response, log_text, exit_code
