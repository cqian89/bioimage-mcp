from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from bioimage_mcp.runtimes.worker_ipc import (
    EvictRequest,
    ExecuteRequest,
    MaterializeRequest,
    ShutdownRequest,
    WorkerState,
    decode_message,
    encode_message,
)

if TYPE_CHECKING:
    from bioimage_mcp.artifacts.memory import MemoryArtifactStore

logger = logging.getLogger(__name__)


def _build_worker_command(entrypoint: str, *, env_id: str | None) -> list[str]:
    """Build command to spawn worker process with optional conda environment.

    Args:
        entrypoint: Python module or script path to execute
        env_id: Optional conda environment name to activate

    Returns:
        Command list suitable for subprocess.Popen
    """
    from bioimage_mcp.bootstrap.env_manager import detect_env_manager

    entry_path = Path(entrypoint)

    manager = detect_env_manager() if env_id else None
    if manager:
        assert env_id is not None
        _name, exe, _version = manager
        if entry_path.exists() and entry_path.suffix == ".py":
            return [exe, "run", "-n", env_id, "python", str(entry_path)]
        return [exe, "run", "-n", env_id, "python", "-m", entrypoint]

    if entry_path.exists() and entry_path.suffix == ".py":
        return [sys.executable, str(entry_path)]
    return [sys.executable, "-m", entrypoint]


class WorkerProcess:
    """Manages a persistent worker subprocess with NDJSON IPC.

    This class handles:
    - Spawning worker subprocess with open stdin/stdout pipes
    - Sending ExecuteRequest and receiving ExecuteResponse via NDJSON
    - Monitoring stderr in background thread
    - Worker lifecycle management (spawning -> ready -> busy -> ready)
    - Clean shutdown with graceful termination

    Related: T021-T023 (US1 - subprocess spawning and pipe handling)
    """

    def __init__(
        self,
        session_id: str,
        env_id: str,
        entrypoint: str = "bioimage_mcp_base.entrypoint",
    ) -> None:
        """Initialize and spawn a worker process.

        Args:
            session_id: Session identifier for this worker
            env_id: Environment identifier (e.g., 'bioimage-mcp-base')
            entrypoint: Python module or script to execute
        """
        self.session_id = session_id
        self.env_id = env_id
        self.entrypoint = entrypoint
        self.state = WorkerState.SPAWNING
        self._ordinal_counter = 0
        self._lock = threading.Lock()
        self._request_lock = threading.Lock()  # T094: Serialize requests to this worker
        self._last_activity_at = datetime.now(UTC)  # T069: Track idle time

        # Spawn the subprocess
        cmd = _build_worker_command(entrypoint, env_id=env_id)
        logger.info("Spawning worker: session=%s env=%s cmd=%s", session_id, env_id, cmd)

        # Set environment variables for worker identity (T032)
        worker_env = os.environ.copy()
        worker_env["BIOIMAGE_MCP_SESSION_ID"] = session_id
        worker_env["BIOIMAGE_MCP_ENV_ID"] = env_id

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            env=worker_env,  # Pass environment variables
        )

        self.process_id = self._process.pid
        self.started_at = datetime.now(UTC)

        # Start stderr capture thread
        self._stderr_lines: Queue[str] = Queue()
        self._stderr_thread = threading.Thread(
            target=self._capture_stderr,
            daemon=True,
            name=f"worker-stderr-{session_id}-{env_id}",
        )
        self._stderr_thread.start()

        # Transition to READY state
        self.state = WorkerState.READY
        logger.info(
            "Worker ready: session=%s env=%s pid=%s",
            session_id,
            env_id,
            self.process_id,
        )

    def _capture_stderr(self) -> None:
        """Background thread to capture stderr from worker process."""
        try:
            assert self._process.stderr is not None
            for line in self._process.stderr:
                line = line.rstrip("\r\n")
                if line:
                    self._stderr_lines.put(line)
                    logger.debug("Worker stderr [%s/%s]: %s", self.session_id, self.env_id, line)
        except Exception as e:  # noqa: BLE001
            logger.warning("Stderr capture failed for %s/%s: %s", self.session_id, self.env_id, e)

    def _get_next_ordinal(self) -> int:
        """Thread-safe ordinal counter for request correlation."""
        with self._lock:
            self._ordinal_counter += 1
            return self._ordinal_counter

    def _update_activity(self) -> None:
        """Update last activity timestamp (T069)."""
        with self._lock:
            self._last_activity_at = datetime.now(UTC)

    def get_idle_seconds(self) -> float:
        """Get seconds since last activity (T069).

        Returns:
            Seconds since last activity
        """
        with self._lock:
            return (datetime.now(UTC) - self._last_activity_at).total_seconds()

    def execute(
        self,
        request: dict[str, Any],
        memory_store: MemoryArtifactStore | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Send execute request and wait for response.

        Args:
            request: ExecuteRequest dict (without 'command' field, will be added)
            memory_store: Optional memory artifact store for registering mem:// artifacts
            timeout_seconds: Optional timeout in seconds for this operation

        Returns:
            ExecuteResponse dict

        Raises:
            RuntimeError: If worker is not alive or in wrong state
            TimeoutError: If operation exceeds timeout
        """
        # T094: Use request_lock to serialize all requests to this worker
        # This ensures only one request is processed at a time (per-worker queueing)
        with self._request_lock:
            if not self.is_alive():
                raise RuntimeError(f"Worker process {self.process_id} is not alive")

            if self.state != WorkerState.READY:
                raise RuntimeError(f"Worker is not ready (state={self.state})")

            # Build ExecuteRequest with ordinal
            ordinal = self._get_next_ordinal()
            exec_req = ExecuteRequest(
                command="execute",
                fn_id=request.get("fn_id", ""),
                inputs=request.get("inputs", {}),
                params=request.get("params", {}),
                work_dir=request.get("work_dir", "."),
                ordinal=ordinal,
            )

            # Transition to BUSY
            with self._lock:
                self.state = WorkerState.BUSY
                self._update_activity()  # T069: Track activity on request start

            try:
                # Send request
                req_line = encode_message(exec_req)
                assert self._process.stdin is not None
                self._process.stdin.write(req_line)
                self._process.stdin.flush()

                logger.debug(
                    "Sent execute request: session=%s env=%s ordinal=%s fn_id=%s",
                    self.session_id,
                    self.env_id,
                    ordinal,
                    exec_req.fn_id,
                )

                # Read response (with optional timeout)
                assert self._process.stdout is not None

                if timeout_seconds is not None:
                    # Use threading-based timeout (cross-platform)
                    import threading

                    response_line = None
                    error = None

                    def read_response():
                        nonlocal response_line, error
                        try:
                            response_line = self._process.stdout.readline()
                        except Exception as e:
                            error = e

                    reader_thread = threading.Thread(target=read_response)
                    reader_thread.daemon = True
                    reader_thread.start()
                    reader_thread.join(timeout=timeout_seconds)

                    if reader_thread.is_alive():
                        # Timeout - kill the worker
                        logger.warning(
                            "Worker timeout: session=%s env=%s ordinal=%s timeout=%s",
                            self.session_id,
                            self.env_id,
                            ordinal,
                            timeout_seconds,
                        )
                        self._process.kill()
                        self._process.wait()
                        with self._lock:
                            self.state = WorkerState.TERMINATED
                        raise TimeoutError(f"Operation exceeded timeout of {timeout_seconds}s")

                    if error:
                        raise error

                    if not response_line:
                        raise RuntimeError("Worker closed stdout without response")
                else:
                    response_line = self._process.stdout.readline()
                    if not response_line:
                        raise RuntimeError("Worker closed stdout without response")

                response_dict = decode_message(response_line)

                # Validate response
                if response_dict.get("command") != "execute_result":
                    raise RuntimeError(
                        f"Expected execute_result, got {response_dict.get('command')}"
                    )

                if response_dict.get("ordinal") != ordinal:
                    raise RuntimeError(
                        f"Ordinal mismatch: expected {ordinal}, got {response_dict.get('ordinal')}"
                    )

                # Register memory artifacts in the memory store (T038)
                if memory_store and response_dict.get("ok"):
                    self._register_memory_artifacts(response_dict.get("outputs", {}), memory_store)

                logger.debug(
                    "Received execute response: session=%s env=%s ordinal=%s ok=%s",
                    self.session_id,
                    self.env_id,
                    ordinal,
                    response_dict.get("ok"),
                )

                return response_dict

            finally:
                # Transition back to READY
                with self._lock:
                    if self.state == WorkerState.BUSY:
                        self.state = WorkerState.READY
                        self._update_activity()  # T069: Track activity on completion

    def evict(self, ref_id: str) -> dict[str, Any]:
        """Send evict command to worker to remove artifact from memory.

        Args:
            ref_id: Artifact reference ID to evict

        Returns:
            EvictResponse dict

        Raises:
            RuntimeError: If worker is not alive
        """
        if not self.is_alive():
            raise RuntimeError(f"Worker process {self.process_id} is not alive")

        # Build EvictRequest with ordinal
        ordinal = self._get_next_ordinal()
        evict_req = EvictRequest(
            command="evict",
            ref_id=ref_id,
            ordinal=ordinal,
        )

        try:
            # Send request
            req_line = encode_message(evict_req)
            assert self._process.stdin is not None
            self._process.stdin.write(req_line)
            self._process.stdin.flush()

            logger.debug(
                "Sent evict request: session=%s env=%s ordinal=%s ref_id=%s",
                self.session_id,
                self.env_id,
                ordinal,
                ref_id,
            )

            # Read response
            assert self._process.stdout is not None
            response_line = self._process.stdout.readline()
            if not response_line:
                raise RuntimeError("Worker closed stdout without response")

            response_dict = decode_message(response_line)

            # Validate response
            if response_dict.get("command") != "evict_result":
                raise RuntimeError(f"Expected evict_result, got {response_dict.get('command')}")

            if response_dict.get("ordinal") != ordinal:
                raise RuntimeError(
                    f"Ordinal mismatch: expected {ordinal}, got {response_dict.get('ordinal')}"
                )

            logger.debug(
                "Received evict response: session=%s env=%s ordinal=%s ok=%s",
                self.session_id,
                self.env_id,
                ordinal,
                response_dict.get("ok"),
            )

            return response_dict

        except Exception:
            # Don't change worker state on evict failures
            raise

    def materialize(
        self,
        ref_id: str,
        target_format: str = "OME-TIFF",
        dest_path: str | None = None,
    ) -> dict[str, Any]:
        """Send materialize command to worker to export mem:// artifact to disk.

        Args:
            ref_id: Artifact reference ID to materialize
            target_format: Output format ('OME-TIFF' or 'OME-Zarr')
            dest_path: Optional destination path (auto-generated if None)

        Returns:
            MaterializeResponse dict with 'path' key on success

        Raises:
            RuntimeError: If worker is not alive
        """
        if not self.is_alive():
            raise RuntimeError(f"Worker process {self.process_id} is not alive")

        # Build MaterializeRequest with ordinal
        ordinal = self._get_next_ordinal()
        materialize_req = MaterializeRequest(
            command="materialize",
            ref_id=ref_id,
            target_format=target_format,  # type: ignore
            dest_path=dest_path,
            ordinal=ordinal,
        )

        try:
            # Send request
            req_line = encode_message(materialize_req)
            assert self._process.stdin is not None
            self._process.stdin.write(req_line)
            self._process.stdin.flush()

            logger.debug(
                "Sent materialize request: session=%s env=%s ordinal=%s ref_id=%s format=%s",
                self.session_id,
                self.env_id,
                ordinal,
                ref_id,
                target_format,
            )

            # Read response
            assert self._process.stdout is not None
            response_line = self._process.stdout.readline()
            if not response_line:
                raise RuntimeError("Worker closed stdout without response")

            response_dict = decode_message(response_line)

            # Validate response
            if response_dict.get("command") != "materialize_result":
                raise RuntimeError(
                    f"Expected materialize_result, got {response_dict.get('command')}"
                )

            if response_dict.get("ordinal") != ordinal:
                raise RuntimeError(
                    f"Ordinal mismatch: expected {ordinal}, got {response_dict.get('ordinal')}"
                )

            logger.debug(
                "Received materialize response: session=%s env=%s ordinal=%s ok=%s path=%s",
                self.session_id,
                self.env_id,
                ordinal,
                response_dict.get("ok"),
                response_dict.get("path"),
            )

            return response_dict

        except Exception:
            # Don't change worker state on materialize failures
            raise

    def _register_memory_artifacts(
        self, outputs: dict[str, Any], memory_store: MemoryArtifactStore
    ) -> None:
        """Register any mem:// artifacts from outputs into the memory store."""
        from bioimage_mcp.artifacts.models import ArtifactRef

        for value in outputs.values():
            if isinstance(value, dict) and value.get("uri", "").startswith("mem://"):
                # Convert output dict to ArtifactRef and register
                try:
                    ref = ArtifactRef(**value)
                    memory_store.register(ref)
                    logger.debug(
                        "Registered memory artifact: ref_id=%s uri=%s",
                        ref.ref_id,
                        ref.uri,
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Failed to register memory artifact %s: %s",
                        value.get("ref_id"),
                        e,
                    )

    def is_alive(self) -> bool:
        """Check if worker process is still running.

        T055: Process health check - polls subprocess returncode.
        If process has terminated, marks state as TERMINATED.
        """
        if self._process is None:
            return False

        # T055: Poll subprocess returncode to detect crashes
        returncode = self._process.poll()
        if returncode is not None:
            # Process has terminated
            with self._lock:
                if self.state != WorkerState.TERMINATED:
                    # T057: Mark worker as terminated on crash detection
                    self.state = WorkerState.TERMINATED
                    logger.warning(
                        "Worker terminated with exit code %s: session=%s env=%s pid=%s",
                        returncode,
                        self.session_id,
                        self.env_id,
                        self.process_id,
                    )
            return False

        return True

    def get_stderr_lines(self) -> list[str]:
        """Get captured stderr lines (non-blocking)."""
        lines = []
        try:
            while True:
                lines.append(self._stderr_lines.get_nowait())
        except Empty:
            pass
        return lines

    def shutdown(self, graceful: bool = True, wait_timeout: float = 30.0) -> None:
        """Terminate the worker process.

        Args:
            graceful: If True, send shutdown request and wait for completion;
                otherwise kill immediately
            wait_timeout: Maximum time to wait for graceful shutdown (default: 30 seconds)
        """
        if not self.is_alive():
            logger.debug(
                "Worker already terminated: session=%s env=%s", self.session_id, self.env_id
            )
            return

        if graceful:
            # T072: Wait for in-flight operations to complete
            import time

            start = time.time()
            while self.state == WorkerState.BUSY and time.time() - start < wait_timeout:
                time.sleep(0.1)

            if self.state == WorkerState.BUSY:
                logger.warning(
                    "Worker still busy after %s seconds, forcing shutdown: session=%s env=%s",
                    wait_timeout,
                    self.session_id,
                    self.env_id,
                )

            try:
                ordinal = self._get_next_ordinal()
                shutdown_req = ShutdownRequest(command="shutdown", graceful=True, ordinal=ordinal)
                req_line = encode_message(shutdown_req)

                assert self._process.stdin is not None
                self._process.stdin.write(req_line)
                self._process.stdin.flush()

                # Wait for shutdown ack (with timeout)
                assert self._process.stdout is not None
                self._process.stdout.readline()  # Read shutdown_ack

                self._process.wait(timeout=5)
                logger.info(
                    "Worker shutdown gracefully: session=%s env=%s pid=%s",
                    self.session_id,
                    self.env_id,
                    self.process_id,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Graceful shutdown failed for %s/%s, forcing: %s",
                    self.session_id,
                    self.env_id,
                    e,
                )
                self._process.kill()
                self._process.wait()
        else:
            self._process.kill()
            self._process.wait()
            logger.info(
                "Worker killed: session=%s env=%s pid=%s",
                self.session_id,
                self.env_id,
                self.process_id,
            )

        self.state = WorkerState.TERMINATED


class WorkerSession(BaseModel):
    session_id: str
    env_id: str
    process_id: int
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    active_artifacts: list[str] = Field(default_factory=list)  # ref_ids in worker memory


class PersistentWorkerManager:
    """Manages persistent worker state for per-session, per-env tool execution.

    IMPLEMENTATION STATUS (Spec 012 - US1):
    ========================================
    Phase 2 (Current): True persistent subprocesses
    - Long-lived worker processes per session/env
    - Process reuse for efficient chaining (eliminates conda overhead)
    - NDJSON IPC via persistent stdin/stdout pipes
    - Automatic worker lifecycle management

    This replaces the Phase 1 metadata-only tracking with actual subprocess
    persistence, achieving 5x speedup on warm starts.

    See: specs/012-persistent-worker/plan.md User Story 1 (T019-T029)
    """

    def __init__(
        self, memory_store: MemoryArtifactStore | None = None, max_workers: int = 8
    ) -> None:
        self._workers: dict[tuple[str, str], WorkerProcess] = {}
        self._lock = threading.Lock()
        self._memory_store = memory_store
        self.max_workers = max_workers

    @staticmethod
    def _create_worker_direct(session_id: str, env_id: str, entrypoint: str) -> WorkerProcess:
        """Create a worker directly without registering (for testing).

        Args:
            session_id: Session identifier
            env_id: Environment identifier
            entrypoint: Python script path or module name

        Returns:
            WorkerProcess instance
        """
        return WorkerProcess(session_id=session_id, env_id=env_id, entrypoint=entrypoint)

    def get_worker(self, session_id: str, env_id: str) -> WorkerProcess:
        """Get or spawn a worker for the session/env pair.

        If a worker already exists and is alive, return it.
        Otherwise, spawn a new worker process.

        T057: Crash detection - detects worker death via is_alive() check.
        T059: On crash, invalidates mem:// artifacts owned by the worker.

        Args:
            session_id: Session identifier
            env_id: Environment identifier (e.g., 'bioimage-mcp-base')

        Returns:
            WorkerProcess instance (may be newly spawned or existing)
        """
        key = (session_id, env_id)
        with self._lock:
            # Check if we have an existing worker
            if key in self._workers:
                worker = self._workers[key]
                # T057: Crash detection via is_alive()
                if worker.is_alive():
                    logger.debug(
                        "Reusing worker: session=%s env=%s pid=%s",
                        session_id,
                        env_id,
                        worker.process_id,
                    )
                    return worker
                else:
                    # T057: Worker died - detect crash
                    # T058: Capture stderr logs on crash
                    stderr_lines = worker.get_stderr_lines()
                    if stderr_lines:
                        logger.error(
                            "Worker crash stderr [%s/%s]: %s",
                            session_id,
                            env_id,
                            "\n".join(stderr_lines[-10:]),  # Last 10 lines
                        )

                    logger.warning(
                        "Worker died unexpectedly: session=%s env=%s pid=%s",
                        session_id,
                        env_id,
                        worker.process_id,
                    )

                    # T059: Invalidate mem:// artifacts on crash
                    if self._memory_store:
                        invalidated = self._memory_store.invalidate_worker(session_id, env_id)
                        logger.warning(
                            "Invalidated %d artifacts after worker crash: session=%s env=%s",
                            len(invalidated),
                            session_id,
                            env_id,
                        )

                    # Remove dead worker from registry
                    del self._workers[key]

            # T096: Enforce max worker limit
            # Count currently alive workers
            alive_workers = sum(1 for w in self._workers.values() if w.is_alive())
            if alive_workers >= self.max_workers:
                raise RuntimeError(
                    f"Maximum worker limit reached ({self.max_workers}). "
                    f"Cannot spawn new worker for {session_id}/{env_id}"
                )

            # Spawn new worker
            # Locate the entrypoint script
            # TODO: Make this configurable or detect from manifest
            repo_root = (
                Path(__file__).resolve().parent.parent.parent.parent
            )  # /.../persistent.py -> runtimes -> bioimage_mcp -> src -> /
            entrypoint_script = repo_root / "tools" / "base" / "bioimage_mcp_base" / "entrypoint.py"

            if not entrypoint_script.exists():
                raise RuntimeError(f"Base tool entrypoint not found: {entrypoint_script}")

            worker = WorkerProcess(
                session_id=session_id,
                env_id=env_id,
                entrypoint=str(entrypoint_script),
            )
            self._workers[key] = worker
            logger.info(
                "Worker spawned: session=%s env=%s pid=%s",
                session_id,
                env_id,
                worker.process_id,
            )
            return worker

    def shutdown_worker(self, session_id: str, env_id: str) -> None:
        """Gracefully stop a worker.

        Args:
            session_id: Session identifier
            env_id: Environment identifier
        """
        key = (session_id, env_id)
        with self._lock:
            if key in self._workers:
                worker = self._workers[key]
                worker.shutdown(graceful=True)
                logger.info("Worker shutdown: session=%s env=%s", session_id, env_id)
                del self._workers[key]

    def shutdown_all(self) -> None:
        """Stop all workers (for server shutdown)."""
        with self._lock:
            if self._workers:
                logger.info("Shutting down %d workers", len(self._workers))
                for worker in self._workers.values():
                    try:
                        worker.shutdown(graceful=True)
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Failed to shutdown worker %s: %s", worker.process_id, e)
            self._workers.clear()

    def check_idle_workers(self, session_timeout_seconds: int = 1800) -> list[tuple[str, str]]:
        """Check for idle workers and shut them down (T070-T071).

        Args:
            session_timeout_seconds: Idle timeout in seconds (default: 30 minutes)

        Returns:
            List of (session_id, env_id) tuples for workers that were shut down
        """
        shutdown_workers = []
        with self._lock:
            for key, worker in list(self._workers.items()):
                if worker.get_idle_seconds() > session_timeout_seconds:
                    session_id, env_id = key
                    logger.info(
                        "Shutting down idle worker: session=%s env=%s idle=%.1fs",
                        session_id,
                        env_id,
                        worker.get_idle_seconds(),
                    )
                    try:
                        worker.shutdown(graceful=True)
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            "Failed to shutdown idle worker %s: %s", worker.process_id, e
                        )
                    del self._workers[key]
                    shutdown_workers.append(key)

                    # Invalidate memory artifacts for this worker
                    if self._memory_store:
                        invalidated = self._memory_store.invalidate_worker(session_id, env_id)
                        logger.info(
                            "Invalidated %d artifacts after idle shutdown: session=%s env=%s",
                            len(invalidated),
                            session_id,
                            env_id,
                        )

        return shutdown_workers

    def register_artifact(self, session_id: str, env_id: str, ref_id: str) -> None:
        """Register a new in-memory artifact.

        Args:
            session_id: Session identifier
            env_id: Environment identifier
            ref_id: Artifact reference ID
        """
        key = (session_id, env_id)
        with self._lock:
            if key in self._workers:
                self._workers[key]
                # Track artifact in WorkerSession if we maintain that state
                # For now, delegate to memory store
                if self._memory_store:
                    # Artifact ref will be created by caller and registered in memory store
                    pass

    def get_artifacts(self, session_id: str, env_id: str) -> list[str]:
        """Get all artifact refs for a worker.

        Args:
            session_id: Session identifier
            env_id: Environment identifier

        Returns:
            List of artifact reference IDs
        """
        if self._memory_store:
            refs = self._memory_store.get_by_session(session_id)
            # Filter by env_id
            from bioimage_mcp.artifacts.memory import parse_mem_uri

            result = []
            for ref in refs:
                try:
                    s_id, e_id, _ = parse_mem_uri(ref.uri)
                    if s_id == session_id and e_id == env_id:
                        result.append(ref.ref_id)
                except ValueError:
                    pass
            return result
        return []

    def is_worker_alive(self, session_id: str, env_id: str) -> bool:
        """Check if worker process is still running.

        Args:
            session_id: Session identifier
            env_id: Environment identifier

        Returns:
            True if worker exists and is alive
        """
        key = (session_id, env_id)
        with self._lock:
            if key not in self._workers:
                return False

            worker = self._workers[key]
            return worker.is_alive()

    def handle_worker_crash(self, session_id: str, env_id: str) -> list[str]:
        """Handle worker crash - returns list of invalidated artifact ref_ids.

        Args:
            session_id: Session identifier
            env_id: Environment identifier

        Returns:
            List of invalidated artifact reference IDs
        """
        # Get artifacts that were in the worker (will be implemented in US2)
        artifacts = self.get_artifacts(session_id, env_id)

        logger.warning(
            "Worker crashed: session=%s env=%s invalidated=%d artifacts",
            session_id,
            env_id,
            len(artifacts),
        )

        # Remove worker from registry
        self.shutdown_worker(session_id, env_id)

        # Invalidate in memory store if available
        if self._memory_store:
            self._memory_store.invalidate_worker(session_id, env_id)

        return artifacts

    def evict_artifact(self, ref_id: str) -> None:
        """Evict an artifact from both worker memory and memory store.

        Args:
            ref_id: Artifact reference ID to evict

        Raises:
            ValueError: If artifact is not a memory artifact
            RuntimeError: If eviction fails
        """
        # Get artifact from memory store to determine worker
        if not self._memory_store:
            raise RuntimeError("Memory store not available")

        ref = self._memory_store.get(ref_id)
        if not ref:
            logger.warning("Artifact not found in memory store: ref_id=%s", ref_id)
            return

        # Parse worker info from URI
        from bioimage_mcp.artifacts.memory import parse_mem_uri

        try:
            session_id, env_id, _ = parse_mem_uri(ref.uri)
        except ValueError as e:
            raise ValueError(f"Not a memory artifact: {ref_id}") from e

        # Get the worker
        key = (session_id, env_id)
        with self._lock:
            if key in self._workers:
                worker = self._workers[key]
                if worker.is_alive():
                    # Send evict command to worker
                    try:
                        evict_response = worker.evict(ref_id)
                        if not evict_response.get("ok"):
                            logger.warning(
                                "Worker eviction failed: ref_id=%s error=%s",
                                ref_id,
                                evict_response.get("error"),
                            )
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            "Failed to send evict command to worker: ref_id=%s error=%s",
                            ref_id,
                            e,
                        )

        # Evict from memory store (even if worker eviction failed)
        self._memory_store.evict(ref_id)
