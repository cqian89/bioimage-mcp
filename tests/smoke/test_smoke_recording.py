"""Test recording mode produces logs."""

import json
from types import SimpleNamespace

import pytest

from tests.smoke.conftest import _resolve_log_outcome


@pytest.mark.smoke_minimal
@pytest.mark.anyio
async def test_recording_mode_creates_log(live_server, smoke_record, log_dir, interaction_logger):
    """Test that recording mode creates interaction logs."""
    if not smoke_record:
        pytest.skip("Recording mode not enabled (use --smoke-record)")

    # Perform a simple interaction
    result = await live_server.call_tool("list", {})
    interaction_logger.log_request("list", {})
    interaction_logger.log_response("0", result, 100.0)

    # Manually save the log to verify its contents (T030)
    test_log_path = log_dir / "test_smoke_recording_manual.json"
    interaction_logger.save(test_log_path)

    assert test_log_path.exists(), "Log file should be created"

    # Verify log content
    with open(test_log_path) as f:
        data = json.load(f)

    # 1. Verify required top-level fields
    assert isinstance(data.get("test_run_id"), str) and data["test_run_id"], (
        "test_run_id must be a non-empty string"
    )
    assert isinstance(data.get("scenario"), str) and data["scenario"], (
        "scenario must be a non-empty string"
    )
    assert isinstance(data.get("interactions"), list), "interactions must be a list"
    assert len(data["interactions"]) >= 2, "Should have at least a request and a response"

    # 2. Verify interaction fields
    for interaction in data["interactions"]:
        assert "timestamp" in interaction, "Interaction must have a timestamp"
        assert interaction["direction"] in ["request", "response"], (
            f"Invalid direction: {interaction['direction']}"
        )
        assert "tool" in interaction, "Interaction must have a tool name"
        assert isinstance(interaction["tool"], str) and interaction["tool"], (
            "Tool must be a non-empty string"
        )

    # 3. Verify specific fields in request/response
    request = next(i for i in data["interactions"] if i["direction"] == "request")
    response = next(i for i in data["interactions"] if i["direction"] == "response")

    assert "params" in request
    assert "result" in response
    assert isinstance(response.get("duration_ms"), (int, float)), (
        "Response should have a duration_ms"
    )
    assert response["duration_ms"] > 0

    # Cleanup manual log (the fixture will still save its own version)
    test_log_path.unlink()


def test_resolve_log_outcome_marks_skipped_setup_as_skipped() -> None:
    rep_setup = SimpleNamespace(skipped=True, failed=False, passed=False, longrepr="skip during setup")

    status, error_summary, skip_reason = _resolve_log_outcome(rep_setup, None, None)

    assert status == "skipped"
    assert error_summary is None
    assert skip_reason == "skip during setup"


def test_resolve_log_outcome_marks_failures_as_failed() -> None:
    rep_call = SimpleNamespace(skipped=False, failed=True, passed=False, longrepr="boom")

    status, error_summary, skip_reason = _resolve_log_outcome(None, rep_call, None)

    assert status == "failed"
    assert error_summary == "boom"
    assert skip_reason is None
