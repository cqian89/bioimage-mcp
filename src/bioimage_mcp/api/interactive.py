from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive_summaries import summarize_artifact
from bioimage_mcp.api.schemas import SessionExportRequest, SessionReplayRequest
from bioimage_mcp.api.sessions import SessionService
from bioimage_mcp.artifacts.models import ArtifactRef

from bioimage_mcp.sessions.manager import SessionManager


class InteractiveExecutionService:
    def __init__(
        self,
        session_manager: SessionManager,
        execution: ExecutionService,
    ) -> None:
        self.session_manager = session_manager
        self.execution = execution
        self.session_service = SessionService(
            config=execution._config,
            session_manager=session_manager,
            artifact_store=execution.artifact_store,
            execution_service=execution,
        )

    def call_tool(
        self,
        session_id: str,
        fn_id: str,
        inputs: dict[str, Any],
        params: dict[str, Any],
        ordinal: int | None = None,
        connection_hint: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Execute a tool call within a session step.

        Args:
            session_id: The session ID.
            fn_id: The function ID to call.
            inputs: Input artifact references.
            params: Function parameters.
            ordinal: Optional step ordinal. If None, appends to end.
            connection_hint: Optional client connection hint (e.g. 'stdio', 'sse').
            dry_run: If True, validate inputs only without execution.

        Returns:
            A dictionary containing the execution result, including:
            - session_id
            - step_id
            - run_id (if not dry_run)
            - status
            - outputs (including summaries)
            - hints (if available)
            - error (if any)
            - log_ref (if available)
            - dry_run (if True)
        """
        # Ensure session exists
        self.session_manager.ensure_session(session_id, connection_hint=connection_hint)

        # Calculate ordinal
        if ordinal is None:
            steps = self.session_manager.store.list_step_attempts(session_id)
            if steps:
                ordinal = max(s.ordinal for s in steps) + 1
            else:
                ordinal = 0

        # Create step ID
        step_id = f"step-{uuid.uuid4()}"

        # Construct workflow spec
        spec = {
            "steps": [
                {
                    "fn_id": fn_id,
                    "inputs": inputs,
                    "params": params,
                }
            ],
            # Pass timeout via run_opts if needed, but not exposed in call_tool API yet
            "run_opts": {},
        }

        # Record start time
        started_at = datetime.now(UTC).isoformat()

        # Run workflow
        # ExecutionService.run_workflow returns dict with run_id, status, etc.
        # It handles DB entries for RunStore and ArtifactStore.
        result = self.execution.run_workflow(spec, session_id=session_id, dry_run=dry_run)

        if dry_run and result["status"] == "success":
            return {
                "session_id": session_id,
                "step_id": step_id,
                "status": "success",
                "dry_run": True,
                "outputs": {},
            }

        if result["status"] == "validation_failed":
            return {
                "session_id": session_id,
                "step_id": step_id,
                "status": "validation_failed",
                "dry_run": dry_run,
                "id": fn_id,
                "error": result["error"],
                "outputs": {},
            }

        hints = result.get("hints")

        # Record end time
        ended_at = datetime.now(UTC).isoformat()

        # Retrieve full run details to get outputs and error
        run_status = self.execution.get_run_status(result["run_id"])
        status = run_status["status"]
        outputs = run_status.get("outputs")
        error = run_status.get("error")
        log_ref = run_status.get("log_ref")
        log_ref_id = log_ref["ref_id"] if log_ref else None

        # Determine canonical status
        # Only successful runs become canonical.
        # This allows retries without overwriting a successful history with a failure.
        canonical = status == "success"

        # Store step attempt
        self.session_manager.store.add_step_attempt(
            session_id=session_id,
            step_id=step_id,
            ordinal=ordinal,
            fn_id=fn_id,
            inputs=inputs,
            params=params,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            run_id=result["run_id"],
            outputs=outputs,
            error=error,
            log_ref_id=log_ref_id,
            canonical=canonical,
        )

        # If this attempt is canonical, ensure it's the ONLY canonical one for this ordinal
        if canonical:
            self.session_manager.store.set_canonical(session_id, step_id, ordinal)

        # Generate summaries for outputs
        # The result outputs are ArtifactRef dictionaries.
        # We need to wrap them and add summaries.
        response_outputs = {}
        if outputs:
            for name, out_data in outputs.items():
                # out_data is the serialized ArtifactRef
                ref = ArtifactRef(**out_data)
                summary = summarize_artifact(ref)

                extra = {}
                # Inline content for LogRef (needed for interactive feedback)
                if ref.type == "LogRef":
                    try:
                        # Accessing internal store to fetch content
                        store = self.execution.artifact_store
                        if store:
                            content_bytes = store.get_raw_content(ref.ref_id)
                            extra["content"] = content_bytes.decode("utf-8")
                    except Exception:  # noqa: BLE001
                        pass  # Best effort

                response_outputs[name] = out_data | {"summary": summary} | extra

        response = {
            "session_id": session_id,
            "step_id": step_id,
            "run_id": result["run_id"],
            "status": status,
            "outputs": response_outputs,
        }

        if hints:
            response["hints"] = hints

        if status == "failed":
            response["isError"] = True
            # Ensure error is present if failed
            if not error:
                response["error"] = {"message": "Tool execution failed", "code": "EXECUTION_FAILED"}

        if error:
            response["error"] = error
        if log_ref:
            response["log_ref"] = log_ref

        return response

    def export_session(self, session_id: str, dest_path: str | None = None) -> dict[str, Any]:
        """Export session to a reproducible workflow artifact."""
        request = SessionExportRequest(session_id=session_id, dest_path=dest_path)
        response = self.session_service.export_session(request)

        # Update session status
        self.session_manager.store.update_session_status(session_id, "exported")

        return {
            "session_id": session_id,
            "workflow_ref": response.workflow_ref.model_dump(),
        }

    def replay_session(
        self,
        workflow_ref: dict[str, Any] | Any,
        inputs: dict[str, str],
        params_overrides: dict[str, dict[str, Any]] | None = None,
        step_overrides: dict[str, dict[str, Any]] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Replay a workflow from an exported record."""
        if hasattr(workflow_ref, "model_dump"):
            ref_data = workflow_ref.model_dump(mode="json")
        elif isinstance(workflow_ref, dict):
            ref_data = workflow_ref
        else:
            raise ValueError(f"Invalid workflow_ref type: {type(workflow_ref)}")

        request = SessionReplayRequest(
            workflow_ref=ref_data,
            inputs=inputs,
            params_overrides=params_overrides,
            step_overrides=step_overrides,
            dry_run=dry_run,
        )
        response = self.session_service.replay_session(request)
        return response.model_dump()
