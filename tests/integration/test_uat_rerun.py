"""UAT Regression tests for stability and recovery."""


import psutil
import pytest


@pytest.mark.integration
@pytest.mark.anyio
async def test_worker_crash_recovery_no_ordinal_mismatch(mcp_test_client):
    """Verify server recovers from worker crash without ordinal mismatch.

    Steps:
    1. Run a valid command to spawn the worker.
    2. Identify and KILL the worker process (Deterministic Failure).
    3. Run another command.
    4. Assert success (implies successful restart + handshake).
    """
    # 1. Prime - ensure worker is running
    res1 = mcp_test_client.call_tool("meta.describe", {}, {"target_fn": "base.io.bioimage.export"})
    assert res1["status"] == "success"

    # 2. Kill worker deterministically
    current_proc = psutil.Process()
    children = current_proc.children(recursive=True)
    worker_proc = None
    for child in children:
        try:
            cmdline = " ".join(child.cmdline())
            if "python" in child.name().lower() and (
                "entrypoint.py" in cmdline or "bioimage_mcp_base.entrypoint" in cmdline
            ):
                worker_proc = child
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    assert worker_proc is not None, "Could not find worker process to kill"
    worker_proc.kill()
    worker_proc.wait()

    # 3. Next request must succeed and NOT have ordinal error
    res2 = mcp_test_client.call_tool("meta.describe", {}, {"target_fn": "base.io.bioimage.export"})
    assert res2["status"] == "success"


@pytest.mark.integration
@pytest.mark.anyio
async def test_sequential_requests_stability(mcp_test_client):
    """Verify stability over multiple sequential requests."""
    for i in range(2):
        res = mcp_test_client.call_tool(
            "meta.describe", {}, {"target_fn": "base.io.bioimage.export"}
        )
        assert res["status"] == "success"
