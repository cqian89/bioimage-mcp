from __future__ import annotations

import time
from pathlib import Path

from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


class FakeExecutionService:
    def __init__(
        self,
        run_result: dict,
        run_status: dict,
        config: Config | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self._run_result = run_result
        self._run_status = run_status
        self._config = config
        self.artifact_store = None
        self._delay_seconds = delay_seconds

    def run_workflow(
        self,
        spec: dict,
        *,
        skip_validation: bool = False,
        session_id: str = "default-session",
        dry_run: bool = False,
        progress_callback=None,
        on_run_created=None,
    ) -> dict:
        self.last_spec = spec
        if on_run_created and self._run_result.get("run_id"):
            on_run_created(self._run_result["run_id"])
        if self._delay_seconds > 0:
            time.sleep(self._delay_seconds)
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
    hints = {"next_steps": ["do_next"], "related_metadata": {"id": "fn.test"}}
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
        "related_metadata": {"id": "fn.test"},
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


def test_call_tool_passes_timeout_seconds(tmp_path: Path) -> None:
    execution = FakeExecutionService(
        run_result={"run_id": "run-3", "status": "success"},
        run_status={"status": "success", "outputs": {}},
    )
    service, store = _make_service(tmp_path, execution)

    result = service.call_tool(
        session_id="sess-5",
        fn_id="fn.test",
        inputs={},
        params={},
        timeout_seconds=123,
    )

    assert result["status"] == "success"
    assert execution.last_spec["run_opts"]["timeout_seconds"] == 123
    store.close()


def test_call_tool_microsam_annotator_runs_in_background(tmp_path: Path, monkeypatch) -> None:
    execution = FakeExecutionService(
        run_result={
            "run_id": "run-interactive-1",
            "status": "success",
            "warnings": [],
        },
        run_status={"status": "running", "outputs": {}},
        delay_seconds=0.2,
    )
    service, store = _make_service(tmp_path, execution)
    monkeypatch.setattr(service, "ASYNC_EARLY_COMPLETION_WAIT_SECONDS", 0.01)
    monkeypatch.setattr(service, "_preflight_non_blocking_interactive_error", lambda _fn_id: None)

    result = service.call_tool(
        session_id="sess-interactive-1",
        fn_id="micro_sam.sam_annotator.annotator_2d",
        inputs={"image": {"ref_id": "r1", "type": "BioImageRef", "uri": "file:///tmp/a.tif"}},
        params={},
    )

    assert result["status"] == "running"
    assert result["run_id"] == "run-interactive-1"
    assert result["warnings"] == ["INTERACTIVE_RUNNING_IN_BACKGROUND"]
    assert execution.last_spec["steps"][0]["id"] == "micro_sam.sam_annotator.annotator_2d"
    time.sleep(0.3)
    store.close()


def test_call_tool_microsam_annotator_immediate_failure_returns_failed(tmp_path: Path) -> None:
    execution = FakeExecutionService(
        run_result={"run_id": "run-interactive-2", "status": "failed", "warnings": []},
        run_status={
            "status": "failed",
            "outputs": {},
            "error": {"code": "HEADLESS_DISPLAY_REQUIRED", "message": "no display"},
        },
        delay_seconds=0.0,
    )
    service, store = _make_service(tmp_path, execution)

    result = service.call_tool(
        session_id="sess-interactive-2",
        fn_id="micro_sam.sam_annotator.annotator_2d",
        inputs={"image": {"ref_id": "r1", "type": "BioImageRef", "uri": "file:///tmp/a.tif"}},
        params={},
    )

    assert result["status"] == "failed"
    assert result["isError"] is True
    assert result["error"]["code"] == "HEADLESS_DISPLAY_REQUIRED"
    store.close()


def test_call_tool_microsam_annotator_preflight_headless_failure(
    tmp_path: Path, monkeypatch
) -> None:
    execution = FakeExecutionService(
        run_result={"run_id": "run-interactive-3", "status": "success"},
        run_status={"status": "success", "outputs": {}},
    )
    service, store = _make_service(tmp_path, execution)

    from bioimage_mcp.registry.dynamic.adapters.microsam import HeadlessDisplayRequiredError

    def _raise_headless(*_args, **_kwargs):
        raise HeadlessDisplayRequiredError("no display")

    monkeypatch.setattr(
        "bioimage_mcp.registry.dynamic.adapters.microsam.MicrosamAdapter._check_gui_available",
        _raise_headless,
    )

    result = service.call_tool(
        session_id="sess-interactive-3",
        fn_id="micro_sam.sam_annotator.annotator_2d",
        inputs={"image": {"ref_id": "r1", "type": "BioImageRef", "uri": "file:///tmp/a.tif"}},
        params={},
    )

    assert result["status"] == "failed"
    assert result["run_id"] == "none"
    assert result["error"]["code"] == "HEADLESS_DISPLAY_REQUIRED"
    assert not hasattr(execution, "last_spec")
    store.close()
