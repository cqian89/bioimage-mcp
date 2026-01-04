from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioimage_mcp.artifacts.models import ArtifactRef

logger = logging.getLogger(__name__)


class ArtifactInvalidatedError(Exception):
    """Raised when attempting to access an invalidated mem:// artifact.

    This typically occurs when the worker owning the artifact has crashed.
    T060: Clear error message for invalidated artifacts.
    """

    pass


def parse_mem_uri(uri: str) -> tuple[str, str, str]:
    """Parse mem://<session_id>/<env_id>/<artifact_id>.

    Returns (session_id, env_id, artifact_id).
    """
    if not uri.startswith("mem://"):
        raise ValueError(f"Invalid memory URI: {uri}")

    parts = uri[6:].split("/")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid memory URI format: {uri}. Expected mem://<session_id>/<env_id>/<artifact_id>"
        )

    return parts[0], parts[1], parts[2]


def build_mem_uri(session_id: str, env_id: str, artifact_id: str) -> str:
    """Build a mem:// URI."""
    return f"mem://{session_id}/{env_id}/{artifact_id}"


class MemoryArtifactStore:
    """Registry for tracking mem:// artifact references.

    IMPLEMENTATION STATUS (Spec 011):
    ================================
    Current (Phase 1): Simulated mem:// URIs
    - Tracks metadata (ArtifactRef) with mem:// URIs
    - Actual data backed by files (_simulated_path in metadata)
    - Provides API surface for future true in-memory storage

    Future (Phase 2): True in-memory storage
    - Data lives in persistent worker subprocess memory
    - mem:// URIs resolve to actual in-memory objects
    - No file backing required for intermediate artifacts

    This simulation approach is acceptable because:
    - API contracts remain stable (mem:// URI format unchanged)
    - Enables testing and development of higher-level workflows
    - Graceful migration path when persistent workers are ready

    See: specs/011-wrapper-consolidation/plan.md Phase 1 (T008-T010)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # ref_id -> ArtifactRef
        self._artifacts: dict[str, ArtifactRef] = {}
        # session_id -> set(ref_id)
        self._session_index: dict[str, set[str]] = {}
        # (session_id, env_id) -> set(ref_id)
        self._worker_index: dict[tuple[str, str], set[str]] = {}

    def register(self, ref: ArtifactRef) -> str:
        """Register a memory artifact, returns the ref_id."""
        session_id, env_id, _ = parse_mem_uri(ref.uri)

        with self._lock:
            self._artifacts[ref.ref_id] = ref

            # Update indices
            if session_id not in self._session_index:
                self._session_index[session_id] = set()
            self._session_index[session_id].add(ref.ref_id)

            worker_key = (session_id, env_id)
            if worker_key not in self._worker_index:
                self._worker_index[worker_key] = set()
            self._worker_index[worker_key].add(ref.ref_id)

        logger.debug("Memory artifact registered: ref_id=%s uri=%s", ref.ref_id, ref.uri)
        return ref.ref_id

    def get(self, ref_id: str) -> ArtifactRef | None:
        """Retrieve artifact metadata by ref_id."""
        with self._lock:
            return self._artifacts.get(ref_id)

    def exists(self, ref_id: str) -> bool:
        """Check if artifact exists."""
        with self._lock:
            return ref_id in self._artifacts

    def get_by_session(self, session_id: str) -> list[ArtifactRef]:
        """Get all artifacts for a session."""
        with self._lock:
            ref_ids = self._session_index.get(session_id, set())
            return [self._artifacts[rid] for rid in ref_ids if rid in self._artifacts]

    def invalidate_session(self, session_id: str) -> list[str]:
        """Invalidate all artifacts for a session, returns list of ref_ids."""
        with self._lock:
            ref_ids = list(self._session_index.pop(session_id, set()))
            for rid in ref_ids:
                ref = self._artifacts.pop(rid, None)
                if ref:
                    # Clean up worker index
                    try:
                        s_id, e_id, _ = parse_mem_uri(ref.uri)
                        worker_key = (s_id, e_id)
                        if worker_key in self._worker_index:
                            self._worker_index[worker_key].discard(rid)
                            if not self._worker_index[worker_key]:
                                del self._worker_index[worker_key]
                    except ValueError:
                        pass
            logger.info("Session invalidated: session_id=%s artifacts=%d", session_id, len(ref_ids))
            return ref_ids

    def invalidate_worker(self, session_id: str, env_id: str) -> list[str]:
        """Invalidate all artifacts for a worker (when it crashes)."""
        worker_key = (session_id, env_id)
        with self._lock:
            ref_ids = list(self._worker_index.pop(worker_key, set()))
            for rid in ref_ids:
                self._artifacts.pop(rid, None)
                # Clean up session index
                if session_id in self._session_index:
                    self._session_index[session_id].discard(rid)
                    if not self._session_index[session_id]:
                        del self._session_index[session_id]
            logger.info(
                "Worker invalidated: session_id=%s env_id=%s artifacts=%d",
                session_id,
                env_id,
                len(ref_ids),
            )
            return ref_ids

    def evict(self, ref_id: str) -> bool:
        """Evict a single artifact from the store.

        Args:
            ref_id: Artifact reference ID to evict

        Returns:
            True if artifact was found and evicted, False if not found
        """
        with self._lock:
            ref = self._artifacts.pop(ref_id, None)
            if ref:
                # Clean up indices
                try:
                    session_id, env_id, _ = parse_mem_uri(ref.uri)

                    # Clean up session index
                    if session_id in self._session_index:
                        self._session_index[session_id].discard(ref_id)
                        if not self._session_index[session_id]:
                            del self._session_index[session_id]

                    # Clean up worker index
                    worker_key = (session_id, env_id)
                    if worker_key in self._worker_index:
                        self._worker_index[worker_key].discard(ref_id)
                        if not self._worker_index[worker_key]:
                            del self._worker_index[worker_key]
                except ValueError:
                    pass

                logger.info("Memory artifact evicted: ref_id=%s uri=%s", ref_id, ref.uri)
                return True

            logger.debug("Memory artifact not found for eviction: ref_id=%s", ref_id)
            return False
