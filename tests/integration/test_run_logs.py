"""Integration test that failed run_workflow still returns LogRef (T015a).

Validates that even when workflow execution fails, the LogRef artifact
is still created and returned to aid debugging (FR-003).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config


def _mock_execute_step_failure(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates a Cellpose failure."""
    return (
        {
            "ok": False,
            "outputs": {},
            "error": {
                "message": "Cellpose failed: could not find cells in image",
                "code": "SEGMENTATION_FAILED",
            },
            "log": "ERROR: No cells detected. Check image quality and parameters.",
        },
        "Cellpose execution log:\n- Loading model: cyto3\n- Processing image...\n- ERROR: No cells detected\n- Exit with error",
        1,
    )


def _mock_execute_step_crash(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates a crash with stderr output."""
    return (
        {
            "ok": False,
            "outputs": {},
            "error": "Process crashed with signal 11",
        },
        "Traceback (most recent call last):\n  File ...\nSegmentation fault (core dumped)",
        -11,
    )


class TestFailedRunLogs:
    """Tests that failed workflow runs still produce LogRef artifacts."""

    def test_failed_run_returns_log_ref_id(self, tmp_path: Path, monkeypatch) -> None:
        """Test that failed run still includes log_ref_id in response."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_failure,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )

        assert result["status"] == "failed"
        assert "log_ref_id" in result, "Failed run must include log_ref_id for debugging"
        assert isinstance(result["log_ref_id"], str)
        assert len(result["log_ref_id"]) > 0

    def test_failed_run_log_ref_contains_error_info(self, tmp_path: Path, monkeypatch) -> None:
        """Test that log from failed run contains error information."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_failure,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )
            status = svc.get_run_status(result["run_id"])

        # Verify log_ref is present even for failed run
        assert "log_ref" in status
        log_ref = status["log_ref"]
        assert log_ref["type"] == "LogRef"

    def test_crashed_run_returns_log_ref(self, tmp_path: Path, monkeypatch) -> None:
        """Test that even crashed runs produce log artifacts."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_crash,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )

        assert result["status"] == "failed"
        assert "log_ref_id" in result

    def test_failed_run_status_includes_error_details(self, tmp_path: Path, monkeypatch) -> None:
        """Test that get_run_status includes error details for failed runs."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_failure,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )
            status = svc.get_run_status(result["run_id"])

        assert status["status"] == "failed"
        assert "error" in status
        error = status["error"]
        assert "message" in error or isinstance(error, dict)

    def test_failed_run_preserves_run_id(self, tmp_path: Path, monkeypatch) -> None:
        """Test that failed runs are tracked with valid run_id."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_failure,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {"steps": [{"fn_id": "cellpose.segment", "inputs": {}, "params": {}}]},
                skip_validation=True,
            )

            # Should be able to retrieve the failed run
            status = svc.get_run_status(result["run_id"])

        assert status["run_id"] == result["run_id"]
        assert status["status"] == "failed"
