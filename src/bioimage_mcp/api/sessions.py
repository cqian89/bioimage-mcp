"""
MCP session management handlers for BioImage-MCP.
Includes support for session export and replay for reproducibility.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.schemas import (
    ErrorDetail,
    ExternalInput,
    InputSource,
    SessionExportRequest,
    SessionExportResponse,
    SessionReplayRequest,
    SessionReplayResponse,
    StepProvenance,
    StructuredError,
    WorkflowRecord,
    WorkflowStep,
)
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.artifacts.store import ArtifactStore
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
        result = self.discovery_service.describe_function(fn_id=fn_id)
        return "error" not in result

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
            raise ValueError(f"Failed to load workflow record: {e}")

        record = WorkflowRecord(**record_data)

        # Pre-validate all functions exist (T114)
        missing_functions = []
        for idx, step in enumerate(record.steps):
            if not self._function_exists(step.id):
                missing_functions.append((idx, step.id))

        if missing_functions:
            return SessionReplayResponse(
                run_id="none",
                session_id="none",
                status="validation_failed",
                workflow_ref=request.workflow_ref,
                error=StructuredError(
                    code="VALIDATION_FAILED",
                    message=f"Referenced function(s) not found: {', '.join(fn_id for _, fn_id in missing_functions)}",
                    details=[
                        ErrorDetail(
                            path=f"/steps/{idx}/id",
                            expected="valid function ID",
                            actual=fn_id,
                            hint="Function may have been removed or renamed. Use 'list' or 'search' to find valid functions.",
                        )
                        for idx, fn_id in missing_functions
                    ],
                ),
            )

        # Validate external input bindings (T097, T088)
        mapped_inputs: dict[str, str] = {}
        for key in record.external_inputs:
            if key not in request.inputs:
                raise ValueError(f"Missing external input: {key}")
            mapped_inputs[key] = request.inputs[key]

        # Execute the replayed workflow step by step
        replay_session_id = str(uuid.uuid4())
        # Ensure the replay session exists in the store (T101)
        self.session_manager.ensure_session(replay_session_id)

        step_outputs: dict[tuple[int, str], str] = {}  # (step_index, port_name) -> ref_id
        last_result: dict[str, Any] = {
            "status": "success",
            "run_id": "none",
            "session_id": replay_session_id,
        }

        for idx, step in enumerate(record.steps):
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

                # Build input with available metadata to enable lazy reconstruction in execution service
                resolved_input = {"ref_id": ref_id}
                if original_art_ref:
                    resolved_input.update(original_art_ref.model_dump(exclude_none=True))

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

            # 3. Execute step
            started_at = datetime.now(UTC).isoformat()
            result = self.execution_service.run_workflow(
                step_spec, session_id=replay_session_id, dry_run=request.dry_run
            )
            last_result = result

            # 4. Integrate with session tracking (T101)
            run_id = result.get("run_id", "none")
            api_status = result.get("status", "failed")
            db_status = "succeeded" if api_status == "success" else api_status

            outputs = result.get("outputs")
            error = result.get("error")
            log_ref_id = (result.get("log_ref") or {}).get("ref_id")

            if not request.dry_run:
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

            # 5. Record outputs for dependent steps
            if api_status in ("success", "succeeded") and "outputs" in result:
                if result.get("outputs"):
                    # Normal execution - use actual outputs
                    for port, out_ref in result["outputs"].items():
                        ref_id = (
                            out_ref.get("ref_id") if isinstance(out_ref, dict) else out_ref.ref_id
                        )
                        step_outputs[(idx, port)] = ref_id
                elif request.dry_run and step.outputs:
                    # Dry-run mode - use virtual references from workflow record
                    for port in step.outputs.keys():
                        step_outputs[(idx, port)] = f"dry-run-{idx}-{port}"

            # 6. Stop on failure
            if api_status in ("failed", "validation_failed"):
                break

        # Map status to allowed values for SessionReplayResponse
        if last_result.get("status") == "validation_failed":
            resp_status = "validation_failed"
        elif request.dry_run:
            resp_status = "ready"
        else:
            resp_status = "running"

        return SessionReplayResponse(
            run_id=last_result.get("run_id", "none"),
            session_id=last_result.get("session_id", "none"),
            status=cast(Any, resp_status),
            workflow_ref=request.workflow_ref,
            log_ref=ArtifactRef(**last_result["log_ref"]) if last_result.get("log_ref") else None,
            error=StructuredError(**last_result["error"]) if last_result.get("error") else None,
        )
