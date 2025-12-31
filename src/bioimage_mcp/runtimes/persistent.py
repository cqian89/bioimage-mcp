from __future__ import annotations

import errno
import os
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Tuple

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from bioimage_mcp.artifacts.memory import MemoryArtifactStore


class WorkerSession(BaseModel):
    session_id: str
    env_id: str
    process_id: int
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_artifacts: list[str] = Field(default_factory=list)  # ref_ids in worker memory


class PersistentWorkerManager:
    """Manages persistent worker processes for tools.

    NOTE: In the current iteration (T016), this manager tracks worker state and
    artifact ownership, but actual process reuse is planned for a future iteration.
    For now, each step still spawns a new process, but the manager provides the
    infrastructure for memory artifact tracking that persists across these calls.
    """

    def __init__(self, memory_store: MemoryArtifactStore | None = None) -> None:
        self._workers: Dict[Tuple[str, str], WorkerSession] = {}
        self._lock = threading.Lock()
        self._memory_store = memory_store

    def get_worker(self, session_id: str, env_id: str) -> WorkerSession:
        """Get or create a worker for the session/env pair."""
        key = (session_id, env_id)
        with self._lock:
            if key not in self._workers:
                # For now, we use a placeholder process_id of 0 as per requirements
                self._workers[key] = WorkerSession(
                    session_id=session_id,
                    env_id=env_id,
                    process_id=0,
                )
            return self._workers[key]

    def shutdown_worker(self, session_id: str, env_id: str) -> None:
        """Gracefully stop a worker."""
        key = (session_id, env_id)
        with self._lock:
            if key in self._workers:
                # In the future, this will involve killing the subprocess
                del self._workers[key]

    def shutdown_all(self) -> None:
        """Stop all workers (for server shutdown)."""
        with self._lock:
            # In the future, iterate and kill all subprocesses
            self._workers.clear()

    def register_artifact(self, session_id: str, env_id: str, ref_id: str) -> None:
        """Register a new in-memory artifact."""
        key = (session_id, env_id)
        with self._lock:
            if key in self._workers:
                worker = self._workers[key]
                if ref_id not in worker.active_artifacts:
                    worker.active_artifacts.append(ref_id)

    def get_artifacts(self, session_id: str, env_id: str) -> list[str]:
        """Get all artifact refs for a worker."""
        key = (session_id, env_id)
        with self._lock:
            if key in self._workers:
                return list(self._workers[key].active_artifacts)
            return []

    def is_worker_alive(self, session_id: str, env_id: str) -> bool:
        """Check if worker process is still running."""
        key = (session_id, env_id)
        with self._lock:
            if key not in self._workers:
                return False

            worker = self._workers[key]
            if worker.process_id == 0:
                # Not yet launched or placeholder
                return True

            try:
                os.kill(worker.process_id, 0)
            except OSError as e:
                # ESRCH means the process does not exist
                return e.errno != errno.ESRCH
            return True

    def handle_worker_crash(self, session_id: str, env_id: str) -> list[str]:
        """Handle worker crash - returns list of invalidated artifact ref_ids."""
        # Get artifacts that were in the worker
        artifacts = self.get_artifacts(session_id, env_id)

        # Remove worker from registry
        self.shutdown_worker(session_id, env_id)

        # Invalidate in memory store if available
        if self._memory_store:
            self._memory_store.invalidate_worker(session_id, env_id)

        return artifacts
