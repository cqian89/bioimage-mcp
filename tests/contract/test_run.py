"""Contract tests for the 'run' MCP tool.

These tests verify:
- Successful execution returns outputs
- Validation failures return structured errors
- Error format follows StructuredError schema
- Failed execution returns log reference
"""

from pathlib import Path
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


# T039: Run success
def test_run_success_returns_outputs(tmp_path: Path, monkeypatch):
    """Successful run should return outputs with ArtifactRefs."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
    )
    store = ArtifactStore(config)

    # Mock execute_step to return success
    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        lambda **_kw: (
            {
                "ok": True,
                "outputs": {"result": {"path": str(tmp_path / "out.tif"), "type": "BioImageRef"}},
            },
            "Execution log",
            0,
        ),
    )

    # Mock _get_function_metadata to return a valid manifest
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "bioimage_mcp.api.execution._get_function_metadata",
        lambda _c, _id: (MagicMock(env_id="env1", entrypoint="main.py"), MagicMock()),
    )

    svc = ExecutionService(config, artifact_store=store)

    # Pre-create output file
    (tmp_path / "out.tif").write_text("fake image data")

    spec = {
        "steps": [
            {
                "fn_id": "base.ops.gaussian",
                "inputs": {"image": {"ref_id": "ref123"}},
                "params": {"sigma": 1.0},
            }
        ]
    }
    # Skip validation since ref123 doesn't exist in store
    response = svc.run_workflow(spec, skip_validation=True)

    assert response["status"] == "success"
    assert "outputs" in response
    assert "result" in response["outputs"]
    assert response["outputs"]["result"]["type"] == "BioImageRef"


# T040: Validation failure
def test_run_validation_failed_for_missing_input(tmp_path: Path, monkeypatch):
    """Run should return validation_failed status for missing required inputs."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    svc = ExecutionService(config)

    # Mock validate_workflow to return errors
    from bioimage_mcp.api.schemas import ErrorDetail

    monkeypatch.setattr(
        svc,
        "validate_workflow",
        lambda _s: [
            ErrorDetail(
                path="/steps/0/inputs/image",
                hint="Missing required input",
                expected="BioImageRef",
                actual=None,
            )
        ],
    )

    spec = {"steps": [{"fn_id": "base.ops.gaussian", "inputs": {}, "params": {}}]}
    response = svc.run_workflow(spec)

    assert response["status"] == "validation_failed"
    assert "error" in response
    assert response["error"]["code"] == "VALIDATION_FAILED"
    assert len(response["error"]["details"]) == 1


# T041: Structured error format
def test_run_error_follows_structured_format(tmp_path: Path, monkeypatch):
    """Run errors should follow StructuredError format with path, expected, actual, hint."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    svc = ExecutionService(config)

    # Mock validate_workflow to return errors
    from bioimage_mcp.api.schemas import ErrorDetail

    monkeypatch.setattr(
        svc,
        "validate_workflow",
        lambda _s: [
            ErrorDetail(
                path="/steps/0/inputs/image",
                expected="BioImageRef",
                actual="TableRef",
                hint="Type mismatch",
            )
        ],
    )

    spec = {"steps": [{"fn_id": "base.ops.gaussian", "inputs": {"image": "ref123"}, "params": {}}]}
    response = svc.run_workflow(spec)

    assert response["error"]["details"][0]["path"] == "/steps/0/inputs/image"
    assert response["error"]["details"][0]["expected"] == "BioImageRef"
    assert response["error"]["details"][0]["actual"] == "TableRef"
    assert response["error"]["details"][0]["hint"] == "Type mismatch"


# T119: Failed execution with log reference
def test_run_failed_includes_log_reference(tmp_path: Path, monkeypatch):
    """When underlying function crashes, run should return failed status with log_ref."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    store = ArtifactStore(config)

    # Mock execute_step to return failure
    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        lambda **_kw: (
            {"ok": False, "error": {"message": "Crash!", "code": "CRASH"}},
            "Stack trace here...",
            1,
        ),
    )

    # Mock _get_function_metadata
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "bioimage_mcp.api.execution._get_function_metadata",
        lambda _c, _id: (MagicMock(env_id="env1", entrypoint="main.py"), MagicMock()),
    )

    svc = ExecutionService(config, artifact_store=store)

    spec = {"steps": [{"fn_id": "base.ops.gaussian", "inputs": {}, "params": {}}]}
    response = svc.run_workflow(spec, skip_validation=True)

    assert response["status"] == "failed"
    assert "log_ref" in response
    assert "error" in response
    assert response["error"]["message"] == "Crash!"
