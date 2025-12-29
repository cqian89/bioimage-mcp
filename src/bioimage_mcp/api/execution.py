from __future__ import annotations

import copy
import hashlib
import platform
import sys
from pathlib import Path
from typing import Any

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.runs.store import RunStore
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.runtimes.protocol import validate_workflow_compatibility


CORE_LEGACY_REDIRECTS = {
    "base.bioimage_mcp_base.io.convert_to_ome_zarr": "base.wrapper.io.convert_to_ome_zarr",
    "base.bioimage_mcp_base.io.export_ome_tiff": "base.wrapper.io.export_ome_tiff",
    "base.bioimage_mcp_base.transforms.project_sum": "base.wrapper.transform.project_sum",
    "base.bioimage_mcp_base.transforms.project_max": "base.wrapper.transform.project_max",
    "base.bioimage_mcp_base.transforms.flip": "base.wrapper.transform.flip",
    "base.bioimage_mcp_base.transforms.crop": "base.wrapper.transform.crop",
    "base.bioimage_mcp_base.transforms.pad": "base.wrapper.transform.pad",
    "base.bioimage_mcp_base.axis_ops.relabel_axes": "base.wrapper.axis.relabel_axes",
    "base.bioimage_mcp_base.axis_ops.squeeze": "base.wrapper.axis.squeeze",
    "base.bioimage_mcp_base.axis_ops.expand_dims": "base.wrapper.axis.expand_dims",
    "base.bioimage_mcp_base.axis_ops.moveaxis": "base.wrapper.axis.moveaxis",
    "base.bioimage_mcp_base.axis_ops.swap_axes": "base.wrapper.axis.swap_axes",
    "base.bioimage_mcp_base.preprocess.normalize_intensity": "base.wrapper.preprocess.normalize_intensity",
    "base.bioimage_mcp_base.transforms.phasor_from_flim": "base.wrapper.phasor.phasor_from_flim",
    "base.bioimage_mcp_base.preprocess.denoise_image": "base.wrapper.denoise.denoise_image",
    "base.bioimage_mcp_base.transforms.phasor_calibrate": "base.wrapper.phasor.phasor_calibrate",
}


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


def _get_input_storage_requirements(
    config: Config,
    fn_id: str,
) -> dict[str, list[str]]:
    """Get supported storage types for each input from manifest hints."""
    manifests, _diagnostics = load_manifests(config.tool_manifest_roots)
    for manifest in manifests:
        for fn in manifest.functions:
            if fn.fn_id == fn_id and fn.hints:
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


def _materialize_zarr_to_file(
    artifact_ref: dict,
    work_dir: Path,
    artifact_store: ArtifactStore,
) -> dict:
    """Materialize a zarr-temp artifact to OME-TIFF file.

    Returns the new artifact reference with storage_type="file".
    """
    import bioio
    from tifffile import imwrite

    uri = artifact_ref.get("uri", "")
    if uri.startswith("file://"):
        path = Path(uri[7:])
    else:
        path = Path(uri)

    img = bioio.BioImage(str(path))
    data = img.data
    axes = img.dims.order

    ref_id = artifact_ref.get("ref_id", "materialized")
    out_path = work_dir / f"materialized-{ref_id}.ome.tiff"
    imwrite(
        str(out_path),
        data,
        compression="zlib",
        metadata={"axes": axes},
    )

    artifact_type = artifact_ref.get("type", "BioImageRef")
    new_ref = artifact_store.import_file(
        out_path,
        artifact_type=artifact_type,
        format="OME-TIFF",
    )
    result = new_ref.model_dump()
    result["storage_type"] = "file"
    result["materialized_from"] = artifact_ref.get("ref_id")
    return result


def execute_step(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
) -> tuple[dict, str, int]:
    manifests, _diagnostics = load_manifests(config.tool_manifest_roots)

    for manifest in manifests:
        for fn in manifest.functions:
            if fn.fn_id != fn_id:
                continue

            entrypoint = manifest.entrypoint
            entry_path = Path(entrypoint)
            if not entry_path.is_absolute():
                candidate = manifest.manifest_path.parent / entry_path
                if candidate.exists():
                    entrypoint = str(candidate)

            work_dir.mkdir(parents=True, exist_ok=True)
            request = {
                "fn_id": fn_id,
                "params": params,
                "inputs": inputs,
                "work_dir": str(work_dir),
                "fs_allowlist_read": [str(path) for path in config.fs_allowlist_read],
            }
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
            for fn in manifest.functions:
                if fn.fn_id == fn_id:
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

    return result


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
    ):
        self._config = config
        self._owns_artifact_store = artifact_store is None
        self._owns_run_store = run_store is None
        self._artifact_store = artifact_store or ArtifactStore(config)
        self._run_store = run_store or RunStore(config)

    @property
    def artifact_store(self) -> ArtifactStore:
        return self._artifact_store

    def close(self) -> None:
        if self._owns_artifact_store:
            self._artifact_store.close()
        if self._owns_run_store:
            self._run_store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def validate_workflow(self, spec: dict) -> list[dict]:
        """Validate workflow step I/O type compatibility before execution.

        Returns a list of validation errors (empty if workflow is valid).
        Raises WorkflowValidationError if validation fails.
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
            {
                "step_index": err.step_index,
                "port_name": err.port_name,
                "expected_type": err.expected_type,
                "actual_type": err.actual_type,
                "message": err.message,
            }
            for err in errors
        ]

    def _get_function_hints(self, fn_id: str) -> dict | None:
        """Load hints for a function from its manifest."""
        manifests, _diagnostics = load_manifests(self._config.tool_manifest_roots)
        for manifest in manifests:
            for fn in manifest.functions:
                if fn.fn_id == fn_id:
                    return fn.hints.model_dump() if fn.hints else None
        return None

    def run_workflow(self, spec: dict, *, skip_validation: bool = False) -> dict:
        # Apply redirects (SC-001)
        spec, core_warnings = _apply_legacy_redirects(spec)

        steps = spec.get("steps") or []
        if len(steps) != 1:
            raise ValueError("v0.0 supports exactly 1 step")

        # Validate workflow compatibility before execution (FR-006)
        if not skip_validation:
            validation_errors = self.validate_workflow(spec)
            if validation_errors:
                raise WorkflowValidationError(
                    f"Workflow validation failed: {len(validation_errors)} error(s)",
                    validation_errors,
                )

        step = steps[0]
        fn_id = step["fn_id"]
        params = step.get("params") or {}
        inputs = step.get("inputs") or {}
        timeout_seconds = (spec.get("run_opts") or {}).get("timeout_seconds")

        input_metadata: dict[str, dict] = {}
        for name, inp in inputs.items():
            if isinstance(inp, dict) and "ref_id" in inp:
                ref_id = inp["ref_id"]
                try:
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

        work_dir = self._config.artifact_store_root / "work" / "runs" / run.run_id
        work_dir.mkdir(parents=True, exist_ok=True)

        self._run_store.set_status(run.run_id, "running")

        for input_name, input_ref in inputs.items():
            if not isinstance(input_ref, dict):
                continue
            if "ref_id" in input_ref and "uri" not in input_ref:
                try:
                    ref = self._artifact_store.get(input_ref["ref_id"])
                except KeyError:
                    continue
                resolved = ref.model_dump()
                resolved.update(input_ref)
                inputs[input_name] = resolved

        storage_requirements = _get_input_storage_requirements(self._config, fn_id)
        materialized_inputs: dict[str, str] = {}
        for input_name, input_ref in inputs.items():
            if not isinstance(input_ref, dict):
                continue
            if input_name not in storage_requirements:
                continue
            supported = storage_requirements[input_name]
            if _needs_materialization(input_ref, supported):
                new_ref = _materialize_zarr_to_file(input_ref, work_dir, self._artifact_store)
                inputs[input_name] = new_ref
                materialized_inputs[input_name] = input_ref.get("ref_id", "unknown")

        if materialized_inputs:
            run.provenance["materialized_inputs"] = materialized_inputs
            self._run_store.update_provenance(run.run_id, run.provenance)

        try:
            response, log_text, exit_code = execute_step(
                config=self._config,
                fn_id=fn_id,
                params=params,
                inputs=inputs,
                work_dir=work_dir,
                timeout_seconds=timeout_seconds,
            )
        except KeyError as exc:
            error_payload = {"message": f"Function not found: {exc}"}
            self._run_store.set_status(run.run_id, "failed", error=error_payload)
            return {
                "run_id": run.run_id,
                "status": "failed",
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
                "run_id": run.run_id,
                "status": "failed",
                "log_ref_id": log_ref.ref_id,
                "input_metadata": input_metadata,
                "hints": error_response_hints,
            }

        outputs_payload: dict = {}
        outputs = response.get("outputs") or {}
        for name, out in outputs.items():
            out_type = out.get("type", "LogRef")
            fmt = out.get("format", "text")
            path = out.get("path")
            content = out.get("content")
            if path:
                p = Path(path)
                p.parent.mkdir(parents=True, exist_ok=True)
                if content is not None:
                    p.write_text(str(content))
                if p.is_dir():
                    ref = self._artifact_store.import_directory(
                        p, artifact_type=out_type, format=fmt
                    )
                else:
                    ref = self._artifact_store.import_file(p, artifact_type=out_type, format=fmt)

                # Propagate metadata from tool response (FR-007)
                ref_data = ref.model_dump()
                tool_metadata = out.get("metadata")
                if tool_metadata:
                    ref_data["metadata"] = {**ref_data.get("metadata", {}), **tool_metadata}
                outputs_payload[name] = ref_data

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
            "run_id": run.run_id,
            "status": "succeeded",
            "workflow_record_ref_id": workflow_record_ref.ref_id,
            "hints": success_hints,
        }

    def get_run_status(self, run_id: str) -> dict:
        run = self._run_store.get(run_id)
        log_ref = self._artifact_store.get(run.log_ref_id)
        payload = {
            "run_id": run.run_id,
            "status": run.status,
            "outputs": run.outputs or {},
            "log_ref": log_ref.model_dump(),
        }
        if run.error:
            payload["error"] = run.error
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

        # Validate workflow record structure
        if "workflow_spec" not in record_data:
            raise ValueError("Invalid workflow record: missing 'workflow_spec'")

        # Extract workflow components
        workflow_spec = record_data["workflow_spec"]
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
                if isinstance(input_ref, dict) and "ref_id" in input_ref:
                    ref_id = input_ref["ref_id"]
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
            step_spec["steps"] = [step]

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
