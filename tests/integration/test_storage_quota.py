import pytest
import sqlite3
from pathlib import Path
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config, StorageSettings
from bioimage_mcp.storage.sqlite import init_schema


@pytest.fixture
def execution_service(tmp_path):
    root = (tmp_path / "mcp").absolute()
    root.mkdir()
    (root / "tools").mkdir()
    config = Config(
        artifact_store_root=root,
        tool_manifest_roots=[(root / "tools").absolute()],
        storage=StorageSettings(quota_bytes=1000, warning_threshold=0.80, critical_threshold=0.95),
    )
    # ExecutionService will create its own stores using the config.
    # Since artifact_store_root is set, they will use the same index.db.
    svc = ExecutionService(config)
    return svc


def test_run_workflow_blocked_by_quota(execution_service):
    # T040, T041: Quota enforcement blocking run
    # Fill up storage to 96%
    large_file = execution_service._config.artifact_store_root / "large.dat"
    large_file.write_bytes(b"x" * 960)

    # Import it into the store to make it counted
    execution_service.artifact_store.import_file(
        large_file, artifact_type="BioImageRef", format="tiff"
    )

    workflow = {"steps": [{"fn_id": "base.identity", "params": {}, "inputs": {}}]}

    # Action
    result = execution_service.run_workflow(workflow)

    # Verification
    assert result["status"] == "failed"
    assert "error" in result
    error = result["error"]
    assert error["code"] == "QUOTA_EXCEEDED"
    assert "96.0%" in error["message"]
    assert error["details"]["usage_percent"] == 96.0
    assert "suggestion" in error["details"]
    assert "prune" in error["details"]["suggestion"]


def test_run_workflow_warning_only(execution_service, caplog):
    # T044: Add warning log when exceeding warning threshold
    # 85% usage
    mid_file = execution_service._config.artifact_store_root / "mid.dat"
    mid_file.write_bytes(b"x" * 850)

    execution_service.artifact_store.import_file(
        mid_file, artifact_type="BioImageRef", format="tiff"
    )

    workflow = {"steps": [{"fn_id": "base.identity", "params": {}, "inputs": {}}]}

    # We need a mock tool or a way to let it pass if it's allowed
    # Since base.identity might not exist, we can use dry_run=True?
    # Wait, if it's blocked by quota, it should happen BEFORE dry_run check?
    # Or maybe it should also apply to dry_run? Probably not.
    # But for this test, we want to see it NOT block but log.

    import logging

    with caplog.at_level(logging.WARNING):
        # We might need to mock execute_step to avoid failure because fn_id doesn't exist
        # or just use a real function if available.
        # Let's try dry_run first. If quota check is before dry_run, it should still work.
        result = execution_service.run_workflow(workflow, dry_run=True)

    assert result["status"] == "success" or (
        result["status"] == "failed" and result["error"]["code"] != "QUOTA_EXCEEDED"
    )
    assert any(
        "storage quota" in record.message.lower() and "85.0%" in record.message
        for record in caplog.records
    )
