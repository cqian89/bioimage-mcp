from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.runs.store import RunStore
from bioimage_mcp.runtimes.executor import execute_tool
from bioimage_mcp.runtimes.protocol import validate_workflow_compatibility


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
        self._owns_stores = artifact_store is None and run_store is None
        self._artifact_store = artifact_store or ArtifactStore(config)
        self._run_store = run_store or RunStore(config)

    def close(self) -> None:
        if self._owns_stores:
            self._artifact_store.close()
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

    def run_workflow(self, spec: dict, *, skip_validation: bool = False) -> dict:
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

        work_dir = self._config.artifact_store_root / "work" / "runs"
        work_dir.mkdir(parents=True, exist_ok=True)

        response, log_text, exit_code = execute_step(
            config=self._config,
            fn_id=fn_id,
            params=params,
            inputs=inputs,
            work_dir=work_dir,
            timeout_seconds=timeout_seconds,
        )

        log_ref = self._artifact_store.write_log(log_text or str(response))
        run = self._run_store.create_run(
            workflow_spec=spec,
            inputs=inputs,
            params=params,
            provenance={"fn_id": fn_id},
            log_ref_id=log_ref.ref_id,
        )

        if not response.get("ok"):
            self._run_store.set_status(
                run.run_id, "failed", error=response.get("error") or {"exit_code": exit_code}
            )
            return {"run_id": run.run_id, "status": "failed", "log_ref_id": log_ref.ref_id}

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
                outputs_payload[name] = ref.model_dump()

        # Generate workflow record artifact (T020, T024)
        workflow_record = {
            "schema_version": "0.1",
            "run_id": run.run_id,
            "created_at": run.created_at,
            "workflow_spec": spec,
            "inputs": inputs,
            "params": params,
            "outputs": outputs_payload,
            "provenance": run.provenance,
        }
        workflow_record_ref = self._artifact_store.write_native_output(
            workflow_record,
            format="workflow-record-json",
            metadata={"run_id": run.run_id},
        )
        outputs_payload["workflow_record"] = workflow_record_ref.model_dump()

        self._run_store.set_status(run.run_id, "succeeded", outputs=outputs_payload)
        return {
            "run_id": run.run_id,
            "status": "succeeded",
            "workflow_record_ref_id": workflow_record_ref.ref_id,
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
