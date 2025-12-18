from __future__ import annotations

import time
from pathlib import Path

from bioimage_mcp.runtimes.executor import execute_tool


def test_execute_tool_timeout_returns_error(tmp_path: Path) -> None:
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(
        "import json,sys,time\n"
        "json.loads(sys.stdin.read() or '{}')\n"
        "time.sleep(5)\n"
        "print(json.dumps({'ok': True}))\n"
    )

    start = time.perf_counter()
    response, log_text, exit_code = execute_tool(
        entrypoint=str(sleeper),
        request={"hello": "world"},
        env_id=None,
        timeout_seconds=1,
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 3
    assert response["ok"] is False
    assert response["error"]["code"] == "TIMEOUT"
    assert exit_code == 124
    assert "TIMEOUT" in log_text
