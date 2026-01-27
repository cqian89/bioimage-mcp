from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioimage_mcp.api.schemas import WorkflowRecord, WorkflowStep
from bioimage_mcp.api.sessions import SessionService
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


def test_replay_session_validation_failed(session_service):
    # Setup
    from bioimage_mcp.artifacts.models import ArtifactRef

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={},
        steps=[
            WorkflowStep(index=0, id="test.fn", inputs={}, params={}, outputs={}, status="success")
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")

    params_schema = {"type": "object", "properties": {"diameter": {"type": "number"}}}
    mock_descriptor = MagicMock()
    mock_descriptor.params_schema = params_schema
    session_service.discovery_service.describe_function.return_value = mock_descriptor

    from bioimage_mcp.api.schemas import SessionReplayRequest

    request = SessionReplayRequest(
        workflow_ref=workflow_ref, inputs={}, params_overrides={"test.fn": {"diameter": "invalid"}}
    )

    # Act
    response = session_service.replay_session(request)

    # Assert
    assert response.status == "validation_failed"
    assert response.error.code == "VALIDATION_FAILED"
    assert len(response.error.details) == 1
    assert response.error.details[0].path == "/params_overrides/test.fn/diameter"


def test_check_version_mismatches(session_service):
    # Setup
    from bioimage_mcp.api.schemas import StepProvenance

    recorded_hash = "old-hash"
    current_hash = "new-hash"

    step = WorkflowStep(
        index=0,
        id="test.fn",
        inputs={},
        params={},
        outputs={},
        status="success",
        provenance=StepProvenance(
            tool_pack_id="test-pack", tool_pack_version="1.0.0", lock_hash=recorded_hash
        ),
    )
    record = WorkflowRecord(session_id="test-session", external_inputs={}, steps=[step])

    session_service.session_manager.get_function_provenance.return_value = {
        "lock_hash": current_hash
    }

    # Act
    mismatches = session_service._check_version_mismatches(record)

    # Assert
    assert len(mismatches) == 1
    assert mismatches[0]["fn_id"] == "test.fn"
    assert mismatches[0]["recorded"] == recorded_hash
    assert mismatches[0]["current"] == current_hash


def test_version_mismatch_warning_helper():
    from bioimage_mcp.api.errors import version_mismatch_warning

    error = version_mismatch_warning(
        message="Version mismatch", fn_id="test.fn", recorded_hash="old", current_hash="new"
    )

    assert error.code == "VERSION_MISMATCH"
    assert len(error.details) == 1
    assert error.details[0].expected == "old"
    assert error.details[0].actual == "new"


def test_replay_session_environment_missing(session_service):
    # Setup
    from unittest.mock import MagicMock, patch

    from bioimage_mcp.artifacts.models import ArtifactRef

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={},
        steps=[
            WorkflowStep(
                index=0, id="missing-env.fn", inputs={}, params={}, outputs={}, status="success"
            )
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")

    from bioimage_mcp.api.schemas import SessionReplayRequest

    request = SessionReplayRequest(workflow_ref=workflow_ref, inputs={})

    # Mock subprocess.run to simulate missing environment
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        # Act
        response = session_service.replay_session(request)

        # Assert
        assert response.status == "validation_failed"
        assert response.error.code == "ENVIRONMENT_MISSING"
        assert response.installable is not None
        assert response.installable.env_name == "missing-env"
        assert "bioimage-mcp install missing-env" in response.installable.command


def test_replay_session_function_not_found(session_service):
    # Setup
    from unittest.mock import MagicMock, patch

    from bioimage_mcp.artifacts.models import ArtifactRef

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={},
        steps=[
            WorkflowStep(
                index=0,
                id="existing-env.missing-fn",
                inputs={},
                params={},
                outputs={},
                status="success",
            )
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")

    from bioimage_mcp.api.schemas import SessionReplayRequest

    request = SessionReplayRequest(workflow_ref=workflow_ref, inputs={})

    # Mock subprocess.run to simulate existing environment
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Mock _function_exists to return False
        session_service._function_exists = MagicMock(return_value=False)

        # Act
        response = session_service.replay_session(request)

        # Assert
        assert response.status == "validation_failed"
        assert response.error.code == "NOT_FOUND"
        assert "Function 'existing-env.missing-fn' not found" in response.error.message


def test_replay_session_progress(session_service):
    # Setup
    from unittest.mock import MagicMock, patch

    from bioimage_mcp.api.schemas import SessionReplayRequest
    from bioimage_mcp.artifacts.models import ArtifactRef

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={},
        steps=[
            WorkflowStep(
                index=0, id="test.fn1", inputs={}, params={}, outputs={}, status="success"
            ),
            WorkflowStep(
                index=1, id="test.fn2", inputs={}, params={}, outputs={}, status="success"
            ),
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")
    session_service.execution_service.run_workflow.return_value = {
        "status": "success",
        "run_id": "run-123",
        "outputs": {"output": ArtifactRef(ref_id="art-1", type="BioImageRef", uri="")},
    }
    session_service._function_exists = MagicMock(return_value=True)

    request = SessionReplayRequest(workflow_ref=workflow_ref, inputs={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        response = session_service.replay_session(request)

        # Assert
        assert response.status == "completed"
        assert len(response.step_progress) == 2
        assert response.step_progress[0].step_index == 0
        assert response.step_progress[0].status == "success"
        assert response.step_progress[1].step_index == 1
        assert response.step_progress[1].status == "success"
        assert "art-1" in response.outputs["output"].ref_id


def test_replay_session_dry_run(session_service):
    # Setup
    from unittest.mock import MagicMock, patch

    from bioimage_mcp.api.schemas import SessionReplayRequest
    from bioimage_mcp.artifacts.models import ArtifactRef

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={},
        steps=[
            WorkflowStep(index=0, id="test.fn1", inputs={}, params={}, outputs={}, status="success")
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")
    session_service._function_exists = MagicMock(return_value=True)

    request = SessionReplayRequest(workflow_ref=workflow_ref, inputs={}, dry_run=True)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        response = session_service.replay_session(request)

        # Assert
        assert response.status == "ready"
        assert len(response.step_progress) == 1
        assert response.step_progress[0].status == "pending"
        # Verify no execution occurred
        session_service.execution_service.run_workflow.assert_not_called()


def test_replay_session_tool_warnings(session_service):
    # Setup
    from unittest.mock import MagicMock, patch

    from bioimage_mcp.api.schemas import SessionReplayRequest
    from bioimage_mcp.artifacts.models import ArtifactRef

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={},
        steps=[
            WorkflowStep(index=0, id="test.fn1", inputs={}, params={}, outputs={}, status="success")
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")
    session_service.execution_service.run_workflow.return_value = {
        "status": "success",
        "run_id": "run-123",
        "warnings": ["Low contrast detected"],
    }
    session_service._function_exists = MagicMock(return_value=True)

    request = SessionReplayRequest(workflow_ref=workflow_ref, inputs={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        response = session_service.replay_session(request)

        # Assert
        assert len(response.warnings) == 1
        assert response.warnings[0].source == "tool"
        assert "Low contrast" in response.warnings[0].message


def test_replay_session_missing_inputs(session_service):
    # Setup
    from unittest.mock import MagicMock, patch

    from bioimage_mcp.api.schemas import ExternalInput, SessionReplayRequest
    from bioimage_mcp.artifacts.models import ArtifactRef

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={
            "input-1": ExternalInput(type="BioImageRef", first_seen={"step": 0, "port": "image"})
        },
        steps=[
            WorkflowStep(index=0, id="test.fn1", inputs={}, params={}, outputs={}, status="success")
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")
    session_service._function_exists = MagicMock(return_value=True)

    # Request with missing 'input-1'
    request = SessionReplayRequest(workflow_ref=workflow_ref, inputs={})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        response = session_service.replay_session(request)

        # Assert
        assert response.status == "validation_failed"
        assert response.error.code == "INPUT_MISSING"
        assert len(response.error.details) == 1
        assert response.error.details[0].path == "/inputs/input-1"
        assert "input-1" in response.human_summary


def test_replay_session_resume(session_service):
    # Setup
    from unittest.mock import MagicMock, patch

    from bioimage_mcp.api.schemas import SessionReplayRequest
    from bioimage_mcp.artifacts.models import ArtifactRef
    from bioimage_mcp.sessions.models import SessionStep

    workflow_ref = ArtifactRef(ref_id="wf-123", type="TableRef", uri="")
    record = WorkflowRecord(
        session_id="old-session",
        external_inputs={},
        steps=[
            WorkflowStep(
                index=0, id="test.fn1", inputs={}, params={}, outputs={}, status="success"
            ),
            WorkflowStep(
                index=1, id="test.fn2", inputs={}, params={}, outputs={}, status="success"
            ),
        ],
    )

    session_service.artifact_store.parse_native_output.return_value = record.model_dump(mode="json")
    session_service._function_exists = MagicMock(return_value=True)

    # Mock existing session with step 0 completed
    replay_session_id = "existing-session"
    mock_step_0 = MagicMock(spec=SessionStep)
    mock_step_0.ordinal = 0
    mock_step_0.fn_id = "test.fn1"
    mock_step_0.status = "success"
    mock_step_0.canonical = True
    mock_step_0.outputs = {"out": {"ref_id": "art-0"}}

    session_service.session_manager.store.list_step_attempts.return_value = [mock_step_0]
    session_service.execution_service.run_workflow.return_value = {
        "status": "success",
        "run_id": "run-456",
        "outputs": {"final": ArtifactRef(ref_id="art-1", type="BioImageRef", uri="")},
    }

    request = SessionReplayRequest(
        workflow_ref=workflow_ref, inputs={}, resume_session_id=replay_session_id
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        response = session_service.replay_session(request)

        # Assert
        assert response.status == "completed"
        assert len(response.step_progress) == 2
        assert response.step_progress[0].status == "skipped"
        assert response.step_progress[1].status == "success"
        assert response.step_progress[1].fn_id == "test.fn2"

        # Verify execution_service.run_workflow was only called once (for step 1)
        assert session_service.execution_service.run_workflow.call_count == 1
