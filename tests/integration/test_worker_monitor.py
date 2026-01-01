"""Integration tests for background worker monitor thread (spec012).

Tests the background monitor thread that:
- Detects crashed workers proactively (within 5s)
- Captures stderr from crashed workers
- Invalidates mem:// artifacts via MemoryArtifactStore.invalidate_worker
- Removes crashed workers from registry
- Reaps idle workers
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import tifffile

from bioimage_mcp.artifacts.memory import MemoryArtifactStore
from bioimage_mcp.runtimes.persistent import PersistentWorkerManager


class TestBackgroundMonitor:
    """Tests for background worker monitor thread."""

    def test_monitor_detects_crashed_worker(self, tmp_path: Path):
        """Verify monitor detects crashed worker within 5 seconds.

        Related: spec012 - Background monitor thread

        Expected behavior:
        1. Spawn a worker
        2. Create a mem:// artifact in worker
        3. Kill the worker process forcefully
        4. Monitor should detect crash within 5 seconds
        5. Monitor should invalidate mem:// artifacts
        6. Monitor should remove worker from registry
        """
        memory_store = MemoryArtifactStore()
        # Use short monitor interval for faster testing
        manager = PersistentWorkerManager(
            memory_store=memory_store,
            monitor_interval_seconds=1.0,  # Check every 1 second
        )

        # Get worker for base environment
        session_id = "test_session"
        env_id = "bioimage-mcp-base"
        worker = manager.get_worker(session_id=session_id, env_id=env_id)

        # Create a simple test image file
        test_data = np.random.randint(0, 255, (10, 10), dtype=np.uint8)
        test_image = tmp_path / "test_input.tif"
        tifffile.imwrite(test_image, test_data)

        # Create a mem:// artifact in worker
        request = {
            "fn_id": "base.bioio.export",
            "inputs": {"image": {"uri": f"file://{test_image}"}},
            "params": {
                "format": "OME-TIFF",
                "output_mode": "memory",
            },
            "work_dir": str(tmp_path),
        }

        response = worker.execute(request, memory_store=memory_store)
        assert response.get("ok") is True, f"Failed to create artifact: {response.get('error')}"

        # Get the memory artifact reference
        mem_artifact_ref = response["outputs"]["output"]
        ref_id = mem_artifact_ref["ref_id"]

        # Verify artifact is in memory store
        assert memory_store.get(ref_id) is not None, "Artifact should be in memory store"

        # Kill the worker forcefully
        worker._process.kill()
        worker._process.wait()

        # Wait for monitor to detect crash (should happen within 5 seconds)
        # Monitor runs every 1 second, so 5 seconds is generous
        start_time = time.time()
        detected = False
        artifact_invalidated = False

        for _ in range(10):  # 10 iterations * 0.5s = 5 seconds max
            time.sleep(0.5)
            # Check if worker was removed from registry AND artifact was invalidated
            if not manager.is_worker_alive(session_id, env_id) and memory_store.get(ref_id) is None:
                detected = True
                artifact_invalidated = True
                break

        elapsed = time.time() - start_time
        assert detected, f"Monitor did not detect crash within {elapsed:.1f}s"
        assert elapsed < 5.0, f"Monitor took too long to detect crash: {elapsed:.1f}s"

        # Verify artifact was invalidated
        assert artifact_invalidated, "Artifact should be invalidated after worker crash"

        # Cleanup
        manager.shutdown_all()

    def test_monitor_reaps_idle_workers(self, tmp_path: Path):
        """Verify monitor reaps idle workers after timeout.

        Related: spec012 - Background monitor thread

        Expected behavior:
        1. Spawn a worker
        2. Execute a request to establish activity
        3. Wait for idle timeout to expire
        4. Monitor should reap the idle worker
        5. Worker should be removed from registry
        """
        memory_store = MemoryArtifactStore()
        # Use short intervals for faster testing
        manager = PersistentWorkerManager(
            memory_store=memory_store,
            monitor_interval_seconds=1.0,  # Check every 1 second
            session_timeout_seconds=3,  # 3 second idle timeout
        )

        # Get worker for base environment
        session_id = "test_session_idle"
        env_id = "bioimage-mcp-base"
        worker = manager.get_worker(session_id=session_id, env_id=env_id)

        # Execute a simple request to establish activity
        request = {
            "fn_id": "meta.describe",
            "inputs": {},
            "params": {"target_fn": "base.bioio.export"},
            "work_dir": str(tmp_path),
        }

        response = worker.execute(request, memory_store=memory_store)
        assert response.get("ok") is True, f"Request failed: {response.get('error')}"

        # Worker should be alive now
        assert manager.is_worker_alive(session_id, env_id), "Worker should be alive"

        # Wait for idle timeout + monitor interval to pass
        # 3s idle timeout + 2.5s buffer for monitor to run = 5.5s total
        time.sleep(5.5)

        # Check if worker was reaped
        assert not manager.is_worker_alive(session_id, env_id), (
            "Worker should be reaped after idle timeout"
        )

        # Cleanup
        manager.shutdown_all()

    def test_monitor_thread_stops_on_shutdown(self, tmp_path: Path):
        """Verify monitor thread stops cleanly on shutdown_all.

        Related: spec012 - Background monitor thread

        Expected behavior:
        1. Create manager (starts monitor thread)
        2. Verify monitor thread is running
        3. Call shutdown_all()
        4. Verify monitor thread stops within timeout
        """
        memory_store = MemoryArtifactStore()
        manager = PersistentWorkerManager(
            memory_store=memory_store,
            monitor_interval_seconds=1.0,
        )

        # Verify monitor thread is running
        assert manager._monitor_thread.is_alive(), "Monitor thread should be running"

        # Shutdown
        manager.shutdown_all()

        # Verify monitor thread stopped
        # Give it a moment to stop
        time.sleep(1.0)
        assert not manager._monitor_thread.is_alive(), "Monitor thread should be stopped"
