"""Tests for worker failure handling."""

from unittest.mock import MagicMock, patch

import pytest

from bioimage_mcp.runtimes.persistent import WorkerProcess, WorkerState


def test_worker_kills_process_on_read_error():
    """Verify worker process is killed when reading response fails."""
    # Mock process
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # Running

    # We need to mock Popen to return our mock_proc
    with patch("subprocess.Popen", return_value=mock_proc):
        # To avoid the handshake in __init__ failing, we provide a successful first read
        # and then a failing second read.
        mock_proc.stdout.readline.side_effect = [
            '{"command": "ready", "version": "1.0"}\n',  # For handshake
            RuntimeError("Connection lost"),  # For execute
        ]

        with patch(
            "bioimage_mcp.runtimes.persistent.decode_message",
            side_effect=[
                {"command": "ready", "version": "1.0"},  # For handshake
                None,  # Should not be reached if readline fails
            ],
        ):
            worker = WorkerProcess("session-1", "test-env")

            # Execute should catch error, kill process, and re-raise
            with pytest.raises(RuntimeError, match="Connection lost"):
                worker.execute({"id": "test", "inputs": {}})

            # Assert kill was called
            mock_proc.kill.assert_called()
            assert worker.state == WorkerState.TERMINATED


def test_worker_shutdown_force_kills_on_busy_timeout():
    """Verify worker is force-killed if it remains BUSY during shutdown."""
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # Running

    with patch("subprocess.Popen", return_value=mock_proc):
        mock_proc.stdout.readline.return_value = '{"command": "ready", "version": "1.0"}\n'
        with patch(
            "bioimage_mcp.runtimes.persistent.decode_message",
            return_value={"command": "ready", "version": "1.0"},
        ):
            worker = WorkerProcess("session-1", "test-env")
            assert worker.state == WorkerState.READY

            # Manually set to BUSY
            worker.state = WorkerState.BUSY

            # Shutdown with a very small timeout
            worker.shutdown(graceful=True, wait_timeout=0.1)

            # Assert kill was called because it timed out waiting for non-BUSY
            mock_proc.kill.assert_called()
            assert worker.state == WorkerState.TERMINATED
