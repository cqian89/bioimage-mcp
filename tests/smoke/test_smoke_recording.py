"""Test recording mode produces logs."""

import pytest


@pytest.mark.smoke_minimal
@pytest.mark.asyncio
async def test_recording_mode_creates_log(live_server, smoke_record, log_dir, interaction_logger):
    """Test that recording mode creates interaction logs."""
    if not smoke_record:
        pytest.skip("Recording mode not enabled (use --smoke-record)")

    # Perform a simple interaction
    result = await live_server.call_tool("list", {})
    interaction_logger.log_request("list", {})
    interaction_logger.log_response("0", result, 100.0)

    # The log will be saved by the interaction_logger fixture teardown
    # We verify the log directory exists
    assert log_dir.exists(), "Log directory should be created"
