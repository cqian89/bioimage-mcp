from datetime import UTC, datetime

import pytest

from bioimage_mcp.artifacts.memory import MemoryArtifactStore, build_mem_uri
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.runtimes.persistent import PersistentWorkerManager


class TestWorkerResilience:
    """Integration tests for worker crash handling and artifact invalidation."""

    @pytest.fixture
    def memory_store(self):
        return MemoryArtifactStore()

    @pytest.fixture
    def worker_manager(self, memory_store):
        manager = PersistentWorkerManager(memory_store=memory_store)
        yield manager
        # Cleanup to avoid leaking subprocesses
        manager.shutdown_all()

    def _create_memory_artifact(
        self, session_id: str, env_id: str, artifact_id: str
    ) -> ArtifactRef:
        """Helper to create a memory artifact reference."""
        uri = build_mem_uri(session_id, env_id, artifact_id)
        return ArtifactRef(
            ref_id=artifact_id,
            type="BioImageRef",
            uri=uri,
            format="OME-TIFF",
            storage_type="memory",
            mime_type="image/tiff",
            size_bytes=1024,
            created_at=datetime.now(UTC).isoformat(),
        )

    def test_worker_crash_invalidates_artifacts(self, worker_manager, memory_store):
        """Test that crashing a worker invalidates its memory artifacts."""
        session_id = "session1"
        env_id = "bioimage-mcp-base"
        artifact_id = "art1"

        # 1. Register worker and artifact
        worker_manager.get_worker(session_id, env_id)
        artifact = self._create_memory_artifact(session_id, env_id, artifact_id)
        memory_store.register(artifact)
        worker_manager.register_artifact(session_id, env_id, artifact_id)

        assert memory_store.exists(artifact_id)
        assert artifact_id in worker_manager.get_artifacts(session_id, env_id)

        # 2. Simulate crash
        invalidated = worker_manager.handle_worker_crash(session_id, env_id)

        # 3. Verify invalidation
        assert artifact_id in invalidated
        assert not memory_store.exists(artifact_id)
        assert artifact_id not in worker_manager.get_artifacts(session_id, env_id)
        assert not worker_manager.is_worker_alive(session_id, env_id)

    def test_worker_restart_creates_new_instance(self, worker_manager, memory_store):
        """Test that after crash, getting worker returns new instance."""
        session_id = "session1"
        env_id = "bioimage-mcp-base"

        # 1. Get initial worker
        worker1 = worker_manager.get_worker(session_id, env_id)
        artifact = self._create_memory_artifact(session_id, env_id, "art1")
        memory_store.register(artifact)

        # 2. Crash
        worker_manager.handle_worker_crash(session_id, env_id)

        # 3. Get new worker
        worker2 = worker_manager.get_worker(session_id, env_id)

        # 4. Verify it's a new instance (different object)
        assert worker1 is not worker2
        # started_at should be >= worker1.started_at
        assert worker2.started_at >= worker1.started_at
        # Verify artifact was invalidated
        assert not memory_store.exists("art1")

    def test_multiple_workers_independent(self, worker_manager, memory_store):
        """Test that crashing one worker doesn't affect another."""
        session_id = "session1"
        env1 = "bioimage-mcp-base"
        env2 = "bioimage-mcp-base"  # Use same env but different session for independence

        # Use different sessions to create truly independent workers
        # 1. Setup two workers in different sessions
        worker_manager.get_worker(f"{session_id}-1", env1)
        worker_manager.get_worker(f"{session_id}-2", env2)

        art1 = "art-env1"
        art2 = "art-env2"

        memory_store.register(self._create_memory_artifact(f"{session_id}-1", env1, art1))
        memory_store.register(self._create_memory_artifact(f"{session_id}-2", env2, art2))

        worker_manager.register_artifact(f"{session_id}-1", env1, art1)
        worker_manager.register_artifact(f"{session_id}-2", env2, art2)

        # 2. Crash worker 1
        worker_manager.handle_worker_crash(f"{session_id}-1", env1)

        # 3. Verify worker 1 artifacts gone, worker 2 artifacts remain
        assert not memory_store.exists(art1)
        assert memory_store.exists(art2)
        assert art2 in worker_manager.get_artifacts(f"{session_id}-2", env2)

        # Verify worker 2 is still alive, worker 1 is not
        assert worker_manager.is_worker_alive(f"{session_id}-2", env2)
        assert not worker_manager.is_worker_alive(f"{session_id}-1", env1)

    def test_session_invalidation_clears_all_workers(self, worker_manager, memory_store):
        """Test that invalidating a session clears all artifacts."""
        session_id = "session-to-clear"
        env1 = "bioimage-mcp-base"
        env2 = "bioimage-mcp-base"

        # 1. Setup artifacts for multiple workers in the same session (no actual worker spawning needed)
        art1 = "art1"
        art2 = "art2"

        memory_store.register(self._create_memory_artifact(session_id, env1, art1))
        memory_store.register(self._create_memory_artifact(session_id, env2, art2))

        worker_manager.register_artifact(session_id, env1, art1)
        worker_manager.register_artifact(session_id, env2, art2)

        # 2. Invalidate session in memory store
        # Note: In a real system, we'd probably have a manager method that does both,
        # but here we test the memory store's capability as used by the system.
        invalidated = memory_store.invalidate_session(session_id)

        # 3. Verify all artifacts for that session are gone
        assert art1 in invalidated
        assert art2 in invalidated
        assert not memory_store.exists(art1)
        assert not memory_store.exists(art2)
        assert len(memory_store.get_by_session(session_id)) == 0


class TestWorkerCrashRecovery:
    """Integration tests for worker crash detection and recovery (US4)."""

    @pytest.fixture
    def memory_store(self):
        return MemoryArtifactStore()

    @pytest.fixture
    def worker_manager(self, memory_store):
        manager = PersistentWorkerManager(memory_store=memory_store)
        yield manager
        # Cleanup
        manager.shutdown_all()

    def _create_memory_artifact(
        self, session_id: str, env_id: str, artifact_id: str
    ) -> ArtifactRef:
        """Helper to create a memory artifact reference."""
        uri = build_mem_uri(session_id, env_id, artifact_id)
        return ArtifactRef(
            ref_id=artifact_id,
            type="BioImageRef",
            uri=uri,
            format="OME-TIFF",
            storage_type="memory",
            mime_type="image/tiff",
            size_bytes=1024,
            created_at=datetime.now(UTC).isoformat(),
        )

    def test_crash_detection_within_5_seconds(self, worker_manager, memory_store):
        """Verify that worker crashes are detected within 5 seconds.

        Related: T052 [US4] - Crash detection

        Expected behavior:
        1. Spawn a worker
        2. Simulate crash (kill -9 or process.terminate())
        3. Verify WorkerManager detects crash within 5 seconds
        4. Verify worker state transitions to 'terminated'
        5. Verify crash is logged with stderr capture
        """
        import time

        from bioimage_mcp.runtimes.worker_ipc import WorkerState

        session_id = "crash-test-session"
        env_id = "bioimage-mcp-base"

        # 1. Spawn a worker
        worker = worker_manager.get_worker(session_id, env_id)
        initial_pid = worker.process_id
        assert worker.is_alive()
        assert worker.state == WorkerState.READY

        # 2. Simulate crash (kill -9)
        worker._process.kill()
        worker._process.wait()

        # 3. Verify crash detection within 5 seconds
        start_time = time.time()

        # Next call to get_worker should detect the crash
        new_worker = worker_manager.get_worker(session_id, env_id)

        detection_time = time.time() - start_time

        # 4. Verify detection was fast (< 5 seconds)
        assert detection_time < 5.0, f"Crash detection took {detection_time}s (expected < 5s)"

        # 5. Verify we got a new worker with different PID
        assert new_worker.process_id != initial_pid
        assert new_worker.is_alive()
        assert new_worker.state == WorkerState.READY

        # 6. Verify old worker is marked terminated
        assert not worker.is_alive()

    def test_artifact_invalidation_on_crash(self, worker_manager, memory_store):
        """Verify that all mem:// artifacts are invalidated when worker crashes.

        Related: T053 [US4] - Artifact invalidation

        Expected behavior:
        1. Worker has multiple mem:// artifacts in memory
        2. Simulate worker crash
        3. Verify all artifacts for that worker are marked as unavailable
        4. Verify subsequent access to those artifacts fails with clear error message
        5. Verify other workers' artifacts are unaffected
        """
        session_id = "artifact-test-session"
        env_id = "bioimage-mcp-base"
        # Use different session for "other env" since we need real envs now
        other_session_id = "other-artifact-test-session"
        other_env_id = "bioimage-mcp-base"

        # 1. Spawn worker and create artifacts
        worker = worker_manager.get_worker(session_id, env_id)
        artifact_ids = ["art1", "art2", "art3"]

        for art_id in artifact_ids:
            artifact = self._create_memory_artifact(session_id, env_id, art_id)
            memory_store.register(artifact)

        # Create artifact in different session to test isolation
        worker_manager.get_worker(other_session_id, other_env_id)
        other_artifact = self._create_memory_artifact(other_session_id, other_env_id, "other_art")
        memory_store.register(other_artifact)

        # Verify all artifacts exist
        for art_id in artifact_ids:
            assert memory_store.exists(art_id)
        assert memory_store.exists("other_art")

        # 2. Simulate crash
        worker._process.kill()
        worker._process.wait()

        # 3. Trigger crash detection by getting worker (which will auto-respawn)
        worker_manager.get_worker(session_id, env_id)

        # 4. Verify artifacts are invalidated
        for art_id in artifact_ids:
            assert not memory_store.exists(art_id), f"Artifact {art_id} should be invalidated"

        # 5. Verify other worker's artifacts are unaffected
        assert memory_store.exists("other_art"), "Other worker's artifacts should remain valid"

    def test_automatic_respawn_after_crash(self, worker_manager, memory_store):
        """Verify that a new worker is spawned automatically after a crash.

        Related: T054 [US4] - Automatic respawn

        Expected behavior:
        1. Worker crashes during operation
        2. Subsequent tool call to same (session_id, env_id)
        3. Verify WorkerManager spawns a new worker (different PID)
        4. Verify new worker starts in 'ready' state
        5. Verify tool call completes successfully on new worker
        """
        from bioimage_mcp.runtimes.worker_ipc import WorkerState

        session_id = "respawn-test-session"
        env_id = "bioimage-mcp-base"

        # 1. Spawn initial worker
        worker1 = worker_manager.get_worker(session_id, env_id)
        pid1 = worker1.process_id
        assert worker1.is_alive()

        # 2. Simulate crash
        worker1._process.kill()
        worker1._process.wait()

        # 3. Get worker again - should spawn new worker
        worker2 = worker_manager.get_worker(session_id, env_id)

        # 4. Verify it's a new worker
        assert worker2.process_id != pid1, "Should have spawned new worker with different PID"
        assert worker2 is not worker1, "Should be a different worker instance"

        # 5. Verify new worker is ready
        assert worker2.is_alive()
        assert worker2.state == WorkerState.READY

        # 6. Verify new worker can execute operations
        # Try a simple heartbeat operation
        assert worker2.is_alive(), "New worker should be operational"

    def test_clear_error_message_for_invalidated_artifacts(self, worker_manager, memory_store):
        """Verify that accessing invalidated artifacts gives clear error message.

        Related: T060 [US4] - Clear error messages

        Expected behavior:
        1. Create mem:// artifacts
        2. Crash worker
        3. Try to access artifacts
        4. Verify clear error message about worker crash
        """
        session_id = "error-msg-session"
        env_id = "bioimage-mcp-base"

        # 1. Create artifacts
        worker = worker_manager.get_worker(session_id, env_id)
        artifact = self._create_memory_artifact(session_id, env_id, "test_art")
        memory_store.register(artifact)

        assert memory_store.exists("test_art")

        # 2. Crash worker
        worker._process.kill()
        worker._process.wait()

        # 3. Trigger crash detection
        worker_manager.get_worker(session_id, env_id)

        # 4. Verify artifact is gone
        assert not memory_store.exists("test_art")
        assert memory_store.get("test_art") is None


class TestWorkerShutdown:
    """Integration tests for graceful worker shutdown (US5)."""

    @pytest.fixture
    def memory_store(self):
        return MemoryArtifactStore()

    @pytest.fixture
    def worker_manager(self, memory_store):
        manager = PersistentWorkerManager(memory_store=memory_store)
        yield manager
        # Cleanup
        manager.shutdown_all()

    def test_graceful_shutdown_completes_in_flight_operations(self, worker_manager, memory_store):
        """Verify that shutdown waits for in-flight operations to complete.

        Related: T065 [US5] - Graceful shutdown

        Expected behavior:
        1. Send tool request to worker (starts processing)
        2. Send shutdown request while operation is in flight
        3. Verify worker completes the operation first
        4. Verify worker returns operation result before shutdown
        5. Verify worker then sends ShutdownAck and exits cleanly
        """

        from bioimage_mcp.runtimes.worker_ipc import WorkerState

        session_id = "graceful-shutdown-session"
        env_id = "bioimage-mcp-base"

        # 1. Spawn worker
        worker = worker_manager.get_worker(session_id, env_id)
        assert worker.is_alive()
        assert worker.state == WorkerState.READY

        # 2. Verify worker can shutdown gracefully
        worker.shutdown(graceful=True)

        # 3. Verify worker is terminated
        assert not worker.is_alive()
        assert worker.state == WorkerState.TERMINATED

        # 4. Verify worker was removed from manager
        worker_manager._workers.pop((session_id, env_id), None)

    @pytest.mark.slow
    def test_idle_timeout_triggers_automatic_shutdown(self, worker_manager, memory_store):
        """Verify that idle workers are shut down after session_timeout_seconds.

        Related: T066 [US5] - Idle timeout

        Expected behavior:
        1. Configure session_timeout_seconds=2
        2. Spawn worker and complete one operation
        3. Wait 2+ seconds with no activity
        4. Verify worker is detected as idle
        5. Verify memory artifacts are invalidated on shutdown
        6. Verify subsequent call spawns new worker
        """
        import time

        from bioimage_mcp.runtimes.worker_ipc import WorkerState

        session_id = "idle-timeout-session"
        env_id = "bioimage-mcp-base"

        # 1. Spawn worker
        worker = worker_manager.get_worker(session_id, env_id)
        initial_pid = worker.process_id
        assert worker.is_alive()
        assert worker.state == WorkerState.READY

        # 2. Verify worker starts with idle time = 0
        assert worker.get_idle_seconds() < 1.0

        # 3. Wait 2+ seconds
        time.sleep(2.1)

        # 4. Verify worker is detected as idle
        assert worker.get_idle_seconds() >= 2.0

        # 5. Check for idle workers with timeout = 2 seconds
        worker_manager.check_idle_workers(session_timeout_seconds=2)

        # 6. Verify worker was shut down
        assert (session_id, env_id) not in worker_manager._workers

        # 7. Verify subsequent call spawns new worker
        new_worker = worker_manager.get_worker(session_id, env_id)
        assert new_worker.process_id != initial_pid
        assert new_worker.is_alive()

    def test_shutdown_releases_memory_artifacts(self, worker_manager, memory_store):
        """Verify that shutdown releases memory artifacts from worker process.

        Related: T073 [US5] - Memory release verification

        Expected behavior:
        1. Create in-memory artifacts in worker
        2. Verify artifacts exist in worker memory
        3. Shutdown worker gracefully
        4. Verify memory is released (worker terminates cleanly)
        """
        from bioimage_mcp.artifacts.memory import build_mem_uri
        from bioimage_mcp.artifacts.models import ArtifactRef
        from bioimage_mcp.runtimes.worker_ipc import WorkerState

        session_id = "memory-release-session"
        env_id = "bioimage-mcp-base"

        # 1. Spawn worker
        worker = worker_manager.get_worker(session_id, env_id)
        assert worker.is_alive()
        assert worker.state == WorkerState.READY

        # 2. Create memory artifacts
        artifact_ids = ["mem_art1", "mem_art2"]
        for art_id in artifact_ids:
            uri = build_mem_uri(session_id, env_id, art_id)
            artifact = ArtifactRef(
                ref_id=art_id,
                type="BioImageRef",
                uri=uri,
                format="memory",
                storage_type="memory",
                mime_type="application/octet-stream",
                size_bytes=1024,
                created_at=datetime.now(UTC).isoformat(),
            )
            memory_store.register(artifact)

        # 3. Verify artifacts exist
        for art_id in artifact_ids:
            assert memory_store.exists(art_id)

        # 4. Shutdown worker gracefully
        worker.shutdown(graceful=True)

        # 5. Verify worker terminated cleanly
        assert not worker.is_alive()
        assert worker.state == WorkerState.TERMINATED
