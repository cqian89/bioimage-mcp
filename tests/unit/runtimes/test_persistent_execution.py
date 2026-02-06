import pytest
import json
import time
import threading
from bioimage_mcp.runtimes.persistent import WorkerProcess


def test_execute_sends_keepalives(tmp_path, monkeypatch):
    """Verify that worker.execute sends progress notifications during long-running calls (FR-017)."""
    # Create a script that hangs for a bit before responding
    script = tmp_path / "hang_then_respond.py"
    script.write_text("""
import sys
import json
import time

# Send ready handshake
print(json.dumps({"command": "ready", "version": "1.0.0"}), flush=True)

for line in sys.stdin:
    try:
        req = json.loads(line)
        if req.get("command") == "execute":
            # Hang for 1 second
            time.sleep(1.0)
            
            # Return success
            response = {
                "command": "execute_result",
                "ok": True,
                "ordinal": req.get("ordinal"),
                "outputs": {"result": "ok"}
            }
            print(json.dumps(response), flush=True)
        elif req.get("command") == "shutdown":
            ack = {"command": "shutdown_ack", "ok": True, "ordinal": req.get("ordinal")}
            print(json.dumps(ack), flush=True)
            break
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
""")

    # Patch KEEPALIVE_INTERVAL to be very short for the test
    monkeypatch.setattr(WorkerProcess, "KEEPALIVE_INTERVAL", 0.3)

    worker = WorkerProcess(session_id="test_keepalive", env_id="", entrypoint=str(script))

    progress_messages = []

    def progress_callback(msg):
        progress_messages.append(msg)

    try:
        # execute should take ~1s, so it should send ~3 keepalives (at 0.3s, 0.6s, 0.9s)
        response = worker.execute(
            {"id": "test_fn", "inputs": {}}, progress_callback=progress_callback
        )

        assert response["ok"] is True
        assert len(progress_messages) >= 2  # At least 2-3 notifications should be sent
        assert "Interactive tool 'test_fn' is active" in progress_messages[0]
    finally:
        worker.shutdown(graceful=False)


def test_execute_timeout_still_works(tmp_path):
    """Verify that timeout still works even with keepalive logic present."""
    script = tmp_path / "hang_forever.py"
    script.write_text("""
import sys
import json
import time
print(json.dumps({"command": "ready", "version": "1.0.0"}), flush=True)
for line in sys.stdin:
    time.sleep(10)
""")

    worker = WorkerProcess(session_id="test_timeout_still_works", env_id="", entrypoint=str(script))

    try:
        # Use a short timeout
        with pytest.raises(TimeoutError):
            worker.execute({"id": "test_fn"}, timeout_seconds=0.5)
    finally:
        worker.shutdown(graceful=False)
