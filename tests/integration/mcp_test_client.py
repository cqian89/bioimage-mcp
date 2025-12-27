from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService

MockFn = Callable[[Path, dict, dict], tuple[dict[str, Any], str, int]]


class MockExecutor:
    """Mock executor for tool execution in tests."""

    def __init__(self, mock_registry: dict[str, MockFn]):
        self.mock_registry = dict(mock_registry)

    def execute_step(
        self,
        *,
        fn_id: str,
        work_dir: Path,
        inputs: dict,
        params: dict,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], str, int]:
        if fn_id in self.mock_registry:
            return self.mock_registry[fn_id](work_dir=work_dir, inputs=inputs, params=params)
        return {"ok": True, "outputs": {}}, "Mock execution successful", 0


@contextmanager
def _patch_execute_step(mock_execute_step: Callable[..., tuple[dict[str, Any], str, int]]):
    import bioimage_mcp.api.execution as execution_module

    original = execution_module.execute_step
    execution_module.execute_step = mock_execute_step
    try:
        yield
    finally:
        execution_module.execute_step = original


class MCPTestClient:
    """Test client for simulating MCP tool calling flows."""

    def __init__(
        self,
        *,
        discovery: DiscoveryService,
        execution: ExecutionService,
        mock_executor: MockExecutor | None = None,
    ) -> None:
        self._discovery = discovery
        self._execution = execution
        self._mock_executor = mock_executor
        self._active_fn_ids: set[str] = set()
        self.context: dict[str, Any] = {}

    def list_tools(self, *, limit: int | None = 50, cursor: str | None = None) -> dict[str, Any]:
        return self._discovery.list_tools(limit=limit, cursor=cursor)

    def search_functions(
        self,
        query: str,
        *,
        tags: list[str] | None = None,
        io_in: str | None = None,
        io_out: str | None = None,
        limit: int | None = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self._discovery.search_functions(
            query=query,
            tags=tags,
            io_in=io_in,
            io_out=io_out,
            limit=limit,
            cursor=cursor,
        )

    def activate_functions(self, fn_ids: list[str]) -> dict[str, Any]:
        self._active_fn_ids = set(fn_ids)
        return {"active_fn_ids": sorted(self._active_fn_ids)}

    def describe_function(self, fn_id: str) -> dict[str, Any]:
        return self._discovery.describe_function(fn_id)

    def call_tool(self, fn_id: str, inputs: dict, params: dict) -> dict[str, Any]:
        if self._active_fn_ids and fn_id not in self._active_fn_ids:
            raise ValueError(f"Function not activated: {fn_id}")

        workflow = {"steps": [{"fn_id": fn_id, "inputs": inputs, "params": params}]}

        if self._mock_executor:
            with _patch_execute_step(self._mock_executor.execute_step):
                result = self._execution.run_workflow(workflow, skip_validation=True)
        else:
            result = self._execution.run_workflow(workflow, skip_validation=False)

        if result.get("status") not in {"succeeded", "running", "queued"}:
            return result

        status = self._execution.get_run_status(result["run_id"])
        outputs = status.get("outputs", {})
        self._record_context(fn_id, outputs)

        return {
            "status": status["status"],
            "run_id": status["run_id"],
            "outputs": outputs,
            "log_ref": status.get("log_ref"),
        }

    def _record_context(self, fn_id: str, outputs: dict[str, Any]) -> None:
        self.context[fn_id] = outputs
        self.context["last.outputs"] = outputs

        for name, output in outputs.items():
            self.context[f"{fn_id}.{name}"] = output

        if len(outputs) == 1:
            only_output = next(iter(outputs.values()))
            self.context[f"{fn_id}.output"] = only_output
