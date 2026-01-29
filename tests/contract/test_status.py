"""Contract tests for the 'status' MCP tool.

These tests verify status polling for running/completed executions.
"""

from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.runs.store import RunStore


# T042: Status tool
def test_status_returns_run_state(tmp_path: Path):
    """Status should return current state of a run."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    store = ArtifactStore(config)
    run_store = RunStore(config)
    svc = ExecutionService(config, artifact_store=store, run_store=run_store)

    # Create a dummy run
    run = run_store.create_run(
        workflow_spec={"steps": []},
        inputs={},
        params={},
        provenance={"id": "test.fn"},
        log_ref_id=store.write_log("init").ref_id,
    )
    run_store.set_status(
        run.run_id,
        "succeeded",
        outputs={"out": {"ref_id": "ref123", "type": "BioImageRef", "uri": "file://out.tif"}},
    )

    response = svc.get_run_status(run.run_id)

    assert response["run_id"] == run.run_id
    assert response["status"] == "success"
    assert "outputs" in response
    assert "progress" in response
    assert response["progress"]["completed"] == 100


def test_status_returns_not_found_for_invalid_run_id(tmp_path: Path):
    """Status should return NOT_FOUND for invalid run_id."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    svc = ExecutionService(config)

    response = svc.get_run_status("invalid_run")
    assert "error" in response
    assert response["error"]["code"] == "NOT_FOUND"
