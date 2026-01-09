import pytest
from unittest.mock import MagicMock
from bioimage_mcp.api.interactive import InteractiveExecutionService


def test_call_tool_quota_exceeded():
    # Setup mocks
    session_manager = MagicMock()
    session_manager.store.list_step_attempts.return_value = []
    execution = MagicMock()

    # Mock run_workflow to return quota exceeded
    quota_error = {
        "code": "QUOTA_EXCEEDED",
        "message": "Storage quota exceeded",
        "details": {"used": 100, "quota": 100},
    }
    execution.run_workflow.return_value = {
        "session_id": "test-session",
        "run_id": "none",
        "status": "failed",
        "id": "unknown",
        "error": quota_error,
    }
    execution.get_run_status.return_value = {"error": "Run not found"}

    # Mock config for SessionService (which is initialized in __init__)
    execution._config.storage.quota_bytes = 1000
    execution.artifact_store = MagicMock()

    service = InteractiveExecutionService(session_manager, execution)

    # Call tool
    result = service.call_tool(session_id="test-session", fn_id="test.tool", inputs={}, params={})

    # Verify results
    assert result["status"] == "failed"
    assert result["session_id"] == "test-session"
    assert result["error"] == quota_error
    assert result["isError"] is True
    assert "step_id" in result
    assert "run_id" not in result or result["run_id"] == "none"

    # Verify get_run_status was NOT called with "none"
    execution.get_run_status.assert_not_called()
