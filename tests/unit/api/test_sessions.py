from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from bioimage_mcp.api.sessions import SessionService
from bioimage_mcp.api.schemas import WorkflowRecord, WorkflowStep, ErrorDetail
from bioimage_mcp.config.schema import Config


@pytest.fixture
def mock_config():
    return Config(
        artifact_store_root="/tmp/artifacts",
        tool_manifest_roots=["/tmp/tools"],
        fs_allowlist_read=["/tmp"],
        fs_allowlist_write=["/tmp"],
    )


@pytest.fixture
def session_service(mock_config):
    session_manager = MagicMock()
    artifact_store = MagicMock()
    execution_service = MagicMock()
    discovery_service = MagicMock()

    return SessionService(
        config=mock_config,
        session_manager=session_manager,
        artifact_store=artifact_store,
        execution_service=execution_service,
        discovery_service=discovery_service,
    )


def test_validate_overrides_valid(session_service):
    # Setup
    fn_id = "test.fn"
    params_schema = {"type": "object", "properties": {"diameter": {"type": "number"}}}
    mock_descriptor = MagicMock()
    mock_descriptor.params_schema = params_schema
    session_service.discovery_service.describe_function.return_value = mock_descriptor

    params_overrides = {fn_id: {"diameter": 30.0}}
    record = WorkflowRecord(session_id="test-session", external_inputs={}, steps=[])

    # Act
    errors = session_service._validate_overrides(params_overrides, None, record)

    # Assert
    assert len(errors) == 0


def test_validate_overrides_invalid_type(session_service):
    # Setup
    fn_id = "test.fn"
    params_schema = {"type": "object", "properties": {"diameter": {"type": "number"}}}
    # Mocking describe_function result
    mock_descriptor = MagicMock()
    mock_descriptor.params_schema = params_schema
    session_service.discovery_service.describe_function.return_value = mock_descriptor

    params_overrides = {fn_id: {"diameter": "not-a-number"}}
    record = WorkflowRecord(session_id="test-session", external_inputs={}, steps=[])

    # Act
    errors = session_service._validate_overrides(params_overrides, None, record)

    # Assert
    assert len(errors) == 1
    assert errors[0].path == f"/params_overrides/{fn_id}/diameter"
    assert "number" in errors[0].expected
    assert "not-a-number" in errors[0].actual


def test_validate_step_overrides_invalid(session_service):
    # Setup
    fn_id = "test.fn"
    params_schema = {"type": "object", "properties": {"diameter": {"type": "number"}}}
    mock_descriptor = MagicMock()
    mock_descriptor.params_schema = params_schema
    session_service.discovery_service.describe_function.return_value = mock_descriptor

    step = WorkflowStep(index=0, id=fn_id, inputs={}, params={}, outputs={}, status="success")
    record = WorkflowRecord(session_id="test-session", external_inputs={}, steps=[step])

    step_overrides = {"step:0": {"params": {"diameter": "invalid"}}}

    # Act
    errors = session_service._validate_overrides(None, step_overrides, record)

    # Assert
    assert len(errors) == 1
    assert errors[0].path == "/step_overrides/step:0/params/diameter"
