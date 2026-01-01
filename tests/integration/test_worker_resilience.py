import pytest
from datetime import UTC, datetime
from bioimage_mcp.runtimes.persistent import PersistentWorkerManager
from bioimage_mcp.artifacts.memory import MemoryArtifactStore, build_mem_uri
from bioimage_mcp.artifacts.models import ArtifactRef


class TestWorkerResilience:
    """Integration tests for worker crash handling and artifact invalidation."""

    @pytest.fixture
    def memory_store(self):
        return MemoryArtifactStore()

    @pytest.fixture
    def worker_manager(self, memory_store):
        return PersistentWorkerManager(memory_store=memory_store)

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
        env_id = "env1"
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
        env_id = "env1"

        # 1. Get initial worker
        worker1 = worker_manager.get_worker(session_id, env_id)
        worker_manager.register_artifact(session_id, env_id, "art1")

        # 2. Crash
        worker_manager.handle_worker_crash(session_id, env_id)

        # 3. Get new worker
        worker2 = worker_manager.get_worker(session_id, env_id)

        # 4. Verify it's a new instance (different object)
        assert worker1 is not worker2
        assert len(worker2.active_artifacts) == 0
        # started_at should be >= worker1.started_at
        assert worker2.started_at >= worker1.started_at

    def test_multiple_workers_independent(self, worker_manager, memory_store):
        """Test that crashing one worker doesn't affect another."""
        session_id = "session1"
        env1 = "env1"
        env2 = "env2"

        # 1. Setup two workers
        worker_manager.get_worker(session_id, env1)
        worker_manager.get_worker(session_id, env2)

        art1 = "art-env1"
        art2 = "art-env2"

        memory_store.register(self._create_memory_artifact(session_id, env1, art1))
        memory_store.register(self._create_memory_artifact(session_id, env2, art2))

        worker_manager.register_artifact(session_id, env1, art1)
        worker_manager.register_artifact(session_id, env2, art2)

        # 2. Crash worker 1
        worker_manager.handle_worker_crash(session_id, env1)

        # 3. Verify worker 1 artifacts gone, worker 2 artifacts remain
        assert not memory_store.exists(art1)
        assert memory_store.exists(art2)
        assert art2 in worker_manager.get_artifacts(session_id, env2)

        # Verify worker 2 is still alive (in our mock world where process_id=0 means alive)
        assert worker_manager.is_worker_alive(session_id, env2)
        assert not worker_manager.is_worker_alive(session_id, env1)

    def test_session_invalidation_clears_all_workers(self, worker_manager, memory_store):
        """Test that invalidating a session clears all artifacts."""
        session_id = "session-to-clear"
        env1 = "env1"
        env2 = "env2"

        # 1. Setup multiple workers in the same session
        worker_manager.get_worker(session_id, env1)
        worker_manager.get_worker(session_id, env2)

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
