"""Integration test for session export (US4).

Tests that sessions can be exported to reproducible workflow artifacts,
filtering only canonical steps and preserving execution history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


def _mock_execute_step_success(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates successful execution."""
    # Create a fake output file
    output_path = work_dir / "output.txt"
    output_path.write_text("result")

    return (
        {
            "ok": True,
            "outputs": {
                "result": {
                    "type": "BioImageRef",
                    "format": "text",
                    "path": str(output_path),
                }
            },
        },
        "Execution successful",
        0,
    )


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
    """Mock execute_step that simulates failure."""
    return (
        {
            "ok": False,
            "error": {"message": "Simulated failure", "code": "TEST_ERROR"},
        },
        "Execution failed",
        1,
    )


class TestExportSession:
    """Integration tests for session export functionality."""

    @pytest.fixture
    def services(self, tmp_path, monkeypatch):
        """Setup services with temporary stores and mocked execution."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        # Setup stores
        artifact_store = ArtifactStore(config)
        session_store = SessionStore()

        # Setup services
        session_manager = SessionManager(session_store, config)
        execution_service = ExecutionService(config, artifact_store=artifact_store)
        interactive_service = InteractiveExecutionService(session_manager, execution_service)

        return interactive_service, execution_service, artifact_store

    def test_export_session_canonical_steps(self, services, monkeypatch):
        """Test that export includes only canonical (successful) steps."""
        interactive, execution, artifact_store = services

        # 1. Setup session
        session_id = "test-session-001"

        # 2. Step 1: Attempt 1 (Failure)
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_failure,
        )
        result1 = interactive.call_tool(
            session_id=session_id,
            fn_id="test.tool",
            inputs={},
            params={"attempt": 1},
        )
        assert result1["status"] == "failed"

        # 3. Step 1: Attempt 2 (Success) - This should become canonical
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_success,
        )
        result2 = interactive.call_tool(
            session_id=session_id,
            fn_id="test.tool",
            inputs={},
            params={"attempt": 2},
            ordinal=0,  # Retry same ordinal
        )
        assert result2["status"] == "success"

        # 4. Step 2: Success
        result3 = interactive.call_tool(
            session_id=session_id,
            fn_id="test.tool",
            inputs={"prev": {"ref_id": "some-ref", "type": "BioImageRef"}},  # Dummy input
            params={"step": 2},
        )
        assert result3["status"] == "success"

        # 5. Export Session
        if not hasattr(interactive, "export_session"):
            pytest.skip("export_session not implemented yet")

        export_result = interactive.export_session(session_id)

        # 6. Verify Export Result
        assert export_result["type"] == "NativeOutputRef"
        assert export_result["format"] == "workflow-record-json"

        # 7. Verify Content
        record_content = artifact_store.get_raw_content(export_result["ref_id"])
        if isinstance(record_content, bytes):
            record = json.loads(record_content.decode())
        else:
            record = json.loads(record_content)

        assert record["session_id"] == session_id
        steps = record["workflow_spec"]["steps"]
        assert len(steps) == 2

        # Verify Step 1 is the successful attempt
        assert steps[0]["params"]["attempt"] == 2

        # Verify Step 2 is present
        assert steps[1]["params"]["step"] == 2

        # Verify Session Status
        session = interactive.session_manager.get_session(session_id)
        assert session.status == "exported"

    def test_export_empty_session_fails(self, services):
        """Test that exporting an empty session raises an error."""
        interactive, _, _ = services
        session_id = "empty-session"
        interactive.session_manager.ensure_session(session_id)

        if not hasattr(interactive, "export_session"):
            pytest.skip("export_session not implemented yet")

        with pytest.raises(ValueError, match="Cannot export empty session"):
            interactive.export_session(session_id)
