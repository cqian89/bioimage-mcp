from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


class FakeExecutionService:
    def __init__(self, run_result: dict, run_status: dict, config: Config | None = None) -> None:
        self._run_result = run_result
        self._run_status = run_status
        self._config = config
        self.artifact_store = None

    def run_workflow(
        self,
        spec: dict,
        *,
        skip_validation: bool = False,
        session_id: str = "default-session",
        dry_run: bool = False,
    ) -> dict:
        self.last_spec = spec
        return self._run_result

    def get_run_status(self, run_id: str) -> dict:
        assert run_id == self._run_result["run_id"]
        return self._run_status

    def validate_workflow(self, spec: dict) -> list[dict]:
        return []


def _make_service(
    tmp_path: Path, execution: FakeExecutionService
) -> tuple[InteractiveExecutionService, SessionStore]:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    store = SessionStore(config)
    manager = SessionManager(store, config)
    execution._config = config
    service = InteractiveExecutionService(manager, execution)
    return service, store


def test_call_tool_returns_hints_on_success(tmp_path: Path) -> None:
    hints = {"next_steps": ["do_next"], "related_metadata": {"fn_id": "fn.test"}}
    execution = FakeExecutionService(
        run_result={"run_id": "run-1", "status": "success", "hints": hints},
        run_status={"status": "success", "outputs": {}},
    )
    service, store = _make_service(tmp_path, execution)

    result = service.call_tool(session_id="sess-1", fn_id="fn.test", inputs={}, params={})

    assert result["status"] == "success"
    assert result["hints"] == hints
    store.close()


def test_call_tool_returns_hints_on_failure(tmp_path: Path) -> None:
    hints = {
        "diagnosis": "bad inputs",
        "suggested_fix": "check inputs",
        "related_metadata": {"fn_id": "fn.test"},
    }
    execution = FakeExecutionService(
        run_result={"run_id": "run-2", "status": "failed", "hints": hints},
        run_status={
            "status": "failed",
            "outputs": {},
            "error": {"message": "boom", "code": "EXECUTION_FAILED"},
        },
    )
    service, store = _make_service(tmp_path, execution)

    result = service.call_tool(session_id="sess-2", fn_id="fn.test", inputs={}, params={})

    assert result["status"] == "failed"
    assert result["hints"] == hints
    assert result["isError"] is True
    store.close()


def test_call_tool_dry_run_success(tmp_path: Path) -> None:
    execution = FakeExecutionService(
        run_result={"run_id": "none", "status": "success", "dry_run": True},
        run_status={"status": "success", "outputs": {}},
    )
    service, store = _make_service(tmp_path, execution)

    result = service.call_tool(
        session_id="sess-3", fn_id="fn.test", inputs={}, params={}, dry_run=True
    )

    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert "run_id" not in result or result["run_id"] == "none"
    store.close()


def test_call_tool_dry_run_validation_failed(tmp_path: Path) -> None:
    error = {"code": "VALIDATION_FAILED", "message": "bad"}
    execution = FakeExecutionService(
        run_result={"run_id": "none", "status": "validation_failed", "error": error},
        run_status={"status": "failed", "outputs": {}},
    )
    service, store = _make_service(tmp_path, execution)

    result = service.call_tool(
        session_id="sess-4", fn_id="fn.test", inputs={}, params={}, dry_run=True
    )

    assert result["status"] == "validation_failed"
    assert result["dry_run"] is True
    assert result["error"] == error
    store.close()
