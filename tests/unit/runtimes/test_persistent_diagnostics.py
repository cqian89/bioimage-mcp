import pytest
import sys
import time
from pathlib import Path
from bioimage_mcp.runtimes.persistent import WorkerProcess


def test_worker_crash_diagnostics(tmp_path):
    """Verify that stderr is included in the error message when a worker crashes."""
    # Create a failing entrypoint script
    script = tmp_path / "fail_entrypoint.py"
    script.write_text("""
import sys
import time
print("This is some stderr output", file=sys.stderr)
print("More stderr output", file=sys.stderr)
sys.exit(1)
""")

    with pytest.raises(RuntimeError) as excinfo:
        WorkerProcess(session_id="test_crash", env_id="", entrypoint=str(script))

    error_msg = str(excinfo.value)
    assert "Worker closed stdout without ready handshake" in error_msg
    # These assertions will fail until the implementation is updated
    assert "Stderr output:" in error_msg
    assert "This is some stderr output" in error_msg
    assert "More stderr output" in error_msg


def test_worker_timeout_diagnostics(tmp_path, monkeypatch):
    """Verify that captured stderr is included in the error message when a handshake times out."""
    # Create a script that hangs but writes to stderr
    script = tmp_path / "hang_entrypoint.py"
    script.write_text("""
import sys
import time
print("Worker starting up...", file=sys.stderr)
sys.stderr.flush()
time.sleep(10)
""")

    # Use a very short timeout for testing
    monkeypatch.setattr(WorkerProcess, "HANDSHAKE_TIMEOUT", 0.5)

    with pytest.raises(RuntimeError) as excinfo:
        WorkerProcess(session_id="test_timeout", env_id="", entrypoint=str(script))

    error_msg = str(excinfo.value)
    assert "failed to send ready handshake within 0.5 seconds" in error_msg
    assert "Stderr output:" in error_msg
    assert "Worker starting up..." in error_msg


if __name__ == "__main__":
    # Manually run if needed
    pass
