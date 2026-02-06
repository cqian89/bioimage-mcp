"""Tests for worker manager shutdown behavior."""

from unittest.mock import MagicMock, patch

from bioimage_mcp.runtimes.persistent import PersistentWorkerManager, WorkerProcess, WorkerState


def test_manager_shutdown_all_cleans_registry():
    """Verify shutdown_all kills all workers and clears the registry."""
    # Mock MemoryArtifactStore
    mock_mem = MagicMock()

    manager = PersistentWorkerManager(memory_store=mock_mem)

    # Mock WorkerProcess
    mock_proc1 = MagicMock()
    mock_proc1.poll.return_value = None
    mock_proc2 = MagicMock()
    mock_proc2.poll.return_value = None

    # Mock Popen to return our mock processes
    with patch("subprocess.Popen", side_effect=[mock_proc1, mock_proc2]):
        with patch(
            "bioimage_mcp.runtimes.executor.detect_env_manager",
            return_value=("mamba", "mamba", "1.0"),
        ):
            with patch(
                "bioimage_mcp.runtimes.persistent.decode_message",
                return_value={"command": "ready", "version": "1.0"},
            ):
                # Hack to allow readline to return successfully
                mock_proc1.stdout.readline.return_value = '{"command": "ready"}\n'
                mock_proc2.stdout.readline.return_value = '{"command": "ready"}\n'

                # Spawn two workers
                manager.get_worker("session-1", "env-1")
                manager.get_worker("session-1", "env-2")

                assert len(manager._workers) == 2

                # Shutdown all
                manager.shutdown_all()

                # Registry should be empty
                assert len(manager._workers) == 0

                # Both processes should have been killed (gracefully or forced)
                # manager.shutdown_all calls worker.shutdown(graceful=True)
                # which in turn calls process.kill() if IPC fails or timeout occurs.
                # In our mock, IPC will fail because we didn't mock stdin.write etc fully for both.
                # But the goal is to see that some form of termination was attempted.
                assert mock_proc1.kill.called or mock_proc1.stdin.write.called
                assert mock_proc2.kill.called or mock_proc2.stdin.write.called


def test_worker_shutdown_handles_ack_timeout():
    """Verify worker is force-killed if it doesn't ACK shutdown."""
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

            # Mock readline to hang (return empty but ack_thread will timeout)
            # Actually, readline() will block. We want to test the timeout.
            # We can use side_effect to wait
            import time

            def hanging_readline():
                time.sleep(5)
                return ""

            mock_proc.stdout.readline.side_effect = hanging_readline

            # Shutdown with small timeout
            # Note: the ACK timeout in shutdown() is hardcoded to 2.0s in my implementation
            worker.shutdown(graceful=True)

            # Assert kill was called because it timed out waiting for ACK
            mock_proc.kill.assert_called()
            assert worker.state == WorkerState.TERMINATED
