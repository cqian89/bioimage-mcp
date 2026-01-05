"""Contract tests for the session_export tool (T083-T085, T113, T117)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from bioimage_mcp.api.sessions import SessionService
from bioimage_mcp.api.schemas import SessionExportRequest, WorkflowRecord
from bioimage_mcp.config.schema import Config
from bioimage_mcp.artifacts.store import ArtifactStore


@pytest.fixture
def session_service(tmp_path):
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
        fs_allowlist_read=[str(tmp_path)],
        fs_allowlist_write=[str(tmp_path)],
    )
    store = ArtifactStore(config)
    # Mock SessionManager and SessionStore
    session_manager = MagicMock()
    service = SessionService(config, session_manager=session_manager, artifact_store=store)
    return service, session_manager, store


def test_session_export_basic(session_service):
    """T083: session_export should return workflow_ref artifact."""
    service, session_manager, _ = session_service

    # Mock canonical steps
    mock_step = MagicMock()
    mock_step.ordinal = 0
    mock_step.fn_id = "test.func"
    mock_step.inputs = {"image": "ref-123"}
    mock_step.params = {"p1": 1}
    mock_step.outputs = {
        "out": {
            "ref_id": "ref-456",
            "type": "BioImageRef",
            "uri": "file:///tmp/out.tif",
        }
    }
    mock_step.status = "succeeded"
    mock_step.canonical = True
    mock_step.log_ref_id = "log-123"
    mock_step.started_at = "2024-01-01T00:00:00Z"
    mock_step.ended_at = "2024-01-01T00:00:01Z"

    session_manager.store.list_step_attempts.return_value = [mock_step]

    # Mock function metadata for provenance
    mock_manifest = MagicMock()
    mock_manifest.id = "test-pack"
    mock_manifest.version = "1.0.0"
    session_manager.get_function_provenance.return_value = {
        "tool_pack_id": "test-pack",
        "tool_pack_version": "1.0.0",
        "lock_hash": "abc",
    }

    req = SessionExportRequest(session_id="sess-123")
    resp = service.export_session(req)

    assert resp.session_id == "sess-123"
    assert resp.workflow_ref.type == "NativeOutputRef"
    assert resp.workflow_ref.format == "workflow-record-json"


def test_session_export_tracks_external_inputs(session_service):
    """T084: Exported workflow should identify external_inputs."""
    service, session_manager, _ = session_service

    # Step 1: uses external image
    step1 = MagicMock(
        ordinal=0,
        fn_id="f1",
        inputs={"image": "ext-1"},
        outputs={
            "out1": {
                "ref_id": "res-1",
                "type": "BioImageRef",
                "uri": "file:///tmp/out1.tif",
            }
        },
        status="success",
        params={},
        log_ref_id=None,
        canonical=True,
        started_at="2024-01-01T00:00:00Z",
        ended_at="2024-01-01T00:00:01Z",
    )
    # Step 2: uses output from Step 1
    step2 = MagicMock(
        ordinal=1,
        fn_id="f2",
        inputs={"image": "res-1"},
        outputs={
            "out2": {
                "ref_id": "res-2",
                "type": "BioImageRef",
                "uri": "file:///tmp/out2.tif",
            }
        },
        status="success",
        params={},
        log_ref_id=None,
        canonical=True,
        started_at="2024-01-01T00:00:02Z",
        ended_at="2024-01-01T00:00:03Z",
    )

    session_manager.store.list_step_attempts.return_value = [step1, step2]
    session_manager.get_function_provenance.return_value = {
        "tool_pack_id": "test-pack",
        "tool_pack_version": "1.0.0",
        "lock_hash": "abc",
    }

    req = SessionExportRequest(session_id="sess-123")
    resp = service.export_session(req)

    # Read the generated artifact to verify content
    import json

    with open(resp.workflow_ref.uri.replace("file://", ""), "r") as f:
        record = json.load(f)

    assert "ext-1" in record["external_inputs"]
    assert record["steps"][0]["inputs"]["image"]["source"] == "external"
    assert record["steps"][0]["inputs"]["image"]["key"] == "ext-1"
    assert record["steps"][1]["inputs"]["image"]["source"] == "step"
    assert record["steps"][1]["inputs"]["image"]["step_index"] == 0


def test_session_export_provenance(session_service):
    """T113: Steps should include tool_pack_id, version, lock_hash."""
    service, session_manager, _ = session_service

    step = MagicMock(
        ordinal=0,
        fn_id="f1",
        inputs={},
        outputs={},
        status="success",
        params={},
        log_ref_id=None,
        started_at="2024-01-01T00:00:00Z",
        ended_at="2024-01-01T00:00:01Z",
    )
    session_manager.store.list_step_attempts.return_value = [step]
    session_manager.get_function_provenance.return_value = {
        "tool_pack_id": "my-tool",
        "tool_pack_version": "2.1.0",
        "lock_hash": "sha256:123",
    }

    req = SessionExportRequest(session_id="sess-123")
    resp = service.export_session(req)

    import json

    with open(resp.workflow_ref.uri.replace("file://", ""), "r") as f:
        record = json.load(f)

    prov = record["steps"][0]["provenance"]
    assert prov["tool_pack_id"] == "my-tool"
    assert prov["tool_pack_version"] == "2.1.0"
    assert prov["lock_hash"] == "sha256:123"


def test_session_export_dest_path_allowlist(session_service, tmp_path):
    """T117: dest_path outside allowed roots should be DENIED."""
    service, _, _ = session_service

    # Path outside tmp_path
    forbidden_path = "/etc/passwd"
    req = SessionExportRequest(session_id="sess-123", dest_path=forbidden_path)

    with pytest.raises(ValueError, match="Permission denied"):
        service.export_session(req)


def test_session_export_dest_path_bypass(session_service, tmp_path):
    """Test that path prefix bypass is correctly handled (Security Fix)."""
    service, _, _ = session_service

    # Create a path that starts with the same prefix as tmp_path but is not under it
    # tmp_path is something like /tmp/pytest-of-user/pytest-N/test_name0
    # We want /tmp/pytest-of-user/pytest-N/test_name0_bypass/file.json
    bypass_path = tmp_path.parent / (tmp_path.name + "_bypass") / "file.json"

    req = SessionExportRequest(session_id="sess-123", dest_path=str(bypass_path))

    with pytest.raises(ValueError, match="Permission denied"):
        service.export_session(req)
