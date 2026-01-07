import json
import subprocess
import sys
import time
from pathlib import Path

import pytest


def test_cellpose_worker_early_handshake():
    """Verify that the cellpose worker sends a ready handshake immediately."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    entrypoint_path = repo_root / "tools" / "cellpose" / "bioimage_mcp_cellpose" / "entrypoint.py"
    assert entrypoint_path.exists()

    # Start the worker in persistent mode
    env = {
        **subprocess.os.environ,
        "BIOIMAGE_MCP_SESSION_ID": "test_session",
        "BIOIMAGE_MCP_ENV_ID": "bioimage-mcp-cellpose",
        "PYTHONPATH": str(repo_root / "src") + ":" + str(repo_root / "tools" / "cellpose"),
    }

    start_time = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, str(entrypoint_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        bufsize=1,
    )

    try:
        # Read the first line of output
        line = proc.stdout.readline()
        elapsed = time.perf_counter() - start_time

        assert line, "Worker did not produce any output"
        data = json.loads(line)

        # In the NEW implementation, we expect 'ready' with status='initializing'
        assert data.get("command") == "ready"
        assert data.get("status") == "initializing"

        # Requirement: handshake within 1 second
        assert elapsed < 1.0, f"Handshake took too long: {elapsed:.3f}s"

        # If it's the two-phase handshake, it might have status='initializing'
        # For now, let's just check it's 'ready'

    finally:
        proc.terminate()
        proc.wait()


def test_cellpose_worker_import_failure_reporting():
    """Verify that the cellpose worker reports import failures gracefully."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    entrypoint_path = repo_root / "tools" / "cellpose" / "bioimage_mcp_cellpose" / "entrypoint.py"

    # We'll use a trick: set a PYTHONPATH that makes 'numpy' fail to import
    # by providing a broken numpy.py in a temp directory.
    # Actually, easier to use an environment variable that our new entrypoint will check.

    env = {
        **subprocess.os.environ,
        "BIOIMAGE_MCP_SESSION_ID": "test_session",
        "BIOIMAGE_MCP_ENV_ID": "bioimage-mcp-cellpose",
        "PYTHONPATH": str(repo_root / "src") + ":" + str(repo_root / "tools" / "cellpose"),
        "SIMULATE_IMPORT_FAILURE": "numpy",
    }

    proc = subprocess.Popen(
        [sys.executable, str(entrypoint_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        bufsize=1,
    )

    try:
        # Read lines until we find the error or it exits
        lines = []
        for _ in range(5):
            line = proc.stdout.readline()
            if not line:
                break
            lines.append(line)
            data = json.loads(line)
            if data.get("command") == "error":
                assert data.get("ok") is False
                assert data.get("error", {}).get("code") == "IMPORT_FAILED"
                return

        pytest.fail(f"Worker did not report import failure. Output: {lines}")

    finally:
        proc.terminate()
        proc.wait()
