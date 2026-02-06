from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from bioimage_mcp.runtimes.executor import _build_command
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
    from bioimage_mcp.storage.memory import MemoryArtifactStore


logger = logging.getLogger(__name__)


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

    HANDSHAKE_TIMEOUT = 30.0

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
        cmd = _build_command(entrypoint, env_id=env_id)
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
        self._stderr_lines: deque[str] = deque(maxlen=100)  # Keep last 100 lines (T115)
        self._stderr_lock = threading.Lock()
        self._stderr_thread = threading.Thread(
            target=self._capture_stderr,
            daemon=True,
            name=f"worker-stderr-{session_id}-{env_id}",
        )
        self._stderr_thread.start()

        # T021: Wait for ready handshake from worker before transitioning to READY
        # The worker MUST send {"command": "ready", "version": "..."} on startup
        # STRICT: Fail if handshake is not received or invalid (spec012 requirement)
        try:
            import threading as _threading

            ready_line = None
            read_error = None

            def read_ready():
                nonlocal ready_line, read_error
                try:
                    assert self._process.stdout is not None
                    ready_line = self._process.stdout.readline()
                except Exception as e:
                    read_error = e

            reader = _threading.Thread(target=read_ready, daemon=True)
            reader.start()
            reader.join(timeout=self.HANDSHAKE_TIMEOUT)  # timeout for ready handshake (spec012)

            # Check for timeout or errors - STRICT mode: kill and raise
            if reader.is_alive():
                # Timeout waiting for ready handshake
                stderr_content = "\n".join(self.get_stderr_lines()[-10:]) or "(no stderr)"
                logger.error(
                    "Timeout waiting for ready handshake after %.1fs (session=%s env=%s). "
                    "Stderr: %s",
                    self.HANDSHAKE_TIMEOUT,
                    session_id,
                    env_id,
                    stderr_content,
                )
                self._process.kill()
                self._process.wait()
                self.state = WorkerState.TERMINATED
                raise RuntimeError(
                    f"Worker failed to send ready handshake within {self.HANDSHAKE_TIMEOUT} "
                    f"seconds (session={session_id}, env={env_id}).\n"
                    f"Stderr output:\n{stderr_content}"
                )

            if read_error:
                stderr_content = "\n".join(self.get_stderr_lines()[-10:]) or "(no stderr)"
                logger.error(
                    "Failed to read ready handshake: %s (session=%s env=%s). Stderr: %s",
                    read_error,
                    session_id,
                    env_id,
                    stderr_content,
                )
                self._process.kill()
                self._process.wait()
                self.state = WorkerState.TERMINATED
                raise RuntimeError(
                    f"Worker ready handshake read failed: {read_error} "
                    f"(session={session_id}, env={env_id}).\n"
                    f"Stderr output:\n{stderr_content}"
                ) from read_error

            if not ready_line:
                stderr_content = "\n".join(self.get_stderr_lines()[-10:]) or "(no stderr)"
                logger.error(
                    "Worker closed stdout before sending ready handshake "
                    "(session=%s env=%s). Stderr: %s",
                    session_id,
                    env_id,
                    stderr_content,
                )
                self._process.kill()
                self._process.wait()
                self.state = WorkerState.TERMINATED
                raise RuntimeError(
                    f"Worker closed stdout without ready handshake "
                    f"(session={session_id}, env={env_id}).\n"
                    f"Stderr output:\n{stderr_content}"
                )

            # Successfully read a line - check if it's a valid ready handshake
            ready_msg = decode_message(ready_line)
            if ready_msg.get("command") != "ready":
                stderr_content = "\n".join(self.get_stderr_lines()[-10:]) or "(no stderr)"
                logger.error(
                    "Expected ready handshake, got: %s (session=%s env=%s). Stderr: %s",
                    ready_msg.get("command"),
                    session_id,
                    env_id,
                    stderr_content,
                )
                self._process.kill()
                self._process.wait()
                self.state = WorkerState.TERMINATED
                raise RuntimeError(
                    f"Worker sent invalid handshake: expected 'ready', "
                    f"got '{ready_msg.get('command')}' "
                    f"(session={session_id}, env={env_id}).\n"
                    f"Stderr output:\n{stderr_content}"
                )

            # Valid ready handshake received
            logger.info(
                "Received ready handshake: version=%s (session=%s env=%s)",
                ready_msg.get("version"),
                session_id,
                env_id,
            )
            # T069: Reset idle timer after successful ready handshake
            self._last_activity_at = datetime.now(UTC)

        except RuntimeError:
            # Re-raise RuntimeError (our handshake failures)
            raise
        except Exception as e:
            stderr_content = "\n".join(self.get_stderr_lines()[-10:]) or "(no stderr)"
            logger.error(
                "Unexpected error during ready handshake: %s (session=%s env=%s). Stderr: %s",
                e,
                session_id,
                env_id,
                stderr_content,
            )
            self._process.kill()
            self._process.wait()
            self.state = WorkerState.TERMINATED
            raise RuntimeError(
                f"Worker ready handshake failed unexpectedly: {e} "
                f"(session={session_id}, env={env_id}).\n"
                f"Stderr output:\n{stderr_content}"
            ) from e

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
                    with self._stderr_lock:
                        self._stderr_lines.append(line)
                    logger.debug("Worker stderr [%s/%s]: %s", self.session_id, self.env_id, line)
        except Exception as e:  # noqa: BLE001
            logger.warning("Stderr capture failed for %s/%s: %s", self.session_id, self.env_id, e)

    def _get_next_ordinal(self) -> int:
        """Thread-safe ordinal counter for request correlation."""
        with self._lock:
            self._ordinal_counter += 1
            return self._ordinal_counter

    def _update_activity_unsafe(self) -> None:
        """Update last activity timestamp without acquiring lock (T069).

        MUST be called while holding self._lock.
        """
        self._last_activity_at = datetime.now(UTC)

    def _update_activity(self) -> None:
        """Update last activity timestamp (T069)."""
        with self._lock:
            self._update_activity_unsafe()

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
                id=request.get("id") or request.get("fn_id", ""),
                inputs=request.get("inputs", {}),
                params=request.get("params", {}),
                work_dir=request.get("work_dir", "."),
                hints=request.get("hints"),
                fs_allowlist_read=request.get("fs_allowlist_read"),
                fs_allowlist_write=request.get("fs_allowlist_write"),
                ordinal=ordinal,
            )

            # Transition to BUSY
            with self._lock:
                self.state = WorkerState.BUSY
                self._update_activity_unsafe()  # T069: Track activity on request start

            try:
                # Send request
                req_line = encode_message(exec_req)
                assert self._process.stdin is not None
                self._process.stdin.write(req_line)
                self._process.stdin.flush()

                logger.debug(
                    "Sent execute request: session=%s env=%s ordinal=%s id=%s",
                    self.session_id,
                    self.env_id,
                    ordinal,
                    exec_req.id,
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
                        # Communication error - kill worker
                        logger.error(
                            "Worker read error (session=%s env=%s ordinal=%s): %s",
                            self.session_id,
                            self.env_id,
                            ordinal,
                            error,
                        )
                        self._process.kill()
                        self._process.wait()
                        with self._lock:
                            self.state = WorkerState.TERMINATED
                        raise error

                    if not response_line:
                        # Unexpected EOF - kill worker
                        logger.error(
                            "Worker closed stdout without response (session=%s env=%s ordinal=%s)",
                            self.session_id,
                            self.env_id,
                            ordinal,
                        )
                        self._process.kill()
                        self._process.wait()
                        with self._lock:
                            self.state = WorkerState.TERMINATED
                        raise RuntimeError("Worker closed stdout without response")
                else:
                    try:
                        response_line = self._process.stdout.readline()
                    except Exception as e:
                        # Communication error - kill worker
                        logger.error(
                            "Worker read error (session=%s env=%s ordinal=%s): %s",
                            self.session_id,
                            self.env_id,
                            ordinal,
                            e,
                        )
                        self._process.kill()
                        self._process.wait()
                        with self._lock:
                            self.state = WorkerState.TERMINATED
                        raise

                    if not response_line:
                        # Unexpected EOF - kill worker
                        logger.error(
                            "Worker closed stdout without response (session=%s env=%s ordinal=%s)",
                            self.session_id,
                            self.env_id,
                            ordinal,
                        )
                        self._process.kill()
                        self._process.wait()
                        with self._lock:
                            self.state = WorkerState.TERMINATED
                        raise RuntimeError("Worker closed stdout without response")

                try:
                    response_dict = decode_message(response_line)
                except Exception as e:
                    # T057: Protocol violation (e.g. junk stdout) - kill worker
                    logger.error(
                        "Worker protocol violation (session=%s env=%s ordinal=%s): %s. Stdout: %r",
                        self.session_id,
                        self.env_id,
                        ordinal,
                        e,
                        response_line,
                    )
                    self._process.kill()
                    self._process.wait()
                    with self._lock:
                        self.state = WorkerState.TERMINATED
                    raise RuntimeError(f"Worker protocol violation: {e}") from e

                # Append stderr to log for error responses (T111)
                if not response_dict.get("ok", True):
                    stderr_lines = self.get_stderr_lines()
                    if stderr_lines:
                        existing_log = response_dict.get("log", "")
                        stderr_content = "\n".join(stderr_lines)
                        response_dict["log"] = (
                            f"{existing_log}\n--- stderr ---\n{stderr_content}"
                            if existing_log
                            else f"--- stderr ---\n{stderr_content}"
                        )

                # Validate response
                if response_dict.get("command") != "execute_result":
                    self._process.kill()
                    self._process.wait()
                    with self._lock:
                        self.state = WorkerState.TERMINATED
                    raise RuntimeError(
                        f"Expected execute_result, got {response_dict.get('command')}"
                    )

                if response_dict.get("ordinal") != ordinal:
                    self._process.kill()
                    self._process.wait()
                    with self._lock:
                        self.state = WorkerState.TERMINATED
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
                        self._update_activity_unsafe()  # T069: Track activity on completion

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
            try:
                response_line = self._process.stdout.readline()
            except Exception as e:
                # Communication error - kill worker
                logger.error(
                    "Worker read error (session=%s env=%s ordinal=%s): %s",
                    self.session_id,
                    self.env_id,
                    ordinal,
                    e,
                )
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise

            if not response_line:
                # Unexpected EOF - kill worker
                logger.error(
                    "Worker closed stdout without response (session=%s env=%s ordinal=%s)",
                    self.session_id,
                    self.env_id,
                    ordinal,
                )
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise RuntimeError("Worker closed stdout without response")

            try:
                response_dict = decode_message(response_line)
            except Exception as e:
                # T057: Protocol violation (e.g. junk stdout) - kill worker
                logger.error(
                    "Worker protocol violation (session=%s env=%s ordinal=%s): %s. Stdout: %r",
                    self.session_id,
                    self.env_id,
                    ordinal,
                    e,
                    response_line,
                )
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise RuntimeError(f"Worker protocol violation: {e}") from e

            # Validate response
            if response_dict.get("command") != "evict_result":
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise RuntimeError(f"Expected evict_result, got {response_dict.get('command')}")

            if response_dict.get("ordinal") != ordinal:
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
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
            try:
                response_line = self._process.stdout.readline()
            except Exception as e:
                # Communication error - kill worker
                logger.error(
                    "Worker read error (session=%s env=%s ordinal=%s): %s",
                    self.session_id,
                    self.env_id,
                    ordinal,
                    e,
                )
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise

            if not response_line:
                # Unexpected EOF - kill worker
                logger.error(
                    "Worker closed stdout without response (session=%s env=%s ordinal=%s)",
                    self.session_id,
                    self.env_id,
                    ordinal,
                )
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise RuntimeError("Worker closed stdout without response")

            try:
                response_dict = decode_message(response_line)
            except Exception as e:
                # T057: Protocol violation (e.g. junk stdout) - kill worker
                logger.error(
                    "Worker protocol violation (session=%s env=%s ordinal=%s): %s. Stdout: %r",
                    self.session_id,
                    self.env_id,
                    ordinal,
                    e,
                    response_line,
                )
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise RuntimeError(f"Worker protocol violation: {e}") from e

            # Validate response
            if response_dict.get("command") != "materialize_result":
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
                raise RuntimeError(
                    f"Expected materialize_result, got {response_dict.get('command')}"
                )

            if response_dict.get("ordinal") != ordinal:
                self._process.kill()
                self._process.wait()
                with self._lock:
                    self.state = WorkerState.TERMINATED
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
        with self._stderr_lock:
            lines = list(self._stderr_lines)
            self._stderr_lines.clear()
            return lines

    def shutdown(self, graceful: bool = True, wait_timeout: float = 30.0) -> None:
        """Terminate the worker process.

        Ensures deterministic convergence to TERMINATED state even if worker is BUSY (SESS-02).

        Args:
            graceful: If True, send shutdown request and wait for completion;
                otherwise kill immediately
            wait_timeout: Maximum time to wait for graceful shutdown (default: 30 seconds)
        """
        if not self.is_alive():
            logger.debug(
                "Worker already terminated: session=%s env=%s", self.session_id, self.env_id
            )
            with self._lock:
                self.state = WorkerState.TERMINATED
            return

        shutdown_method = "graceful"
        if graceful:
            # T072: Wait for in-flight operations to complete
            import time

            start = time.time()
            while self.state == WorkerState.BUSY and time.time() - start < wait_timeout:
                time.sleep(0.1)

            if self.state == WorkerState.BUSY:
                logger.warning(
                    "Worker still BUSY after %.1fs, escalating to force-kill: session=%s env=%s",
                    wait_timeout,
                    self.session_id,
                    self.env_id,
                )
                shutdown_method = "force-kill (busy timeout)"
                self._process.kill()
                self._process.wait()
            else:
                try:
                    ordinal = self._get_next_ordinal()
                    shutdown_req = ShutdownRequest(
                        command="shutdown", graceful=True, ordinal=ordinal
                    )
                    req_line = encode_message(shutdown_req)

                    assert self._process.stdin is not None
                    self._process.stdin.write(req_line)
                    self._process.stdin.flush()

                    # Wait for shutdown ack (with timeout to avoid deadlocks on blocked pipes)
                    assert self._process.stdout is not None

                    # Use a small timeout for the ACK since state is already not BUSY
                    def _read_ack():
                        try:
                            # We use a short read here because the worker should be exiting
                            self._process.stdout.readline()
                        except Exception:
                            pass

                    ack_thread = threading.Thread(target=_read_ack, daemon=True)
                    ack_thread.start()
                    ack_thread.join(timeout=2.0)

                    if ack_thread.is_alive():
                        logger.warning(
                            "Worker failed to ACK shutdown within 2s, force-killing: "
                            "session=%s env=%s",
                            self.session_id,
                            self.env_id,
                        )
                        shutdown_method = "force-kill (no ACK)"
                        self._process.kill()
                        self._process.wait()
                    else:
                        self._process.wait(timeout=5)
                        logger.info(
                            "Worker shutdown gracefully: session=%s env=%s pid=%s",
                            self.session_id,
                            self.env_id,
                            self.process_id,
                        )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Graceful shutdown IPC failed for %s/%s, forcing: %s",
                        self.session_id,
                        self.env_id,
                        e,
                    )
                    shutdown_method = f"force-kill (IPC error: {e})"
                    self._process.kill()
                    self._process.wait()
        else:
            shutdown_method = "immediate-kill"
            self._process.kill()
            self._process.wait()
            logger.info(
                "Worker killed: session=%s env=%s pid=%s",
                self.session_id,
                self.env_id,
                self.process_id,
            )

        with self._lock:
            self.state = WorkerState.TERMINATED
        logger.debug(
            "Worker shutdown complete (%s): session=%s env=%s",
            shutdown_method,
            self.session_id,
            self.env_id,
        )


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
        self,
        memory_store: MemoryArtifactStore | None = None,
        max_workers: int = 8,
        worker_wait_timeout: float = 60.0,
        session_timeout_seconds: int = 1800,
        monitor_interval_seconds: float = 2.0,
        manifest_roots: list[Path] | None = None,
    ) -> None:
        self._workers: dict[tuple[str, str], WorkerProcess] = {}
        self._lock = threading.Lock()
        self._worker_available = threading.Condition(
            self._lock
        )  # Condition for worker availability
        self._memory_store = memory_store
        self.max_workers = max_workers
        self.worker_wait_timeout = worker_wait_timeout
        self.session_timeout_seconds = session_timeout_seconds
        self.monitor_interval_seconds = monitor_interval_seconds
        self.manifest_roots = manifest_roots or []

        # Background monitor thread (spec012)
        self._monitor_stop = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_workers,
            daemon=True,
            name="worker-monitor",
        )
        self._monitor_thread.start()
        logger.info(
            "Worker monitor thread started (interval=%.1fs, session_timeout=%ds)",
            monitor_interval_seconds,
            session_timeout_seconds,
        )

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

    def _resolve_entrypoint(self, env_id: str) -> Path:
        """Resolve entrypoint script path for a given environment ID.

        Looks up the tool manifest for the env_id and extracts the entrypoint path.
        Falls back to the base toolkit entrypoint if not found.
        """
        # Fallback to base entrypoint
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        base_entrypoint = repo_root / "tools" / "base" / "bioimage_mcp_base" / "entrypoint.py"

        if not self.manifest_roots:
            return base_entrypoint

        try:
            from bioimage_mcp.registry.loader import load_manifests

            manifests, _ = load_manifests(self.manifest_roots)

            for manifest in manifests:
                if manifest.env_id == env_id:
                    if manifest.entrypoint:
                        # Entrypoint is relative to manifest directory
                        manifest_dir = Path(manifest.manifest_path).parent
                        entrypoint_path = (manifest_dir / manifest.entrypoint).resolve()
                        if entrypoint_path.exists():
                            logger.debug(
                                "Resolved entrypoint for %s from manifest: %s",
                                env_id,
                                entrypoint_path,
                            )
                            return entrypoint_path
                        else:
                            logger.warning(
                                "Entrypoint specified in manifest for %s does not exist: %s",
                                env_id,
                                entrypoint_path,
                            )
                    break
        except Exception as e:  # noqa: BLE001
            logger.error("Error resolving entrypoint from manifest: %s", e)

        # Final fallback
        logger.debug("Using fallback base entrypoint for %s", env_id)
        return base_entrypoint

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

            # T096: Enforce max worker limit with queueing (FR-016)
            # Wait for worker availability if at limit
            import time

            wait_start = time.time()
            while True:
                # Count currently alive workers
                alive_workers = sum(1 for w in self._workers.values() if w.is_alive())
                if alive_workers < self.max_workers:
                    # Space available, proceed to spawn
                    break

                # Check if we've exceeded timeout
                elapsed = time.time() - wait_start
                if elapsed >= self.worker_wait_timeout:
                    raise RuntimeError(
                        f"Maximum worker limit reached ({self.max_workers}). "
                        f"Timed out after {self.worker_wait_timeout:.1f}s "
                        f"waiting for worker availability. "
                        f"Cannot spawn new worker for {session_id}/{env_id}"
                    )

                # Wait for notification that a worker was released
                remaining_timeout = self.worker_wait_timeout - elapsed
                logger.info(
                    "Worker limit reached (%d/%d), waiting up to %.1fs "
                    "for availability: session=%s env=%s",
                    alive_workers,
                    self.max_workers,
                    remaining_timeout,
                    session_id,
                    env_id,
                )
                self._worker_available.wait(timeout=min(remaining_timeout, 1.0))

            # Spawn new worker
            # Resolve entrypoint from manifest (T098)
            entrypoint_script = self._resolve_entrypoint(env_id)

            if not entrypoint_script.exists():
                raise RuntimeError(f"Tool entrypoint not found: {entrypoint_script}")

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
                # Notify waiting threads that a worker slot is available
                self._worker_available.notify_all()

    def shutdown_all(self) -> None:
        """Stop all workers (for server shutdown)."""
        # Stop monitor thread first (without holding lock)
        if hasattr(self, "_monitor_stop"):
            self._monitor_stop.set()

        # Join monitor thread (without holding lock to avoid deadlock)
        if hasattr(self, "_monitor_thread") and self._monitor_thread.is_alive():
            logger.info("Stopping worker monitor thread...")
            self._monitor_thread.join(timeout=5.0)
            if self._monitor_thread.is_alive():
                logger.warning("Worker monitor thread did not stop in time")

        # Now shutdown workers
        with self._lock:
            workers_to_shutdown = list(self._workers.values())

        # Shutdown workers without holding lock (avoid blocking on I/O)
        if workers_to_shutdown:
            logger.info("Shutting down %d workers", len(workers_to_shutdown))
            for worker in workers_to_shutdown:
                try:
                    worker.shutdown(graceful=True)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Failed to shutdown worker %s: %s", worker.process_id, e)

        # Clear workers registry
        with self._lock:
            self._workers.clear()
            # Notify all waiting threads (though server is shutting down)
            self._worker_available.notify_all()

    def check_idle_workers(self, session_timeout_seconds: int = 1800) -> list[tuple[str, str]]:
        """Check for idle workers and shut them down (T070-T071).

        Args:
            session_timeout_seconds: Idle timeout in seconds (default: 30 minutes)

        Returns:
            List of (session_id, env_id) tuples for workers that were shut down
        """
        # Identify idle workers (with lock)
        idle_workers = []
        with self._lock:
            for key, worker in list(self._workers.items()):
                if worker.get_idle_seconds() > session_timeout_seconds:
                    session_id, env_id = key
                    logger.info(
                        "Marking idle worker for shutdown: session=%s env=%s idle=%.1fs",
                        session_id,
                        env_id,
                        worker.get_idle_seconds(),
                    )
                    idle_workers.append((key, worker))

        # Shutdown idle workers WITHOUT holding lock (avoid blocking)
        shutdown_workers = []
        for key, worker in idle_workers:
            session_id, env_id = key
            try:
                worker.shutdown(graceful=True)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to shutdown idle worker %s: %s", worker.process_id, e)

            # Remove from registry and track
            with self._lock:
                if key in self._workers:
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

        # Notify waiting threads if any workers were shut down
        if shutdown_workers:
            with self._lock:
                self._worker_available.notify_all()

        return shutdown_workers

    def _monitor_workers(self) -> None:
        """Background thread to monitor worker health and reap idle workers.

        This thread runs every ~monitor_interval_seconds and:
        1. Detects crashed workers proactively (within 5s as per spec012)
        2. Captures stderr from crashed workers
        3. Invalidates mem:// artifacts via MemoryArtifactStore.invalidate_worker
        4. Removes crashed workers from _workers registry
        5. Reaps idle workers by calling check_idle_workers
        6. Notifies waiting threads when workers are freed

        Related: spec012 US4 - Graceful Worker Crash Recovery
        """

        logger.info("Worker monitor thread started")

        while not self._monitor_stop.is_set():
            try:
                # Sleep first (interruptible)
                if self._monitor_stop.wait(timeout=self.monitor_interval_seconds):
                    # Stop event was set
                    break

                # Check for crashed workers
                crashed_workers = []
                with self._lock:
                    for key, worker in list(self._workers.items()):
                        if not worker.is_alive():
                            crashed_workers.append((key, worker))

                # Handle crashes outside the lock (avoid blocking on I/O)
                for key, worker in crashed_workers:
                    session_id, env_id = key
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
                        "Monitor detected worker crash: session=%s env=%s pid=%s",
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

                    # Remove dead worker from registry (with lock)
                    with self._lock:
                        if key in self._workers:
                            del self._workers[key]
                            # Notify waiting threads that a worker slot is available
                            self._worker_available.notify_all()

                # Reap idle workers
                reaped = self.check_idle_workers(
                    session_timeout_seconds=self.session_timeout_seconds
                )
                if reaped:
                    logger.info("Monitor reaped %d idle workers: %s", len(reaped), reaped)

            except Exception as e:  # noqa: BLE001
                logger.error("Worker monitor thread error: %s", e, exc_info=True)
                # Continue monitoring despite errors
                time.sleep(1.0)

        logger.info("Worker monitor thread stopped")

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
