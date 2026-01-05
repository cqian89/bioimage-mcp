"""Contract tests for the 'status' MCP tool.

These tests verify status polling for running/completed executions.
"""

import pytest
from bioimage_mcp.api.schemas import StatusRequest, StatusResponse, Progress


# T042: Status tool
def test_status_returns_run_state():
    """Status should return current state of a run."""
    # Given: A run_id from a previous run
    # When: status(run_id="run_123")
    # Then: Response has run_id, status, progress, outputs
    pytest.skip("Not implemented - RED phase")


def test_status_returns_not_found_for_invalid_run_id():
    """Status should return NOT_FOUND for invalid run_id."""
    # Given: An invalid run_id
    # When: status(run_id="invalid_run")
    # Then: Error with code NOT_FOUND
    pytest.skip("Not implemented - RED phase")
