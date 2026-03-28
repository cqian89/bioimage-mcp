from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.errors import execution_error
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive_summaries import summarize_artifact
from bioimage_mcp.api.schemas import SessionExportRequest, SessionReplayRequest
from bioimage_mcp.api.sessions import SessionService
from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.sessions.manager import SessionManager

logger = logging.getLogger(__name__)


class InteractiveExecutionService:
    ASYNC_EARLY_COMPLETION_WAIT_SECONDS = 0.25
    ASYNC_RUN_CREATION_TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        session_manager: SessionManager,
        execution: ExecutionService,
        discovery: DiscoveryService | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.execution = execution
        self.session_service = SessionService(
            config=execution._config,
            session_manager=session_manager,
            artifact_store=execution.artifact_store,
            execution_service=execution,
            discovery_service=discovery,
        )

    @staticmethod
    def _is_non_blocking_interactive(fn_id: str, dry_run: bool) -> bool:
        if dry_run:
            return False
        return fn_id.startswith("micro_sam.sam_annotator.")

    @staticmethod
    def _normalize_hints(hints: dict[str, Any] | None) -> dict[str, Any] | None:
        if not hints:
            return hints
        if isinstance(hints.get("suggested_fix"), dict):
            suggested_fix = dict(hints["suggested_fix"])
            if suggested_fix.get("fn_id"):
                suggested_fix["id"] = suggested_fix["fn_id"]
            suggested_fix.pop("fn_id", None)
            hints = {**hints, "suggested_fix": suggested_fix}
        if isinstance(hints.get("next_steps"), list):
            normalized_next_steps = []
            for step in hints["next_steps"]:
                if isinstance(step, dict):
                    normalized = dict(step)
                    if normalized.get("fn_id"):
                        normalized["id"] = normalized["fn_id"]
                    normalized.pop("fn_id", None)
                    normalized_next_steps.append(normalized)
                else:
                    normalized_next_steps.append(step)
            hints = {**hints, "next_steps": normalized_next_steps}
        return hints

    def _finalize_async_step(
        self,
        *,
        session_id: str,
        step_id: str,
        ordinal: int,
        result: dict[str, Any],
        run_id_hint: str | None,
    ) -> None:
        ended_at = datetime.now(UTC).isoformat()
        run_id = result.get("run_id") or run_id_hint

        if result.get("status") == "validation_failed":
            self.session_manager.store.update_step_attempt(
                step_id,
                status="failed",
                ended_at=ended_at,
                error=result.get("error")
                or execution_error(message="Validation failed").model_dump(),
                canonical=False,
            )
            return

        if not run_id:
            self.session_manager.store.update_step_attempt(
                step_id,
                status="failed",
                ended_at=ended_at,
                error=execution_error(
                    message="Interactive run failed before run_id was created",
                    hint="Check server logs for background execution failures",
                ).model_dump(),
                canonical=False,
            )
            return

        run_status = self.execution.get_run_status(run_id)
        status = run_status.get("status", "failed")
        outputs = run_status.get("outputs") or {}
        error = run_status.get("error")
        log_ref = run_status.get("log_ref")
        log_ref_id = log_ref.get("ref_id") if isinstance(log_ref, dict) else None
        canonical = status == "success"

        self.session_manager.store.update_step_attempt(
            step_id,
            status=status,
            ended_at=ended_at,
            run_id=run_id,
            outputs=outputs,
            error=error,
            log_ref_id=log_ref_id,
            canonical=canonical,
        )
        if canonical:
            self.session_manager.store.set_canonical(session_id, step_id, ordinal)

    def _start_non_blocking_interactive(
        self,
        *,
        session_id: str,
        step_id: str,
        ordinal: int,
        fn_id: str,
        inputs: dict[str, Any],
        params: dict[str, Any],
        spec: dict[str, Any],
        started_at: str,
        dry_run: bool,
        progress_callback: Callable[[str], None] | None,
    ) -> dict[str, Any]:
        run_id_holder: dict[str, str] = {}
        result_holder: dict[str, Any] = {}
        error_holder: dict[str, Any] = {}
        run_created = threading.Event()
        finished = threading.Event()

        self.session_manager.store.add_step_attempt(
            session_id=session_id,
            step_id=step_id,
            ordinal=ordinal,
            fn_id=fn_id,
            inputs=inputs,
            params=params,
            status="running",
            started_at=started_at,
            ended_at=None,
            run_id=None,
            outputs=None,
            error=None,
            log_ref_id=None,
            canonical=False,
        )

        def on_run_created(run_id: str) -> None:
            run_id_holder["run_id"] = run_id
            try:
                self.session_manager.store.update_step_attempt(step_id, run_id=run_id)
            except Exception:  # noqa: BLE001
                logger.exception("Failed updating session step run_id for %s", step_id)
            run_created.set()

        def _run_in_background() -> None:
            try:
                result = self.execution.run_workflow(
                    spec,
                    session_id=session_id,
                    dry_run=dry_run,
                    progress_callback=progress_callback,
                    on_run_created=on_run_created,
                )
                result_holder["result"] = result
                self._finalize_async_step(
                    session_id=session_id,
                    step_id=step_id,
                    ordinal=ordinal,
                    result=result,
                    run_id_hint=run_id_holder.get("run_id"),
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Interactive background run crashed for %s", fn_id)
                error_holder["error"] = exc
                try:
                    self.session_manager.store.update_step_attempt(
                        step_id,
                        status="failed",
                        ended_at=datetime.now(UTC).isoformat(),
                        error=execution_error(
                            message=f"Background execution failed: {exc}",
                            hint="Check server logs for traceback details",
                        ).model_dump(),
                        canonical=False,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Failed updating crashed background step %s", step_id)
            finally:
                finished.set()

        thread = threading.Thread(
            target=_run_in_background, daemon=True, name=f"interactive-{step_id}"
        )
        thread.start()

        if finished.wait(timeout=self.ASYNC_EARLY_COMPLETION_WAIT_SECONDS):
            if error_holder.get("error") is not None:
                error_payload = execution_error(
                    message=f"Background execution failed: {error_holder['error']}",
                    hint="Check server logs for traceback details",
                ).model_dump()
                return {
                    "session_id": session_id,
                    "step_id": step_id,
                    "status": "failed",
                    "run_id": run_id_holder.get("run_id", "none"),
                    "outputs": {},
                    "isError": True,
                    "error": error_payload,
                }

            result = result_holder.get("result")
            if isinstance(result, dict) and result.get("status") == "validation_failed":
                return {
                    "session_id": session_id,
                    "step_id": step_id,
                    "status": "validation_failed",
                    "dry_run": dry_run,
                    "id": fn_id,
                    "error": result.get("error"),
                    "outputs": {},
                }

            run_id = run_id_holder.get("run_id") or (
                result.get("run_id") if isinstance(result, dict) else None
            )
            if run_id:
                run_status = self.execution.get_run_status(run_id)
                if run_status.get("status") in {"success", "failed"}:
                    response = {
                        "session_id": session_id,
                        "step_id": step_id,
                        "run_id": run_id,
                        "status": run_status["status"],
                        "outputs": run_status.get("outputs") or {},
                        "warnings": (result.get("warnings") if isinstance(result, dict) else [])
                        or [],
                    }
                    if run_status.get("error"):
                        response["error"] = run_status["error"]
                        response["isError"] = True
                    if run_status.get("log_ref"):
                        response["log_ref"] = run_status["log_ref"]
                    hints = self._normalize_hints(
                        result.get("hints") if isinstance(result, dict) else None
                    )
                    if hints:
                        response["hints"] = hints
                    return response

        if not run_created.wait(timeout=self.ASYNC_RUN_CREATION_TIMEOUT_SECONDS):
            error_payload = execution_error(
                message="Interactive run did not create a run_id in time",
                hint="The server accepted the request but failed to initialize run tracking",
            ).model_dump()
            return {
                "session_id": session_id,
                "step_id": step_id,
                "status": "failed",
                "run_id": "none",
                "outputs": {},
                "isError": True,
                "error": error_payload,
            }

        run_id = run_id_holder["run_id"]
        return {
            "session_id": session_id,
            "step_id": step_id,
            "run_id": run_id,
            "status": "running",
            "outputs": {},
            "warnings": ["INTERACTIVE_RUNNING_IN_BACKGROUND"],
            "hints": {
                "diagnosis": "Interactive annotation is running in the background.",
                "next_steps": [
                    {
                        "id": "status",
                        "params": {"run_id": run_id},
                    }
                ],
            },
        }

    def call_tool(
        self,
        session_id: str,
        fn_id: str,
        inputs: dict[str, Any],
        params: dict[str, Any],
        ordinal: int | None = None,
        connection_hint: str | None = None,
        timeout_seconds: int | None = None,
        dry_run: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Execute a tool call within a session step.

        Args:
            session_id: The session ID.
            fn_id: The function ID to call.
            inputs: Input artifact references.
            params: Function parameters.
            ordinal: Optional step ordinal. If None, appends to end.
            connection_hint: Optional client connection hint (e.g. 'stdio', 'sse').
            timeout_seconds: Optional timeout in seconds.
            dry_run: If True, validate inputs only without execution.
            progress_callback: Optional callback for progress notifications.

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
                    "id": fn_id,
                    "inputs": inputs,
                    "params": params,
                }
            ],
            "run_opts": {},
        }

        if timeout_seconds is not None:
            spec["run_opts"]["timeout_seconds"] = timeout_seconds

        # Record start time
        started_at = datetime.now(UTC).isoformat()

        if self._is_non_blocking_interactive(fn_id, dry_run):
            return self._start_non_blocking_interactive(
                session_id=session_id,
                step_id=step_id,
                ordinal=ordinal,
                fn_id=fn_id,
                inputs=inputs,
                params=params,
                spec=spec,
                started_at=started_at,
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

        # Run workflow
        # ExecutionService.run_workflow returns dict with run_id, status, etc.
        # It handles DB entries for RunStore and ArtifactStore.
        result = self.execution.run_workflow(
            spec,
            session_id=session_id,
            dry_run=dry_run,
            progress_callback=progress_callback,
        )

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

        hints = self._normalize_hints(result.get("hints"))

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
            "warnings": result.get("warnings", []),
        }

        if hints:
            response["hints"] = hints

        if status == "failed":
            response["isError"] = True
            # Ensure error is present if failed
            if not error:
                response["error"] = execution_error(
                    message="Tool execution failed",
                    hint="Check logs for crash details or environment issues",
                ).model_dump()

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
