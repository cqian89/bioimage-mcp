"""Contract tests for the 'run' MCP tool.

These tests verify:
- Successful execution returns outputs
- Validation failures return structured errors
- Error format follows StructuredError schema
- Failed execution returns log reference
"""

import pytest
from bioimage_mcp.api.schemas import RunRequest, RunResponse, ArtifactRef, StructuredError


# T039: Run success
def test_run_success_returns_outputs():
    """Successful run should return outputs with ArtifactRefs."""
    # Given: Valid function ID, inputs, and params
    # When: run(id="base.ops.gaussian", inputs={"image": "ref_123"}, params={"sigma": 1.0})
    # Then: status == "success"
    # And: outputs contains ArtifactRef objects
    pytest.skip("Not implemented - RED phase")


# T040: Validation failure
def test_run_validation_failed_for_missing_input():
    """Run should return validation_failed status for missing required inputs."""
    # Given: Function with required input
    # When: run(id="base.ops.gaussian", inputs={}, params={})
    # Then: status == "validation_failed"
    # And: error.code == "VALIDATION_FAILED"
    pytest.skip("Not implemented - RED phase")


# T041: Structured error format
def test_run_error_follows_structured_format():
    """Run errors should follow StructuredError format with path, expected, actual, hint."""
    # Given: Invalid input type
    # When: run with wrong input
    # Then: error.details[0] has path, expected, actual, hint fields
    pytest.skip("Not implemented - RED phase")


# T119: Failed execution with log reference
def test_run_failed_includes_log_reference():
    """When underlying function crashes, run should return failed status with log_ref."""
    # Given: A function that will crash
    # When: run that causes crash
    # Then: status == "failed"
    # And: log_ref is present with reference to error log
    pytest.skip("Not implemented - RED phase")
