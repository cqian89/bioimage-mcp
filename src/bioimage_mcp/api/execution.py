import copy
import hashlib
import logging
import platform
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from bioimage_mcp.api.errors import execution_error, not_found_error, validation_error
from bioimage_mcp.api.schemas import ErrorDetail
from bioimage_mcp.artifacts.memory import MemoryArtifactStore, build_mem_uri
from bioimage_mcp.artifacts.metadata import extract_image_metadata
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.dynamic.io_bridge import IOBridge
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.runs.recorder import record_artifact_dimensions
from bioimage_mcp.runs.store import RunStore
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.runtimes.persistent import PersistentWorkerManager
from bioimage_mcp.runtimes.protocol import validate_workflow_compatibility

logger = logging.getLogger(__name__)


CORE_LEGACY_REDIRECTS = {}


def _apply_legacy_redirects(spec: dict) -> tuple[dict, list[str]]:
    """Rewrite legacy fn_ids in workflow spec and collect warnings."""
    new_spec = copy.deepcopy(spec)
    warnings = []
    steps = new_spec.get("steps") or []
    for step in steps:
        fn_id = step.get("fn_id")
        if fn_id in CORE_LEGACY_REDIRECTS:
            new_fn_id = CORE_LEGACY_REDIRECTS[fn_id]
            warnings.append(
                f"DEPRECATED: {fn_id} is deprecated and will be removed in v1.0.0. "
                f"Use {new_fn_id} instead."
            )
            step["fn_id"] = new_fn_id
    return new_spec, warnings


def _extract_env_from_uri(uri: str) -> str | None:
    """Extract environment ID from a memory URI (mem://session/env/ref)."""
    if uri.startswith("mem://"):
        parts = uri[6:].split("/")
        if len(parts) >= 2:
            return parts[1]
    return None


def _needs_cross_env_materialization(artifact_uri: str, source_env: str, target_env: str) -> bool:
    """Check if mem:// artifact needs materialization for cross-env handoff.

    Args:
        artifact_uri: URI of the artifact
        source_env: Source environment ID from artifact
        target_env: Target environment ID where function will execute

    Returns:
        True if artifact is mem:// and environments differ
    """
    if not artifact_uri.startswith("mem://"):
        return False
    return source_env != target_env


def _materialize_memory_artifact_via_worker(
    worker_manager: PersistentWorkerManager,
    session_id: str,
    source_env: str,
    ref_id: str,
    target_format: str = "OME-TIFF",
    dest_path: str | None = None,
) -> str | None:
    """Delegate materialization to the source worker process.

    This satisfies Constitution III by delegating I/O to the tool environment.

    Args:
        worker_manager: Worker manager instance
        session_id: Session ID for worker lookup
        source_env: Source environment ID where artifact lives
        ref_id: Artifact reference ID to materialize
        target_format: Output format (OME-TIFF or OME-Zarr)
        dest_path: Optional destination path

    Returns:
        Path to materialized file, or None if failed
    """
    try:
        # Get the worker that owns the memory artifact
        worker = worker_manager.get_worker(session_id=session_id, env_id=source_env)

        # Send materialize command to worker
        response = worker.materialize(
            ref_id=ref_id, target_format=target_format, dest_path=dest_path
        )

        if response.get("ok"):
            return response.get("path")
        else:
            logger.error(
                "Worker materialization failed: ref_id=%s error=%s",
                ref_id,
                response.get("error"),
            )
            return None

    except Exception as e:  # noqa: BLE001
        logger.error("Failed to materialize via worker: ref_id=%s error=%s", ref_id, e)
        return None


def _get_input_storage_requirements(
    config: Config,
    fn_id: str,
) -> dict[str, list[str]]:
    """Get supported storage types for each input from manifest hints."""
    manifests, _diagnostics = load_manifests(config.tool_manifest_roots)
    for manifest in manifests:
        env_prefix = _env_prefix_from_tool_id(manifest.tool_id)
        for fn in manifest.functions:
            if _matches_fn_id(fn_id, fn.fn_id, env_prefix) and fn.hints:
                return {
                    name: req.supported_storage_types or ["file", "zarr-temp"]
                    for name, req in (fn.hints.inputs or {}).items()
                    if hasattr(req, "supported_storage_types")
                }
    return {}


def _needs_materialization(artifact_ref: dict, supported_types: list[str]) -> bool:
    """Check if artifact needs materialization to a supported storage type."""
    storage_type = artifact_ref.get("storage_type", "file")
    return storage_type == "zarr-temp" and "zarr-temp" not in supported_types


def _env_prefix_from_tool_id(tool_id: str | None) -> str | None:
    if not tool_id:
        return None
    if tool_id.startswith("tools."):
        return tool_id.split(".", 1)[1]
    return tool_id


def _matches_fn_id(fn_id: str, candidate: str, env_prefix: str | None) -> bool:
    if candidate == fn_id:
        return True
    if env_prefix and candidate.startswith(f"{env_prefix}."):
        return candidate[len(env_prefix) + 1 :] == fn_id
    return False


def _get_function_metadata(config: Config, fn_id: str) -> tuple[Any, Any] | tuple[None, None]:
    """Find manifest and function definition (or overlay) for a given fn_id."""
    manifests, _ = load_manifests(config.tool_manifest_roots)
    for manifest in manifests:
        env_prefix = _env_prefix_from_tool_id(manifest.tool_id)
        # 1. Check explicit functions
        for fn in manifest.functions:
            if _matches_fn_id(fn_id, fn.fn_id, env_prefix):
                return manifest, fn

        # 2. Check overlays (for dynamic functions) (T048)
        if fn_id in manifest.function_overlays:
            return manifest, manifest.function_overlays[fn_id]
        if env_prefix:
            prefixed_id = f"{env_prefix}.{fn_id}"
            if prefixed_id in manifest.function_overlays:
                return manifest, manifest.function_overlays[prefixed_id]

        # 3. Check dynamic source prefixes
        if any(
            fn_id.startswith(f"{manifest.tool_id.replace('tools.', '')}.{ds.prefix}.")
            for ds in manifest.dynamic_sources
        ) or (fn_id.startswith("base.") and manifest.tool_id == "tools.base"):
            return manifest, None
    return None, None


def execute_step(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    worker_manager: PersistentWorkerManager | None = None,
    session_id: str = "default-session",
    class_context: dict | None = None,
) -> tuple[dict, str, int]:
    manifest, fn_def = _get_function_metadata(config, fn_id)
    if not manifest:
        raise KeyError(fn_id)

    entrypoint = manifest.entrypoint
    entry_path = Path(entrypoint)
    if not entry_path.is_absolute():
        candidate = manifest.manifest_path.parent / entry_path
        if candidate.exists():
            entrypoint = str(candidate)

    work_dir.mkdir(parents=True, exist_ok=True)

    # Resolve hints from either function definition or overlay (T048)
    hints = None
    if fn_def and hasattr(fn_def, "hints") and fn_def.hints:
        hints = fn_def.hints.model_dump(mode="json")

    request = {
        "fn_id": fn_id,
        "params": params,
        "inputs": inputs,
        "work_dir": str(work_dir),
        "hints": hints,
        "class_context": class_context,
        "fs_allowlist_read": [str(path) for path in config.fs_allowlist_read],
        "fs_allowlist_write": [str(path) for path in config.fs_allowlist_write],
    }

    if worker_manager:
        # Use persistent worker for execution (T016, spec 012)
        worker = worker_manager.get_worker(session_id, manifest.env_id)

        # Send request to persistent worker
        try:
            response = worker.execute(
                request=request,
                memory_store=worker_manager._memory_store,
                timeout_seconds=timeout_seconds,
            )

            # Parse worker response to match expected format
            # WorkerProcess.execute() returns ExecuteResponse dict
            # Need to convert to tuple[dict, str, int] format

            # Extract log from response (if available)
            log_text = response.get("log", "")

            # Extract exit code (worker responses use ok/error, not exit codes)
            exit_code = 0 if response.get("ok") else 1

            return response, log_text, exit_code

        except Exception as e:
            # On worker error, return error response in expected format
            logger.error(
                "Worker execution failed: session=%s env=%s error=%s",
                session_id,
                manifest.env_id,
                e,
            )
            error_response = {
                "ok": False,
                "error": execution_error(
                    message=f"Worker execution failed: {e}",
                    path="",
                    hint="Check tool environment and logs for crash details",
                ).model_dump(),
            }
            return error_response, str(e), 1

    # Fall back to one-shot execution when worker_manager is None
    return execute_tool(
        entrypoint=entrypoint,
        request=request,
        env_id=manifest.env_id,
        timeout_seconds=timeout_seconds,
    )

    raise KeyError(fn_id)


def _get_function_ports(
    config: Config,
    fn_ids: list[str],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Get input/output port definitions for the given function IDs.

    Returns a mapping of fn_id -> {"inputs": [...], "outputs": [...]}
    """
    # print(f"DEBUG: loading manifests from {config.tool_manifest_roots}")
    manifests, _diagnostics = load_manifests(config.tool_manifest_roots)
    result: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for fn_id in fn_ids:
        for manifest in manifests:
            env_prefix = _env_prefix_from_tool_id(manifest.tool_id)
            for fn in manifest.functions:
                if _matches_fn_id(fn_id, fn.fn_id, env_prefix):
                    result[fn_id] = {
                        "inputs": [
                            {
                                "name": inp.name,
                                "artifact_type": inp.artifact_type,
                                "format": inp.format,
                                "required": inp.required,
                            }
                            for inp in (fn.inputs or [])
                        ],
                        "outputs": [
                            {
                                "name": out.name,
                                "artifact_type": out.artifact_type,
                                "format": out.format,
                            }
                            for out in (fn.outputs or [])
                        ],
                    }
                    break
            if fn_id in result:
                break

    return result


def _materialize_zarr_to_file(
    artifact_ref: dict, work_dir: Path, artifact_store: ArtifactStore
) -> dict:
    """Legacy helper for materializing Zarr artifacts to files.

    This is now primarily used in tests as the main materialization logic
    is integrated into ExecutionService.run_workflow.
    """
    storage_type = artifact_ref.get("storage_type", "file")
    if storage_type != "zarr-temp":
        return artifact_ref

    ref_id = artifact_ref.get("ref_id")
    uri = artifact_ref.get("uri")
    if not uri and ref_id:
        try:
            uri = artifact_store.get(ref_id).uri
        except KeyError:
            uri = None

    if not uri:
        raise ValueError("Artifact is missing URI for materialization")

    parsed = urlparse(uri)
    if parsed.scheme not in ("", "file"):
        raise ValueError(f"Unsupported URI scheme for materialization: {parsed.scheme}")

    if parsed.scheme == "file":
        raw_path = unquote(parsed.path)
        if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
            raw_path = raw_path[1:]
        src_path = Path(raw_path)
    else:
        src_path = Path(uri)

    if not src_path.exists():
        raise FileNotFoundError(f"Artifact path does not exist: {src_path}")

    artifact_type = artifact_ref.get("type", "BioImageRef")
    if src_path.is_dir():
        # Core can now materialize directory-backed artifacts (OME-Zarr) (T049)
        materialized_format = artifact_ref.get("format") or "OME-Zarr"
        new_ref = artifact_store.import_directory(
            src_path, artifact_type=artifact_type, format=materialized_format
        )
        return new_ref.model_dump()

    materialized_format = artifact_ref.get("format") or "OME-TIFF"
    new_ref = artifact_store.import_file(
        src_path, artifact_type=artifact_type, format=materialized_format
    )
    return new_ref.model_dump()


class WorkflowValidationError(ValueError):
    """Raised when workflow validation fails before execution."""

    def __init__(self, message: str, errors: list[dict]):
        super().__init__(message)
        self.errors = errors


class ExecutionService:
    def __init__(
        self,
        config: Config,
        *,
        artifact_store: ArtifactStore | None = None,
        run_store: RunStore | None = None,
        memory_store: MemoryArtifactStore | None = None,
        worker_manager: PersistentWorkerManager | None = None,
    ):
        self._config = config
        self._owns_artifact_store = artifact_store is None
        self._owns_run_store = run_store is None
        self._owns_worker_manager = worker_manager is None
        self._artifact_store = artifact_store or ArtifactStore(config)
        self._run_store = run_store or RunStore(config)
        self._memory_store = memory_store or MemoryArtifactStore()
        self._worker_manager = worker_manager or PersistentWorkerManager(
            memory_store=self._memory_store,
            max_workers=config.max_workers,
            session_timeout_seconds=config.session_timeout_seconds,
            manifest_roots=config.tool_manifest_roots,
        )
        self._io_bridge = IOBridge(artifact_store_path=config.artifact_store_root)

    @property
    def artifact_store(self) -> ArtifactStore:
        return self._artifact_store

    def close(self) -> None:
        if self._owns_worker_manager:
            self._worker_manager.shutdown_all()
        if self._owns_artifact_store:
            self._artifact_store.close()
        if self._owns_run_store:
            self._run_store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def validate_workflow(self, spec: dict) -> list[ErrorDetail]:
        """Validate workflow step I/O type compatibility before execution.

        Returns a list of validation errors (empty if workflow is valid).
        """
        # Apply redirects (SC-001)
        spec, _warnings = _apply_legacy_redirects(spec)

        steps = spec.get("steps") or []
        if not steps:
            return []

        # Collect all fn_ids from steps
        fn_ids = [step.get("fn_id", "") for step in steps]

        # Get function port definitions
        function_ports = _get_function_ports(self._config, fn_ids)

        # Validate compatibility
        errors = validate_workflow_compatibility(spec, function_ports)

        return [
            ErrorDetail(
                path=f"/steps/{err.step_index}/inputs/{err.port_name}",
                expected=err.expected_type,
                actual=err.actual_type,
                hint=err.message,
            )
            for err in errors
        ]

    def _get_function_hints(self, fn_id: str) -> dict | None:
        """Load hints for a function from its manifest."""
        manifests, _diagnostics = load_manifests(self._config.tool_manifest_roots)
        for manifest in manifests:
            env_prefix = _env_prefix_from_tool_id(manifest.tool_id)
            for fn in manifest.functions:
                if _matches_fn_id(fn_id, fn.fn_id, env_prefix):
                    return fn.hints.model_dump() if fn.hints else None
        return None

    def _get_target_env(self, fn_id: str) -> str:
        """Find the environment ID for a given function."""
        manifests, _ = load_manifests(self._config.tool_manifest_roots)
        for manifest in manifests:
            env_prefix = _env_prefix_from_tool_id(manifest.tool_id)
            # Check explicit functions
            if any(_matches_fn_id(fn_id, f.fn_id, env_prefix) for f in manifest.functions):
                return manifest.env_id
            # Check dynamic sources
            if any(
                fn_id.startswith(f"{manifest.tool_id.replace('tools.', '')}.{ds.prefix}.")
                for ds in manifest.dynamic_sources
            ):
                return manifest.env_id
            # Check overlays
            if fn_id in manifest.function_overlays:
                return manifest.env_id
            # Special case for 'base' prefix
            if fn_id.startswith("base.") and manifest.tool_id == "tools.base":
                return manifest.env_id
        return "default"

    def reconstruct_object(
        self,
        python_class: str,
        init_params: dict[str, Any],
        session_id: str,
        ref_id: str | None = None,
    ) -> ArtifactRef:
        """Reconstruct an object from its class and init_params (T046).

        This is used during session replay or when an object is evicted from memory.
        It calls the constructor in the appropriate environment.
        """
        # Determine target environment from python_class
        # Heuristic: try to find env via _get_target_env with a guessed fn_id
        # target_env = self._get_target_env(python_class)

        # Execute the reconstruction
        work_dir = (
            self._config.artifact_store_root / "work" / "reconstruct" / (ref_id or uuid.uuid4().hex)
        )
        work_dir.mkdir(parents=True, exist_ok=True)

        # We use a special internal fn_id 'core.reconstruct'
        response, _log, _exit_code = execute_step(
            config=self._config,
            fn_id="core.reconstruct",
            params={},  # init_params passed via class_context
            inputs={},
            work_dir=work_dir,
            timeout_seconds=60,
            worker_manager=self._worker_manager,
            session_id=session_id,
            class_context={
                "python_class": python_class,
                "init_params": init_params,
            },
        )

        if not response.get("ok"):
            error_msg = response.get("error", {}).get("message", "Unknown error")
            raise RuntimeError(f"Reconstruction failed for {python_class}: {error_msg}")

        # The response should contain the new ObjectRef
        outputs = response.get("outputs") or {}
        # Find the ObjectRef in outputs. We expect at least one.
        obj_ref_data = None
        for out in outputs.values():
            if isinstance(out, dict) and out.get("type") == "ObjectRef":
                obj_ref_data = out
                break

        if not obj_ref_data:
            raise RuntimeError(f"Reconstruction of {python_class} did not return an ObjectRef")

        # Update ref_id if requested
        if ref_id:
            obj_ref_data["ref_id"] = ref_id

        # Wrap as ArtifactRef (or specifically ObjectRef if imported)
        from bioimage_mcp.artifacts.models import ObjectRef

        ref = ObjectRef(**obj_ref_data)

        # Ensure it's registered in memory store
        # (execute_step might have already done this via worker_manager)
        if not self._memory_store.get(ref.ref_id):
            self._memory_store.register(ref)

        return ref

    def run_workflow(
        self,
        spec: dict,
        *,
        skip_validation: bool = False,
        session_id: str = "default-session",
        dry_run: bool = False,
    ) -> dict:
        # Apply redirects (SC-001)
        spec, core_warnings = _apply_legacy_redirects(spec)

        steps = spec.get("steps") or []
        if not steps:
            return {
                "session_id": session_id,
                "run_id": "none",
                "status": "validation_failed",
                "id": "none",
                "outputs": {},
                "error": validation_error(
                    message="Workflow must have at least one step",
                    path="/steps",
                    expected="list with at least one step",
                ).model_dump(),
            }

        if len(steps) != 1:
            # For now, still supporting exactly 1 step as per existing logic,
            # but returning structured error instead of raising.
            return {
                "session_id": session_id,
                "run_id": "none",
                "status": "validation_failed",
                "id": steps[0].get("fn_id", "unknown"),
                "outputs": {},
                "error": validation_error(
                    message="v0.0 supports exactly 1 step",
                    path="/steps",
                    expected="exactly 1 step",
                    actual=str(len(steps)),
                ).model_dump(),
            }

        step = steps[0]
        fn_id = step["fn_id"]
        params = step.get("params") or {}
        inputs = step.get("inputs") or {}

        # Validate workflow compatibility before execution (FR-006)
        if not skip_validation:
            validation_errors = self.validate_workflow(spec)
            if validation_errors:
                return {
                    "session_id": session_id,
                    "run_id": "none",
                    "status": "validation_failed",
                    "id": fn_id,
                    "outputs": {},
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": f"Workflow validation failed: {len(validation_errors)} error(s)",
                        "details": [err.model_dump() for err in validation_errors],
                    },
                }

        if dry_run:
            return {
                "session_id": session_id,
                "run_id": "none",
                "status": "success",
                "id": fn_id,
                "outputs": {},
                "dry_run": True,
            }

        run_opts = spec.get("run_opts") or {}
        output_mode = run_opts.get("output_mode", "file")
        session_id = run_opts.get("session_id", session_id)
        timeout_seconds = run_opts.get("timeout_seconds", self._config.worker_timeout_seconds)

        input_metadata: dict[str, dict] = {}
        for name, inp in inputs.items():
            if isinstance(inp, dict) and "ref_id" in inp:
                ref_id = inp["ref_id"]
                try:
                    # Resolve from memory store first (T016)
                    mem_ref = self._memory_store.get(ref_id)
                    if mem_ref:
                        input_metadata[name] = mem_ref.metadata or {}
                    else:
                        ref = self._artifact_store.get(ref_id)
                        input_metadata[name] = ref.metadata or {}
                except KeyError:
                    input_metadata[name] = {}

        # Create the run early so we can use its ID to isolate outputs (FR-009).
        log_ref = self._artifact_store.write_log("workflow started")
        run = self._run_store.create_run(
            workflow_spec=spec,
            inputs=inputs,
            params=params,
            provenance={"fn_id": fn_id},
            log_ref_id=log_ref.ref_id,
        )

        # Record input dimensions in provenance (T028a)
        def _record_input_dims(name: str, val: Any, idx: int | None = None):
            suffix = f"[{idx}]" if idx is not None else ""
            key = f"input.{name}{suffix}"
            if isinstance(val, list):
                for i, item in enumerate(val):
                    _record_input_dims(name, item, i)
                return

            ref_id = None
            if isinstance(val, dict) and "ref_id" in val:
                ref_id = val["ref_id"]
            elif isinstance(val, str) and not val.startswith(("file://", "mem://", "/")):
                ref_id = val

            if ref_id:
                try:
                    # Resolve from memory store first
                    ref = self._memory_store.get(ref_id) or self._artifact_store.get(ref_id)
                    record_artifact_dimensions(run.provenance, key, ref.model_dump())
                except KeyError:
                    pass

        for name, inp in inputs.items():
            _record_input_dims(name, inp)

        work_dir = self._config.artifact_store_root / "work" / "runs" / run.run_id
        work_dir.mkdir(parents=True, exist_ok=True)

        self._run_store.set_status(run.run_id, "running")

        # Get target environment and ports for IOBridge (T024)
        target_env = self._get_target_env(fn_id)
        fn_ports = _get_function_ports(self._config, [fn_id]).get(fn_id, {})

        # Pre-process inputs: convert plain ref_id strings or lists of ref_ids
        # to resolved artifact dicts
        def _resolve_input_ref(val: Any) -> Any:
            if isinstance(val, str) and not val.startswith(("file://", "mem://", "/")):
                # Treat as ref_id string - resolve to full artifact
                mem_ref = self._memory_store.get(val)
                if mem_ref:
                    resolved = mem_ref.model_dump()
                    meta = mem_ref.metadata
                    simulated_path = None
                    if isinstance(meta, dict):
                        simulated_path = meta.get("_simulated_path")
                    elif hasattr(meta, "model_dump"):
                        simulated_path = meta.model_dump().get("_simulated_path")

                    if simulated_path:
                        resolved["uri"] = f"file://{simulated_path}"
                    return resolved
                else:
                    try:
                        ref = self._artifact_store.get(val)
                        return ref.model_dump()
                    except KeyError:
                        return val
            elif isinstance(val, list):
                return [_resolve_input_ref(item) for item in val]
            return val

        for input_name, input_ref in inputs.items():
            inputs[input_name] = _resolve_input_ref(input_ref)

        def _resolve_and_reconstruct(val: Any) -> Any:
            if isinstance(val, list):
                return [_resolve_and_reconstruct(item) for item in val]
            if not isinstance(val, dict) or "ref_id" not in val:
                return val

            ref_id = val["ref_id"]
            mem_ref = self._memory_store.get(ref_id)

            # Check for ObjectRef reconstruction (T046)
            if not mem_ref and val.get("type") == "ObjectRef":
                python_class = val.get("python_class")
                metadata = val.get("metadata") or {}
                init_params = metadata.get("init_params")
                if python_class and init_params is not None:
                    logger.info("Reconstructing missing ObjectRef %s", ref_id)
                    try:
                        self.reconstruct_object(
                            python_class=python_class,
                            init_params=init_params,
                            session_id=session_id,
                            ref_id=ref_id,
                        )
                        # Refresh mem_ref after reconstruction
                        mem_ref = self._memory_store.get(ref_id)
                    except Exception as e:
                        logger.error("Failed to reconstruct %s: %s", ref_id, e)

            if mem_ref:
                resolved = mem_ref.model_dump()
                # Use simulated file path for tool input (T016 Fix)
                # Handle both dict and Pydantic model metadata (T024)
                meta = mem_ref.metadata
                simulated_path = None
                if isinstance(meta, dict):
                    simulated_path = meta.get("_simulated_path")
                elif hasattr(meta, "model_dump"):
                    simulated_path = meta.model_dump().get("_simulated_path")

                if simulated_path:
                    resolved["uri"] = f"file://{simulated_path}"
                    logger.debug(
                        "Resolving mem:// input: %s -> %s",
                        mem_ref.uri,
                        resolved["uri"],
                    )
                resolved.update(val)
                return resolved

            # Resolve from file store
            if "uri" not in val:
                try:
                    ref = self._artifact_store.get(ref_id)
                    resolved = ref.model_dump()
                    resolved.update(val)
                    return resolved
                except KeyError:
                    pass
            return val

        for input_name, input_ref in inputs.items():
            inputs[input_name] = _resolve_and_reconstruct(input_ref)

        storage_requirements = _get_input_storage_requirements(self._config, fn_id)
        materialized_inputs: dict[str, str] = {}
        handoffs: list[dict] = []

        def _process_handoff(input_name: str, val: Any) -> Any:
            if isinstance(val, list):
                return [_process_handoff(input_name, item) for item in val]
            if not isinstance(val, dict) or "ref_id" not in val:
                return val

            ref_id = val["ref_id"]
            try:
                # Use the original artifact from store for handoff check
                artifact = self._memory_store.get(ref_id) or self._artifact_store.get(ref_id)
                if not artifact:
                    return val
            except KeyError:
                return val

            meta = artifact.metadata
            env_id = "unknown"
            if isinstance(meta, dict):
                env_id = meta.get("env_id", "unknown")
            elif hasattr(meta, "env_id"):
                env_id = getattr(meta, "env_id", "unknown")
            elif hasattr(meta, "model_dump"):
                env_id = meta.model_dump().get("env_id", "unknown")

            source_env = _extract_env_from_uri(artifact.uri) or env_id

            # Get target format from port definitions
            target_format = None
            for port in fn_ports.get("inputs", []):
                if port["name"] == input_name:
                    target_format = port.get("format")
                    break

            # Check if handoff is needed via IOBridge
            needs_handoff = self._io_bridge.needs_handoff(
                artifact, source_env, target_env, target_format
            )

            # Also check legacy zarr-temp materialization
            supported = storage_requirements.get(input_name, ["file"])
            legacy_needs_mat = _needs_materialization(val, supported)

            if legacy_needs_mat:
                # Use compatibility helper for legacy zarr-temp materialization
                # (facilitates mocking in tests)
                materialized = _materialize_zarr_to_file(val, work_dir, self._artifact_store)
                if materialized and materialized.get("ref_id") != ref_id:
                    materialized_inputs[input_name] = ref_id
                    return materialized

            if needs_handoff or legacy_needs_mat:
                negotiated_format = self._io_bridge.negotiate_format(artifact, target_format)
                out_path = self._io_bridge.create_materialization_path(
                    session_id, ref_id, negotiated_format
                )
                out_path.parent.mkdir(parents=True, exist_ok=True)

                logger.info(
                    "Automatic handoff: %s (%s) -> %s (%s). Negotiated: %s",
                    source_env,
                    artifact.format,
                    target_env,
                    target_format or "any",
                    negotiated_format,
                )

                # Check if this is a cross-env mem:// artifact (T045, T046)
                if _needs_cross_env_materialization(artifact.uri, source_env, target_env):
                    # Delegate materialization to source worker (Constitution III compliance)
                    logger.info(
                        "Cross-env mem:// artifact detected, delegating to worker: %s -> %s",
                        source_env,
                        target_env,
                    )

                    materialized_path = _materialize_memory_artifact_via_worker(
                        worker_manager=self._worker_manager,
                        session_id=session_id,
                        source_env=source_env,
                        ref_id=ref_id,
                        target_format=negotiated_format,
                        dest_path=str(out_path),
                    )

                    if materialized_path:
                        # Import as new artifact (T049: support directories)
                        p = Path(materialized_path)
                        if p.is_dir():
                            new_ref = self._artifact_store.import_directory(
                                p,
                                artifact_type=artifact.type,
                                format=negotiated_format,
                            )
                        else:
                            new_ref = self._artifact_store.import_file(
                                p,
                                artifact_type=artifact.type,
                                format=negotiated_format,
                            )

                        # Record handoff
                        handoff = self._io_bridge.record_handoff(
                            source_ref_id=ref_id,
                            target_ref_id=new_ref.ref_id,
                            source_env=source_env,
                            target_env=target_env,
                            format=negotiated_format,
                        )
                        handoffs.append(handoff.model_dump(mode="json"))

                        # Update inputs
                        new_ref_data = new_ref.model_dump()
                        new_ref_data["materialized_from"] = ref_id
                        materialized_inputs[input_name] = ref_id
                        return new_ref_data
                    else:
                        logger.error(
                            "Worker materialization failed for %s. Core cannot perform I/O "
                            "(Constitution III). Operation will fail.",
                            ref_id,
                        )
                        return val
            return val

        for input_name, input_ref in inputs.items():
            inputs[input_name] = _process_handoff(input_name, input_ref)

        if materialized_inputs:
            run.provenance["materialized_inputs"] = materialized_inputs
            if handoffs:
                run.provenance["handoffs"] = handoffs
            self._run_store.update_provenance(run.run_id, run.provenance)

        try:
            response, log_text, exit_code = execute_step(
                config=self._config,
                fn_id=fn_id,
                params=params,
                inputs=inputs,
                work_dir=work_dir,
                timeout_seconds=timeout_seconds,
                worker_manager=self._worker_manager,
                session_id=session_id,
            )
        except KeyError as exc:
            error_payload = not_found_error(
                message=f"Function not found: {exc}",
                path="/steps/0/fn_id",
                expected="valid function ID",
                hint="Use 'search' or 'list' to find valid function IDs",
            ).model_dump()
            self._run_store.set_status(run.run_id, "failed", error=error_payload)
            return {
                "session_id": session_id,
                "run_id": run.run_id,
                "status": "failed",
                "id": fn_id,
                "log_ref": log_ref.model_dump(),
                "log_ref_id": log_ref.ref_id,
                "error": error_payload,
            }

        # Propagate tool-level warnings to log (T030)
        tool_warnings = response.get("warnings", [])
        all_warnings = core_warnings + tool_warnings
        if all_warnings:
            warning_prefix = "\n".join(f"WARNING: {w}" for w in all_warnings)
            if log_text:
                log_text = f"{warning_prefix}\n\n{log_text}"
            else:
                log_text = warning_prefix

        log_ref = self._artifact_store.write_log(log_text or str(response))
        run.log_ref_id = log_ref.ref_id
        self._run_store.set_log_ref(run.run_id, log_ref.ref_id)

        if not response.get("ok"):
            error_payload = response.get("error") or {"exit_code": exit_code}
            if not isinstance(error_payload, dict):
                error_payload = {"message": str(error_payload)}
                if exit_code is not None:
                    error_payload.setdefault("exit_code", exit_code)

            # Map error to StructuredError if possible
            if "code" not in error_payload:
                error_payload["code"] = "EXECUTION_FAILED"

            if "details" not in error_payload or not error_payload["details"]:
                error_payload["details"] = [
                    {
                        "path": "",
                        "hint": "Check tool logs for more information",
                    }
                ]

            self._run_store.set_status(run.run_id, "failed", error=error_payload)
            hints = self._get_function_hints(fn_id)
            error_hints = hints.get("error_hints") if hints else {}
            error_response_hints = None
            error_code = error_payload.get("code") or "GENERAL"
            if error_hints or input_metadata:
                selected_hints = error_hints.get(error_code) or error_hints.get("GENERAL", {})
                error_response_hints = {
                    "diagnosis": selected_hints.get("diagnosis"),
                    "suggested_fix": selected_hints.get("suggested_fix"),
                    "related_metadata": input_metadata,
                }
            return {
                "session_id": session_id,
                "run_id": run.run_id,
                "status": "failed",
                "id": fn_id,
                "log_ref": log_ref.model_dump(),
                "log_ref_id": log_ref.ref_id,
                "error": error_payload,
                "hints": error_response_hints,
                "warnings": all_warnings,
            }

        outputs_payload: dict = {}
        outputs = response.get("outputs") or {}

        # Use the already discovered target_env (T024, T016)
        env_id = target_env

        for name, out in outputs.items():
            out_type = out.get("type", "LogRef")
            fmt = out.get("format", "text")
            path = out.get("path")
            content = out.get("content")

            if output_mode == "memory" and out_type in ["BioImageRef", "LabelImageRef"]:
                # Requesting memory artifact (T016)
                # PHASE 1 SIMULATION: mem:// URIs are backed by files, not worker memory.
                # The _simulated_path metadata tracks the actual file location.
                # Phase 2 will replace this with true in-memory storage in persistent workers.
                # See: specs/011-wrapper-consolidation/plan.md
                ref_id = f"mem-{uuid.uuid4().hex[:8]}"
                uri = build_mem_uri(session_id, env_id, ref_id)

                # Extract metadata from the temporary file if available
                meta = out.get("metadata") or {}
                if path:
                    # Keep track of the simulated file path (T016 simulation)
                    meta["_simulated_path"] = str(Path(path).absolute())
                    try:
                        file_meta = extract_image_metadata(Path(path))
                        if file_meta:
                            meta = {**meta, **file_meta}
                    except Exception:
                        pass

                ref = ArtifactRef(
                    ref_id=ref_id,
                    type=out_type,
                    uri=uri,
                    format=fmt,
                    storage_type="memory",
                    mime_type="application/octet-stream",
                    size_bytes=0,
                    created_at=ArtifactRef.now(),
                    metadata=meta,
                    ndim=meta.get("ndim"),
                    dims=meta.get("dims"),
                    physical_pixel_sizes=meta.get("physical_pixel_sizes"),
                )
                self._memory_store.register(ref)
                self._worker_manager.register_artifact(session_id, env_id, ref_id)
                logger.info("Memory output generated: ref_id=%s storage_type=%s", ref_id, "memory")
                outputs_payload[name] = ref.model_dump()
                record_artifact_dimensions(run.provenance, f"output.{name}", outputs_payload[name])
            elif out_type in [
                "ObjectRef",
                "FigureRef",
                "AxesRef",
                "AxesImageRef",
                "GroupByRef",
            ]:
                # Handle ObjectRef and its subclasses (T018-T024)
                # Register in memory store so it can be resolved for next steps
                ref_id = out.get("ref_id")
                uri = out.get("uri")
                from bioimage_mcp.artifacts.models import (
                    AxesImageRef,
                    AxesRef,
                    FigureRef,
                    GroupByRef,
                    ObjectRef,
                )

                type_map = {
                    "ObjectRef": ObjectRef,
                    "FigureRef": FigureRef,
                    "AxesRef": AxesRef,
                    "AxesImageRef": AxesImageRef,
                    "GroupByRef": GroupByRef,
                }
                ref_class = type_map.get(out_type, ObjectRef)

                ref = ref_class(
                    ref_id=ref_id,
                    type=out_type,
                    uri=uri,
                    format=out.get("format", "pickle"),
                    storage_type="memory",
                    created_at=ref_class.now(),
                    metadata=out.get("metadata", {}),
                    python_class=out.get("python_class", "unknown"),
                )
                self._memory_store.register(ref)
                # Also register with worker manager for session tracking
                self._worker_manager.register_artifact(session_id, env_id, ref_id)
                logger.info(
                    "Object output registered: type=%s ref_id=%s uri=%s", out_type, ref_id, uri
                )
                outputs_payload[name] = ref.model_dump()
            elif path:
                p = Path(path)
                out_type = out.get("type", "BioImageRef")
                fmt = out.get("format", "OME-TIFF")
                tool_metadata = out.get("metadata") or {}

                if content is not None:
                    p.write_text(str(content))

                if p.is_dir():
                    ref = self._artifact_store.import_directory(
                        p,
                        artifact_type=out_type,
                        format=fmt,
                        metadata_override=tool_metadata,
                        ref_id=out.get("ref_id"),
                    )
                else:
                    # Pass tool metadata as override to preserve native dimensions (T048)
                    ref = self._artifact_store.import_file(
                        p,
                        artifact_type=out_type,
                        format=fmt,
                        metadata_override=tool_metadata,
                        ref_id=out.get("ref_id"),
                    )

                ref_data = ref.model_dump()

                # Check if path is outside work_dir (user-specified export path)
                # If so, override URI to point to user's original file location (T020)
                try:
                    p_resolved = p.resolve()
                    work_dir_resolved = work_dir.resolve()
                    is_user_specified_path = not p_resolved.is_relative_to(work_dir_resolved)
                except ValueError:
                    is_user_specified_path = True  # Different drives on Windows

                if is_user_specified_path:
                    # User explicitly exported to this path - return their path in URI
                    ref_data["uri"] = p_resolved.as_uri()

                outputs_payload[name] = ref_data
                record_artifact_dimensions(run.provenance, f"output.{name}", ref_data)

        tool_provenance = response.get("provenance") or {}
        if tool_provenance:
            run.provenance.update(tool_provenance)
            self._run_store.update_provenance(run.run_id, run.provenance)

        # Capture tool manifest checksums (T040) and env fingerprint (T039)
        manifests, _diagnostics = load_manifests(self._config.tool_manifest_roots)
        tool_manifests = []
        for manifest in manifests:
            # Only include manifests used in this workflow
            for manifest_fn in manifest.functions:
                if manifest_fn.fn_id == fn_id:
                    manifest_path = manifest.manifest_path
                    try:
                        manifest_content = manifest_path.read_bytes()
                        checksum = hashlib.sha256(manifest_content).hexdigest()
                    except OSError:
                        checksum = "unavailable"
                    tool_manifests.append(
                        {
                            "tool_id": manifest.tool_id,
                            "tool_version": manifest.tool_version,
                            "env_id": manifest.env_id,
                            "manifest_checksum": checksum,
                        }
                    )
                    break

        # Capture environment fingerprint for reproducibility (T039)
        env_fingerprint = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
        }

        # Generate workflow record artifact (T020, T024)
        workflow_record = {
            "schema_version": "0.1",
            "run_id": run.run_id,
            "created_at": run.created_at,
            "workflow_spec": spec,
            "inputs": inputs,
            "params": params,
            "outputs": outputs_payload,
            "log_ref": log_ref.model_dump(),
            "provenance": run.provenance,
            "tool_manifests": tool_manifests,
            "env_fingerprint": env_fingerprint,
        }
        workflow_record_ref = self._artifact_store.write_native_output(
            workflow_record,
            format="workflow-record-json",
            metadata={"run_id": run.run_id},
        )
        outputs_payload["workflow_record"] = workflow_record_ref.model_dump()
        self._run_store.set_native_output_ref(run.run_id, workflow_record_ref.ref_id)

        self._run_store.set_status(run.run_id, "succeeded", outputs=outputs_payload)
        hints = self._get_function_hints(fn_id)
        success_hints = hints.get("success_hints") if hints else None

        return {
            "session_id": session_id,
            "run_id": run.run_id,
            "status": "success",
            "id": fn_id,
            "outputs": outputs_payload,
            "log_ref": log_ref.model_dump(),
            "log_ref_id": log_ref.ref_id,
            "workflow_record_ref_id": workflow_record_ref.ref_id,
            "hints": success_hints,
            "warnings": all_warnings,
        }

    def get_run_status(self, run_id: str) -> dict:
        try:
            run = self._run_store.get(run_id)
        except KeyError:
            return {
                "status": "failed",
                "error": not_found_error(
                    message=f"Run not found: {run_id}",
                    path="/run_id",
                    expected="valid run ID",
                    hint="Ensure the run_id is correct and from a recent execution",
                ).model_dump(),
            }

        log_ref = self._artifact_store.get(run.log_ref_id) if run.log_ref_id else None
        # Map DB status to API status
        api_status = "running"
        if run.status == "succeeded":
            api_status = "success"
        elif run.status == "failed":
            api_status = "failed"

        payload = {
            "run_id": run.run_id,
            "status": api_status,
            "outputs": run.outputs or {},
            "log_ref": log_ref.model_dump() if log_ref else None,
        }
        if run.error:
            payload["error"] = run.error

        # Add progress if available (mocked for now as we don't have real progress yet)
        if api_status == "running":
            payload["progress"] = {"completed": 0, "total": 100}
        elif api_status == "success":
            payload["progress"] = {"completed": 100, "total": 100}

        return payload

    def replay_workflow(
        self,
        native_output_ref_id: str,
        *,
        override_inputs: dict | None = None,
        override_params: dict | None = None,
    ) -> dict:
        """Replay a workflow from a saved NativeOutputRef (T029, T030, T031).

        Accepts a NativeOutputRef (format: workflow-record-json), parses it,
        and starts a new run with equivalent workflow spec.

        Args:
            native_output_ref_id: Reference ID of the workflow-record-json artifact
            override_inputs: Optional dict to override original inputs
            override_params: Optional dict to override original parameters

        Returns:
            dict with run_id, status, and workflow_record_ref_id

        Raises:
            ValueError: If workflow record is invalid or has missing inputs
            KeyError: If referenced artifact not found
        """
        # T028: Parse the workflow record
        record_data = self._artifact_store.parse_native_output(native_output_ref_id)

        # Extract workflow components
        if "workflow_spec" in record_data:
            workflow_spec = record_data["workflow_spec"]
        else:
            # Fallback for new WorkflowRecord schema where steps are at top level
            workflow_spec = {"steps": record_data.get("steps", [])}

        _original_inputs = record_data.get("inputs", {})  # Keep for future input override
        original_params = record_data.get("params", {})
        original_run_id = record_data.get("run_id") or record_data.get("session_id", "unknown")

        # Apply overrides if provided
        # inputs = {**original_inputs, **(override_inputs or {})}  # TODO: use in future
        params = {**original_params, **(override_params or {})}

        # T030: Validate that all required inputs are available
        steps = workflow_spec.get("steps", [])
        for i, step in enumerate(steps):
            step_inputs = step.get("inputs", {})
            for input_name, input_ref in step_inputs.items():
                ref_id = None
                if isinstance(input_ref, dict):
                    if "ref_id" in input_ref:
                        ref_id = input_ref["ref_id"]
                    elif input_ref.get("source") == "external" and "key" in input_ref:
                        ref_id = input_ref["key"]
                    elif input_ref.get("source") == "step":
                        source_idx = input_ref.get("step_index")
                        port = input_ref.get("port")
                        if source_idx is not None and port:
                            try:
                                source_step = steps[source_idx]
                                source_outputs = source_step.get("outputs", {})
                                out_ref = source_outputs.get(port)
                                if isinstance(out_ref, dict):
                                    ref_id = out_ref.get("ref_id")
                            except (IndexError, KeyError):
                                pass

                if ref_id:
                    try:
                        self._artifact_store.get(ref_id)
                    except KeyError as exc:
                        raise ValueError(
                            f"Missing input artifact for replay: step {i} input '{input_name}' "
                            f"references ref_id '{ref_id}' which no longer exists"
                        ) from exc

        # Update step inputs/params with merged values
        replay_spec = copy.deepcopy(workflow_spec)
        if replay_spec.get("steps"):
            for step in replay_spec["steps"]:
                # Merge params
                step_params = step.get("params", {})
                step["params"] = {**step_params, **params}

        # Execute the replayed workflow (iterate over steps)
        last_result = {"status": "succeeded", "run_id": None}

        for step in replay_spec.get("steps", []):
            step_spec = replay_spec.copy()
            # Map 'id' to 'fn_id' for compatibility with run_workflow if using new schema
            single_step = step.copy()
            if "id" in single_step and "fn_id" not in single_step:
                single_step["fn_id"] = single_step["id"]

            step_spec["steps"] = [single_step]

            result = self.run_workflow(step_spec, skip_validation=True)

            # T031: Link replayed run to original run_id in provenance
            if result["status"] in {"succeeded", "running", "queued"}:
                run = self._run_store.get(result["run_id"])
                run.provenance["replayed_from_run_id"] = original_run_id
                run.provenance["original_workflow_record_ref_id"] = native_output_ref_id
                self._run_store.update_provenance(result["run_id"], run.provenance)

            last_result = result

            # Stop on failure
            if result["status"] == "failed":
                break

        return last_result
