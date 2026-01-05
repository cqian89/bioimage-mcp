"""Contract tests for the 'run' MCP tool.

These tests verify:
- Successful execution returns outputs
- Validation failures return structured errors
- Error format follows StructuredError schema
- Failed execution returns log reference
"""

import pytest
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


# T067: Dry-run success
def test_dry_run_success(tmp_path: Path, monkeypatch):
    """dry_run=true with valid inputs should return success without executing."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    svc = ExecutionService(config)

    # Mock validate_workflow to return NO errors
    monkeypatch.setattr(svc, "validate_workflow", lambda _s: [])

    # Mock execute_step - it should NOT be called
    def fail_if_called(**_kw):
        pytest.fail("execute_step should not be called during dry_run")

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", fail_if_called)

    # Mock _get_function_metadata
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "bioimage_mcp.api.execution._get_function_metadata",
        lambda _c, _id: (MagicMock(env_id="env1", entrypoint="main.py"), MagicMock()),
    )

    spec = {"steps": [{"fn_id": "base.ops.gaussian", "inputs": {"image": "ref1"}, "params": {}}]}
    response = svc.run_workflow(spec, dry_run=True)

    assert response["status"] == "success"
    assert response.get("dry_run") is True
    assert "outputs" in response
    assert response["run_id"] == "none"


# T068: Dry-run validation failure
def test_dry_run_validation_failed_missing_input(tmp_path: Path, monkeypatch):
    """dry_run=true should fail validation same as real run."""
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
                actual="missing",
            )
        ],
    )

    # Mock _get_function_metadata
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "bioimage_mcp.api.execution._get_function_metadata",
        lambda _c, _id: (MagicMock(env_id="env1", entrypoint="main.py"), MagicMock()),
    )

    spec = {"steps": [{"fn_id": "base.ops.gaussian", "inputs": {}, "params": {}}]}
    response = svc.run_workflow(spec, dry_run=True)

    assert response["status"] == "validation_failed"
    assert response["error"]["code"] == "VALIDATION_FAILED"
    assert response["error"]["details"][0]["actual"] == "missing"


# T069: Dry-run parity with real execution
def test_dry_run_validation_parity(tmp_path: Path, monkeypatch):
    """Dry-run validation should be identical to real execution validation."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    svc = ExecutionService(config)

    # Mock validate_workflow
    from bioimage_mcp.api.schemas import ErrorDetail

    errors = [
        ErrorDetail(
            path="/steps/0/inputs/image",
            hint="Type mismatch",
            expected="BioImageRef",
            actual="TableRef",
        )
    ]
    monkeypatch.setattr(svc, "validate_workflow", lambda _s: errors)

    # Mock _get_function_metadata
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "bioimage_mcp.api.execution._get_function_metadata",
        lambda _c, _id: (MagicMock(env_id="env1", entrypoint="main.py"), MagicMock()),
    )

    spec = {"steps": [{"fn_id": "base.ops.gaussian", "inputs": {"image": "ref1"}, "params": {}}]}

    # Run dry
    dry_response = svc.run_workflow(spec, dry_run=True)

    # Run real
    real_response = svc.run_workflow(spec, dry_run=False)

    assert dry_response["status"] == "validation_failed"
    assert real_response["status"] == "validation_failed"
    assert dry_response["error"] == real_response["error"]


# T038b: NOT_FOUND error for invalid function ID in run
def test_run_returns_not_found_for_invalid_id(tmp_path: Path):
    """Run should return NOT_FOUND error for non-existent function IDs."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    svc = ExecutionService(config)

    spec = {"steps": [{"fn_id": "invalid.function.id", "inputs": {}, "params": {}}]}
    response = svc.run_workflow(spec, skip_validation=True)

    assert response["status"] == "failed"
    assert "error" in response
    assert response["error"]["code"] == "NOT_FOUND"
    assert "details" in response["error"]
    assert response["error"]["details"][0]["path"] == "/steps/0/fn_id"
