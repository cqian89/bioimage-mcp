"""
MCP session management handlers for BioImage-MCP.
Includes support for session export and replay for reproducibility.
"""

import json
import logging
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from jsonschema import ValidationError, validate

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.errors import (
    environment_missing_error,
    format_error_summary,
    input_missing_error,
    not_found_error,
)
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.schemas import (
    ErrorDetail,
    ExternalInput,
    InputSource,
    InstallOffer,
    ReplayWarning,
    SessionExportRequest,
    SessionExportResponse,
    SessionReplayRequest,
    SessionReplayResponse,
    StepProgress,
    StepProvenance,
    StructuredError,
    WorkflowRecord,
    WorkflowStep,
)
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.bootstrap.env_manager import detect_env_manager
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing MCP sessions, export, and replay."""

    def __init__(
        self,
        config: Config,
        session_manager: SessionManager,
        artifact_store: ArtifactStore,
        execution_service: ExecutionService | None = None,
        discovery_service: DiscoveryService | None = None,
    ) -> None:
        self.config = config
        self.session_manager = session_manager
        self.artifact_store = artifact_store
        self.execution_service = execution_service
        self.discovery_service = discovery_service

    def _function_exists(self, fn_id: str) -> bool:
        """Check if a function exists in the registry."""
        if not self.discovery_service:
            # Fallback to execution service if discovery not available
            if self.execution_service:
                from bioimage_mcp.api.execution import _get_function_metadata

                manifest, fn_def = _get_function_metadata(self.config, fn_id)
                return manifest is not None
            return True  # Cannot verify, assume exists

        # Use discovery service to check registry
        result = self.discovery_service.describe_function(id=fn_id)
        if "error" not in result:
            return True

        # Fall back to manifest inspection for dynamic functions
        from bioimage_mcp.api.execution import _get_function_metadata

        manifest, _fn_def = _get_function_metadata(self.config, fn_id)
        return manifest is not None

    def _env_installed(self, env_name: str) -> bool:
        """Check if a conda environment is installed."""
        detected = detect_env_manager()
        if not detected:
            # No conda-like manager available (common in tests); skip env check.
            return True
        _manager_name, executable, _version = detected
        try:
            return (
                subprocess.run(
                    [
                        executable,
                        "run",
                        "-n",
                        f"bioimage-mcp-{env_name}",
                        "python",
                        "-c",
                        "print('ok')",
                    ],
                    capture_output=True,
                ).returncode
                == 0
            )
        except Exception:
            return False

    def _validate_overrides(
        self,
        params_overrides: dict[str, dict[str, Any]] | None,
        step_overrides: dict[str, dict[str, Any]] | None,
        record: WorkflowRecord,
    ) -> list[ErrorDetail]:
        """Validate parameter and step overrides against tool schemas."""
        errors: list[ErrorDetail] = []
        if not self.discovery_service:
            return errors

        # 1. Validate params_overrides (by fn_id)
        if params_overrides:
            for fn_id, override_params in params_overrides.items():
                result = self.discovery_service.describe_function(id=fn_id)
                if isinstance(result, dict) and "error" in result:
                    continue

                # Result is likely a FunctionDescriptor or a dict
                params_schema = (
                    result.params_schema
                    if hasattr(result, "params_schema")
                    else result.get("params_schema", {})
                )
                try:
                    validate(instance=override_params, schema=params_schema)
                except ValidationError as e:
                    path = (
                        f"/params_overrides/{fn_id}/{'.'.join(str(p) for p in e.path)}"
                        if e.path
                        else f"/params_overrides/{fn_id}"
                    )
                    errors.append(
                        ErrorDetail(
                            path=path,
                            expected=str(e.validator_value),
                            actual=str(e.instance),
                            hint=e.message,
                        )
                    )

        # 2. Validate step_overrides (by step:{idx})
        if step_overrides:
            for step_key, overrides in step_overrides.items():
                if not step_key.startswith("step:"):
                    continue
                try:
                    idx = int(step_key.split(":")[1])
                    if idx < 0 or idx >= len(record.steps):
                        continue
                except (ValueError, IndexError):
                    continue

                step = record.steps[idx]
                override_params = overrides.get("params")
                if not override_params:
                    continue

                result = self.discovery_service.describe_function(id=step.id)
                if isinstance(result, dict) and "error" in result:
                    continue

                params_schema = (
                    result.params_schema
                    if hasattr(result, "params_schema")
                    else result.get("params_schema", {})
                )
                try:
                    validate(instance=override_params, schema=params_schema)
                except ValidationError as e:
                    path = (
                        f"/step_overrides/{step_key}/params/{'.'.join(str(p) for p in e.path)}"
                        if e.path
                        else f"/step_overrides/{step_key}/params"
                    )
                    errors.append(
                        ErrorDetail(
                            path=path,
                            expected=str(e.validator_value),
                            actual=str(e.instance),
                            hint=e.message,
                        )
                    )

        return errors

    def _check_version_mismatches(self, record: WorkflowRecord) -> list[dict]:
        """Check for version mismatches between recorded and current tool versions."""
        mismatches = []
        for step in record.steps:
            if not step.provenance or not step.provenance.lock_hash:
                continue

            current_prov = self.session_manager.get_function_provenance(step.id)
            current_hash = current_prov.get("lock_hash")

            if step.provenance.lock_hash != current_hash:
                mismatches.append(
                    {
                        "id": step.id,
                        "step_index": step.index,
                        "recorded": step.provenance.lock_hash,
                        "current": current_hash,
                    }
                )
        return mismatches

    def export_session(self, request: SessionExportRequest) -> SessionExportResponse:
        """Export session to a reproducible workflow record (T093)."""
        session_id = request.session_id

        # Enforce allowed-roots for dest_path (T118, T117)
        if request.dest_path:
            dest_path = Path(request.dest_path).resolve()
            allowed = False
            for root in self.config.fs_allowlist_write:
                root_path = Path(root).resolve()
                try:
                    if dest_path.is_relative_to(root_path):
                        allowed = True
                        break
                except ValueError:
                    continue
            if not allowed:
                raise ValueError(
                    f"Permission denied: {request.dest_path} is not in allowed write roots"
                )

        # Get canonical steps (T092)
        steps = self.session_manager.store.list_step_attempts(session_id)
        canonical_steps = [
            s
            for s in steps
            if getattr(s, "canonical", False) and s.status in ("success", "succeeded")
        ]

        if not canonical_steps:
            raise ValueError("Cannot export empty session: no canonical successful steps found")

        # Identify external inputs and mark step input sources (T094, T095)
        external_inputs: dict[str, ExternalInput] = {}
        workflow_steps: list[WorkflowStep] = []

        # Track which artifacts are produced by which steps
        artifact_to_step: dict[str, tuple[int, str]] = {}  # ref_id -> (step_index, port_name)

        for idx, step in enumerate(canonical_steps):
            step_inputs: dict[str, InputSource] = {}
            for port, inp in step.inputs.items():
                # Handle different input value types
                if isinstance(inp, str):
                    ref_id = inp
                elif isinstance(inp, dict):
                    ref_id = inp.get("ref_id")
                else:
                    # Skip non-artifact inputs (booleans, numbers, etc.)
                    continue

                if not ref_id:
                    continue

                if ref_id in artifact_to_step:
                    source_idx, source_port = artifact_to_step[ref_id]
                    step_inputs[port] = InputSource(
                        source="step", step_index=source_idx, port=source_port
                    )
                else:
                    # External input
                    if ref_id not in external_inputs:
                        # Find artifact type
                        try:
                            artifact = self.artifact_store.get(ref_id)
                            art_type = artifact.type
                        except KeyError:
                            art_type = "BioImageRef"  # Default

                        external_inputs[ref_id] = ExternalInput(
                            type=art_type, first_seen={"step_index": idx, "port": port}
                        )

                    step_inputs[port] = InputSource(source="external", key=ref_id)

            # Record outputs
            step_outputs: dict[str, ArtifactRef] = {}
            if step.outputs:
                for port, out in step.outputs.items():
                    # Handle both dict and model instances
                    if hasattr(out, "model_dump"):
                        ref_data = out.model_dump(mode="json")
                    else:
                        ref_data = out
                    art_ref = ArtifactRef(**ref_data)
                    step_outputs[port] = art_ref
                    artifact_to_step[art_ref.ref_id] = (idx, port)

            # Get provenance (T113)
            prov_data = {}
            if hasattr(self.session_manager, "get_function_provenance"):
                prov_data = self.session_manager.get_function_provenance(step.fn_id)

            provenance = StepProvenance(
                tool_pack_id=prov_data.get("tool_pack_id", "unknown"),
                tool_pack_version=prov_data.get("tool_pack_version", "0.0.0"),
                lock_hash=prov_data.get("lock_hash"),
            )

            workflow_steps.append(
                WorkflowStep(
                    index=idx,
                    id=step.fn_id,
                    inputs=step_inputs,
                    params=step.params,
                    outputs=step_outputs,
                    status="success",
                    started_at=step.started_at,
                    ended_at=step.ended_at,
                    provenance=provenance,
                    log_ref=ArtifactRef(ref_id=step.log_ref_id, type="LogRef", uri="")
                    if step.log_ref_id
                    else None,
                )
            )

        # Create WorkflowRecord
        record = WorkflowRecord(
            session_id=session_id, external_inputs=external_inputs, steps=workflow_steps
        )

        # Save as artifact
        if request.dest_path:
            out_path = Path(request.dest_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(record.model_dump_json(indent=2))
            store_ref = self.artifact_store.import_file(
                out_path, artifact_type="TableRef", format="workflow-record-json"
            )
            # Override URI to point to user-provided path for better UX
            workflow_ref = store_ref.model_copy(update={"uri": out_path.absolute().as_uri()})
        else:
            store_ref = self.artifact_store.write_native_output(
                record.model_dump(mode="json"), format="workflow-record-json"
            )
            workflow_ref = store_ref

        return SessionExportResponse(session_id=session_id, workflow_ref=workflow_ref)

    def replay_session(self, request: SessionReplayRequest) -> SessionReplayResponse:
        """Replay a workflow from an exported record (T096)."""
        if not self.execution_service:
            raise ValueError("ExecutionService not configured")

        # Load workflow record
        try:
            # ArtifactRef might have uri or we look up by ref_id
            if request.workflow_ref.uri:
                uri = request.workflow_ref.uri
                if uri.startswith("file://"):
                    path = Path(uri[7:])
                    record_data = json.loads(path.read_text())
                else:
                    record_data = self.artifact_store.parse_native_output(
                        request.workflow_ref.ref_id
                    )
            else:
                record_data = self.artifact_store.parse_native_output(request.workflow_ref.ref_id)
        except Exception as e:
            raise ValueError(f"Failed to load workflow record: {e}") from e

        record = WorkflowRecord(**record_data)

        # Initialize tracking (T04-03-02)
        step_progress: list[StepProgress] = []
        replay_warnings: list[ReplayWarning] = []

        # Check for version mismatches (T04-02-01)
        version_mismatches = self._check_version_mismatches(record)
        for mismatch in version_mismatches:
            replay_warnings.append(
                ReplayWarning(
                    level="warning",
                    source="version_check",
                    step_index=mismatch["step_index"],
                    id=mismatch["fn_id"],
                    message=(
                        f"Tool version changed: recorded lock_hash={mismatch['recorded'][:8]}..., "
                        f"current={mismatch['current'][:8]}..."
                    ),
                )
            )

        # Validate overrides against tool schemas (T-override-validation)
        if request.params_overrides or request.step_overrides:
            override_errors = self._validate_overrides(
                params_overrides=request.params_overrides,
                step_overrides=request.step_overrides,
                record=record,
            )
            if override_errors:
                error = StructuredError(
                    code="VALIDATION_FAILED",
                    message=f"Override validation failed: {len(override_errors)} error(s)",
                    details=override_errors,
                )
                return SessionReplayResponse(
                    run_id="none",
                    session_id="none",
                    status="validation_failed",
                    workflow_ref=request.workflow_ref,
                    error=error,
                    human_summary=(
                        f"Replay status: VALIDATION_FAILED\n{format_error_summary(error)}"
                    ),
                )

        # Pre-validate all functions exist and environments are installed (T114)
        for idx, step in enumerate(record.steps):
            fn_id = step.id
            env_name = fn_id.split(".")[0]

            # Check if conda environment is installed
            env_installed = self._env_installed(env_name)

            if not env_installed:
                install_offer = InstallOffer(
                    env_name=env_name,
                    command=f"bioimage-mcp install {env_name}",
                )
                error = environment_missing_error(
                    message=f"Environment '{env_name}' not installed",
                    env_name=env_name,
                    id=fn_id,
                )
                return SessionReplayResponse(
                    run_id="none",
                    session_id="none",
                    status="validation_failed",
                    workflow_ref=request.workflow_ref,
                    error=error,
                    installable=install_offer,
                    human_summary=(
                        f"Replay status: VALIDATION_FAILED\n{format_error_summary(error)}"
                    ),
                )

            # Environment exists, now check if function exists in it
            if not self._function_exists(fn_id):
                error = not_found_error(
                    message=f"Function '{fn_id}' not found in environment '{env_name}'",
                    path=f"/steps/{idx}/id",
                    expected="installed function",
                    hint=(
                        "Function may have been removed or renamed. "
                        "Use 'list' or 'search' to find valid functions."
                    ),
                )
                return SessionReplayResponse(
                    run_id="none",
                    session_id="none",
                    status="validation_failed",
                    workflow_ref=request.workflow_ref,
                    error=error,
                    human_summary=(
                        f"Replay status: VALIDATION_FAILED\n{format_error_summary(error)}"
                    ),
                )

        # Handle dry-run (T04-03-03)
        if request.dry_run:
            for idx, step in enumerate(record.steps):
                step_progress.append(
                    StepProgress(
                        step_index=idx,
                        id=step.id,
                        status="pending",
                        message=f"Step {idx + 1}/{len(record.steps)}: Would run {step.id}",
                    )
                )

            return SessionReplayResponse(
                run_id="dry-run",
                session_id="dry-run",
                status="ready",
                workflow_ref=request.workflow_ref,
                step_progress=step_progress,
                warnings=replay_warnings,
                human_summary=(
                    f"Replay status: READY\n"
                    f"Dry-run successful. Ready to replay {len(record.steps)} steps."
                ),
            )

        # Validate external input bindings (T097, T088)
        mapped_inputs: dict[str, str] = {}
        missing_inputs = []
        for key in record.external_inputs:
            if key not in request.inputs:
                missing_inputs.append(key)
            else:
                mapped_inputs[key] = request.inputs[key]

        if missing_inputs:
            error = input_missing_error(
                message=f"Missing {len(missing_inputs)} required external input(s)",
                missing_inputs=missing_inputs,
            )
            return SessionReplayResponse(
                run_id="none",
                session_id="none",
                status="validation_failed",
                workflow_ref=request.workflow_ref,
                error=error,
                human_summary=(f"Replay status: VALIDATION_FAILED\n{format_error_summary(error)}"),
            )

        # Execute the replayed workflow step by step
        replay_session_id = request.resume_session_id or str(uuid.uuid4())
        # Ensure the replay session exists in the store (T101)
        self.session_manager.ensure_session(replay_session_id)

        start_step_idx = 0
        if request.resume_from_step is not None:
            start_step_idx = request.resume_from_step
        elif request.resume_session_id:
            # Auto-detect last successful step
            existing_steps = self.session_manager.store.list_step_attempts(replay_session_id)
            successful_ordinals = {
                s.ordinal
                for s in existing_steps
                if s.canonical and s.status in ("success", "succeeded")
            }
            if successful_ordinals:
                start_step_idx = max(successful_ordinals) + 1

        step_outputs: dict[tuple[int, str], str] = {}  # (step_index, port_name) -> ref_id

        # Populate outputs from previous steps and progress if resuming
        if start_step_idx > 0:
            existing_steps = self.session_manager.store.list_step_attempts(replay_session_id)
            for s in existing_steps:
                if (
                    s.ordinal < start_step_idx
                    and s.canonical
                    and s.status in ("success", "succeeded")
                ):
                    if s.outputs:
                        for port, out_ref in s.outputs.items():
                            ref_id = (
                                out_ref.get("ref_id")
                                if isinstance(out_ref, dict)
                                else out_ref.ref_id
                            )
                            step_outputs[(s.ordinal, port)] = ref_id

            # Add skipped steps to progress
            for i in range(start_step_idx):
                if i < len(record.steps):
                    step_progress.append(
                        StepProgress(
                            step_index=i,
                            id=record.steps[i].id,
                            status="skipped",
                            message=(
                                f"Step {i + 1}/{len(record.steps)}: Skipped (already completed)"
                            ),
                        )
                    )

        final_outputs: dict[str, ArtifactRef] = {}
        last_result: dict[str, Any] = {
            "status": "success",
            "run_id": "none",
            "session_id": replay_session_id,
        }

        for idx, step in enumerate(record.steps):
            # Skip steps already completed
            if idx < start_step_idx:
                continue

            # 1. Resolve inputs for this step
            inputs = {}
            for port, source in step.inputs.items():
                if source.source == "external":
                    ref_id = mapped_inputs[source.key]
                else:
                    ref_id = step_outputs.get((source.step_index, source.port))
                    if not ref_id:
                        raise ValueError(
                            f"Step {idx} depends on missing output from step {source.step_index}"
                        )

                # Check for ObjectRef reconstruction metadata (T046)
                original_art_ref = None
                if source.source == "step":
                    source_step = record.steps[source.step_index]
                    original_art_ref = source_step.outputs.get(source.port)

                # Build input with available metadata to enable lazy
                # reconstruction in execution service
                resolved_input = {"ref_id": ref_id}
                if source.source == "external":
                    external_input = record.external_inputs.get(source.key)
                    if external_input:
                        resolved_input.update(external_input.model_dump())
                        resolved_input["ref_id"] = ref_id
                if original_art_ref:
                    original_data = original_art_ref.model_dump(exclude_none=True)
                    if source.source == "step":
                        # For step dependencies, we MUST use the new ref_id and uri
                        # produced by the replay. Overwriting with original
                        # would break cache lookup.
                        original_data.pop("ref_id", None)
                        original_data.pop("uri", None)
                    resolved_input.update(original_data)

                if (
                    original_art_ref
                    and original_art_ref.type == "ObjectRef"
                    and not self.execution_service._memory_store.get(ref_id)
                ):
                    # Attempt eager reconstruction
                    python_class = original_art_ref.python_class
                    metadata = original_art_ref.metadata or {}
                    init_params = metadata.get("init_params")

                    if python_class and init_params is not None:
                        logger.info(
                            "Eagerly reconstructing ObjectRef %s (%s)", ref_id, python_class
                        )
                        try:
                            self.execution_service.reconstruct_object(
                                python_class=python_class,
                                init_params=init_params,
                                session_id=replay_session_id,
                                ref_id=ref_id,
                            )
                        except Exception as e:
                            logger.error("Failed eager reconstruction for %s: %s", ref_id, e)

                inputs[port] = resolved_input

            # 2. Resolve parameters
            params = step.params.copy()
            if request.params_overrides and step.id in request.params_overrides:
                params.update(request.params_overrides[step.id])
            if request.step_overrides and f"step:{idx}" in request.step_overrides:
                overrides = request.step_overrides[f"step:{idx}"]
                if "params" in overrides:
                    params.update(overrides["params"])

            step_spec = {"steps": [{"fn_id": step.id, "inputs": inputs, "params": params}]}

            # 3. Update progress (T04-03-02)
            started_at = datetime.now(UTC).isoformat()
            progress = StepProgress(
                step_index=idx,
                id=step.id,
                status="running",
                started_at=started_at,
                message=f"Step {idx + 1}/{len(record.steps)}: Running {step.id}",
            )
            step_progress.append(progress)

            # 4. Execute step
            result = self.execution_service.run_workflow(
                step_spec, session_id=replay_session_id, dry_run=request.dry_run
            )
            last_result = result

            # 5. Integrate with session tracking (T101)
            run_id = result.get("run_id", "none")
            api_status = result.get("status", "failed")
            db_status = "succeeded" if api_status == "success" else api_status

            outputs = result.get("outputs")
            error = result.get("error")
            log_ref_id = (result.get("log_ref") or {}).get("ref_id")

            self.session_manager.store.add_step_attempt(
                session_id=replay_session_id,
                step_id=f"replay-{uuid.uuid4().hex[:8]}",
                ordinal=idx,
                fn_id=step.id,
                inputs=inputs,
                params=params,
                status=cast(Any, db_status),
                started_at=started_at,
                ended_at=datetime.now(UTC).isoformat(),
                run_id=run_id,
                outputs=outputs,
                error=error,
                log_ref_id=log_ref_id,
                canonical=(api_status == "success"),
            )

            # Update the progress entry (T04-03-02)
            step_progress[-1] = step_progress[-1].model_copy(
                update={
                    "status": "success" if api_status == "success" else "failed",
                    "ended_at": datetime.now(UTC).isoformat(),
                    "message": (
                        f"Step {idx + 1}/{len(record.steps)}: "
                        f"{'Completed' if api_status == 'success' else 'Failed'} {step.id}"
                    ),
                }
            )

            # Extract warnings from tool execution result (T04-03-02)
            if "warnings" in result and result["warnings"]:
                for warning_msg in result["warnings"]:
                    replay_warnings.append(
                        ReplayWarning(
                            level="warning",
                            source="tool",
                            step_index=idx,
                            id=step.id,
                            message=warning_msg,
                        )
                    )

            # 6. Record outputs for dependent steps and final response (T04-03-02)
            if api_status in ("success", "succeeded") and "outputs" in result:
                if result.get("outputs"):
                    # Normal execution - use actual outputs
                    for port, out_ref in result["outputs"].items():
                        ref_id = (
                            out_ref.get("ref_id") if isinstance(out_ref, dict) else out_ref.ref_id
                        )
                        step_outputs[(idx, port)] = ref_id

                    final_outputs = {
                        k: ArtifactRef(**(v if isinstance(v, dict) else v.model_dump()))
                        for k, v in result["outputs"].items()
                    }

            # 7. Stop on failure
            if api_status in ("failed", "validation_failed"):
                break

        # Map status to allowed values for SessionReplayResponse
        api_status = last_result.get("status")
        if api_status == "validation_failed":
            resp_status = "validation_failed"
        elif api_status == "success":
            resp_status = "success"
        elif api_status in ("running", "queued"):
            resp_status = "running"
        else:
            resp_status = "failed"

        # On failure, include resume info
        resume_info = None
        if resp_status == "failed":
            resume_info = {
                "resume_session_id": replay_session_id,
                "resume_from_step": len(
                    [p for p in step_progress if p.status in ("success", "skipped")]
                ),
                "hint": "Fix the reported error and call replay again with these resume parameters",
            }

        # Generate human-readable summary
        error_info = last_result.get("error")
        error_obj = (
            StructuredError(**error_info)
            if error_info and isinstance(error_info, dict)
            else error_info
        )

        human_summary = f"Replay status: {resp_status.upper()}\n"
        if resp_status == "success":
            human_summary += f"Successfully replayed {len(record.steps)} steps."
        elif resp_status == "ready":
            human_summary += f"Dry-run successful. Ready to replay {len(record.steps)} steps."
        else:
            completed_count = len([p for p in step_progress if p.status in ("success", "skipped")])
            human_summary += f"Replay stopped after {completed_count} steps.\n"
            if error_obj:
                human_summary += format_error_summary(error_obj)

        return SessionReplayResponse(
            run_id=last_result.get("run_id", "none"),
            session_id=replay_session_id,
            status=cast(Any, resp_status),
            workflow_ref=request.workflow_ref,
            log_ref=ArtifactRef(**last_result["log_ref"]) if last_result.get("log_ref") else None,
            error=error_obj,
            step_progress=step_progress,
            warnings=replay_warnings,
            outputs=final_outputs,
            resume_info=resume_info,
            human_summary=human_summary,
        )
