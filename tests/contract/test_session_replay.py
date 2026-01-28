"""Contract tests for the session_replay tool (T086-T090, T114)."""

import json
from unittest.mock import MagicMock

import pytest

from bioimage_mcp.api.schemas import ArtifactRef, SessionReplayRequest
from bioimage_mcp.api.sessions import SessionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


@pytest.fixture
def session_service(tmp_path):
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
        fs_allowlist_read=[str(tmp_path)],
        fs_allowlist_write=[str(tmp_path)],
    )
    store = ArtifactStore(config)
    session_manager = MagicMock()
    execution_service = MagicMock()
    service = SessionService(
        config,
        session_manager=session_manager,
        artifact_store=store,
        execution_service=execution_service,
    )
    # Mock _function_exists to return True by default so basic tests pass
    service._function_exists = MagicMock(return_value=True)
    # Mock _env_installed to return True by default so env validation doesn't block tests
    service._env_installed = MagicMock(return_value=True)
    return service, session_manager, execution_service, store


def create_mock_workflow(tmp_path, steps=None, external_inputs=None):
    if steps is None:
        steps = [
            {
                "index": 0,
                "id": "test.func",
                "inputs": {"image": {"source": "external", "key": "input1"}},
                "params": {"p1": 1},
                "outputs": {},
                "status": "success",
            }
        ]
    if external_inputs is None:
        external_inputs = {
            "input1": {"type": "BioImageRef", "first_seen": {"step_index": 0, "port": "image"}}
        }

    workflow = {
        "schema_version": "2026-01",
        "session_id": "old-sess",
        "external_inputs": external_inputs,
        "steps": steps,
    }
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(workflow))
    return ArtifactRef(
        ref_id="wf-1", type="TableRef", format="workflow-record-json", uri=f"file://{path}"
    )


def test_session_replay_basic(session_service, tmp_path):
    """T086: session_replay should execute workflow with new inputs."""
    service, _, execution_service, _ = session_service

    wf_ref = create_mock_workflow(tmp_path)
    req = SessionReplayRequest(workflow_ref=wf_ref, inputs={"input1": "new-ref-123"})

    execution_service.run_workflow.return_value = {
        "run_id": "run-replay-1",
        "session_id": "new-sess",
        "status": "success",
        "log_ref": None,
        "error": None,
        "outputs": {"result": {"ref_id": "out-123", "type": "BioImageRef", "uri": ""}},
    }

    resp = service.replay_session(req)

    assert resp.run_id == "run-replay-1"
    assert resp.status == "success"
    # Verify execution_service was called with mapped inputs
    call_args = execution_service.run_workflow.call_args[0][0]
    assert call_args["steps"][0]["inputs"]["image"]["ref_id"] == "new-ref-123"


def test_session_replay_missing_input_error(session_service, tmp_path):
    """T088: session_replay should fail if external input not provided."""
    service, _, _, _ = session_service

    wf_ref = create_mock_workflow(tmp_path)
    # Missing input1
    req = SessionReplayRequest(workflow_ref=wf_ref, inputs={})

    resp = service.replay_session(req)

    assert resp.status == "validation_failed"
    assert resp.error.code == "INPUT_MISSING"
    assert "Missing 1 required external input(s)" in resp.error.message
    assert len(resp.error.details) == 1
    assert resp.error.details[0].path == "/inputs/input1"


def test_session_replay_params_overrides(session_service, tmp_path):
    """T089: session_replay should apply params_overrides by function ID."""
    service, _, execution_service, _ = session_service

    wf_ref = create_mock_workflow(tmp_path)
    req = SessionReplayRequest(
        workflow_ref=wf_ref,
        inputs={"input1": "new-ref-123"},
        params_overrides={"test.func": {"p1": 99}},
    )

    execution_service.run_workflow.return_value = {
        "run_id": "run-replay-1",
        "session_id": "new-sess",
        "status": "success",
        "log_ref": None,
        "error": None,
        "outputs": {"result": {"ref_id": "out-123", "type": "BioImageRef", "uri": ""}},
    }

    service.replay_session(req)

    call_args = execution_service.run_workflow.call_args[0][0]
    assert call_args["steps"][0]["params"]["p1"] == 99


def test_session_replay_step_overrides(session_service, tmp_path):
    """T090: session_replay should apply step_overrides by step index."""
    service, _, execution_service, _ = session_service

    wf_ref = create_mock_workflow(tmp_path)
    req = SessionReplayRequest(
        workflow_ref=wf_ref,
        inputs={"input1": "new-ref-123"},
        step_overrides={"step:0": {"params": {"p1": 42}}},
    )

    execution_service.run_workflow.return_value = {
        "run_id": "run-replay-1",
        "session_id": "new-sess",
        "status": "success",
        "log_ref": None,
        "error": None,
        "outputs": {"result": {"ref_id": "out-123", "type": "BioImageRef", "uri": ""}},
    }

    service.replay_session(req)

    call_args = execution_service.run_workflow.call_args[0][0]
    assert call_args["steps"][0]["params"]["p1"] == 42


def test_session_replay_function_not_found(session_service, tmp_path):
    """T114: session_replay should fail if function no longer exists."""
    service, _, execution_service, _ = session_service

    wf_ref = create_mock_workflow(tmp_path)
    req = SessionReplayRequest(workflow_ref=wf_ref, inputs={"input1": "new-ref-123"})

    # Mock function not found
    service._function_exists.return_value = False

    resp = service.replay_session(req)

    assert resp.status == "validation_failed"
    assert resp.error.code == "NOT_FOUND"
    assert "Function 'test.func' not found" in resp.error.message
    assert len(resp.error.details) == 1
    assert resp.error.details[0].path == "/steps/0/id"

    # Verify execution was NOT started
    execution_service.run_workflow.assert_not_called()
