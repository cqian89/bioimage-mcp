from pathlib import Path

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


def test_call_tool_dry_run_success(tmp_path: Path, monkeypatch) -> None:
    # Setup directories
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    tool_root.mkdir()

    # Create dummy tool entrypoint and manifest
    entrypoint = tmp_path / "tool_entrypoint.py"
    entrypoint.write_text(
        """
import json
import sys

req = json.loads(sys.stdin.read() or '{}')
resp = {'ok': True, 'outputs': {}}
print(json.dumps(resp))
""".lstrip()
    )

    (tool_root / "manifest.yaml").write_text(
        f"""
manifest_version: '0.0'
tool_id: tools.test
tool_version: '0.0.0'
name: Test
description: Test tool
env_id: bioimage-mcp-base
entrypoint: {entrypoint}
platforms_supported: [linux-64]
functions:
  - fn_id: fn.test
    tool_id: tools.test
    name: Test
    description: Test
    inputs: []
    outputs: []
    params_schema: {{type: object}}
""".lstrip()
    )

    # Initialize Config
    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    # Mock environment manager
    monkeypatch.setattr("bioimage_mcp.runtimes.executor.detect_env_manager", lambda: None)

    # Initialize Services
    execution_service = ExecutionService(config)
    session_store = SessionStore(config)
    session_manager = SessionManager(session_store, config)
    service = InteractiveExecutionService(session_manager, execution_service)

    # Create session
    session_id = "test_sess_dry_run"
    session_manager.ensure_session(session_id)

    # --- Test Action: Call with dry_run=True ---
    # This will fail with TypeError until we update the code
    try:
        result = service.call_tool(
            session_id=session_id,
            fn_id="fn.test",
            params={"p": 1},
            inputs={},
            dry_run=True,
        )
    except TypeError:
        # If code not updated yet, this is expected if we were running it now.
        # But we will update code next.
        pytest.fail("call_tool does not accept dry_run argument yet")

    # Verify result
    assert result["session_id"] == session_id
    assert result["status"] == "success"
    assert result.get("dry_run") is True
    assert "outputs" in result

    # Verify NO step recorded
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 0

    # Verify NO run created
    # We can check the run store directly
    # RunStore uses SQLite, we can list runs if there's a method or query the DB
    # The RunStore API has .get(run_id), but not list_runs() in the interface usually?
    # Actually ExecutionService has ._run_store.
    # We can check internal DB directly or trust that if no step is recorded (which links to run),
    # we are mostly good, but better to check run store.
    # RunStore usually has a cursor.
    # Let's inspect RunStore briefly or just assume for now.
    # But wait, we can just check if any run directory was created in artifacts/work/runs
    run_dir = artifact_root / "work" / "runs"
    if run_dir.exists():
        assert len(list(run_dir.iterdir())) == 0

    execution_service.close()


def test_call_tool_dry_run_validation_failure(tmp_path: Path, monkeypatch) -> None:
    # Setup directories
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    tool_root.mkdir()

    # Create dummy tool manifest with required input
    entrypoint = tmp_path / "tool_entrypoint.py"
    entrypoint.touch()

    (tool_root / "manifest.yaml").write_text(
        f"""
manifest_version: '0.0'
tool_id: tools.test
tool_version: '0.0.0'
name: Test
description: Test tool
env_id: bioimage-mcp-base
entrypoint: {entrypoint}
platforms_supported: [linux-64]
functions:
  - fn_id: fn.test_req
    tool_id: tools.test
    name: Test Req
    description: Test required input
    inputs:
      - name: image
        artifact_type: BioImageRef
        required: true
    outputs: []
    params_schema: {{type: object}}
""".lstrip()
    )

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
    )
    monkeypatch.setattr("bioimage_mcp.runtimes.executor.detect_env_manager", lambda: None)

    execution_service = ExecutionService(config)
    session_store = SessionStore(config)
    session_manager = SessionManager(session_store, config)
    service = InteractiveExecutionService(session_manager, execution_service)

    session_id = "test_sess_dry_run_fail"
    session_manager.ensure_session(session_id)

    # --- Test Action: Call with dry_run=True and missing input ---
    result = service.call_tool(
        session_id=session_id,
        fn_id="fn.test_req",
        params={},
        inputs={},  # Missing required 'image'
        dry_run=True,
    )

    assert result["session_id"] == session_id
    assert result["status"] == "validation_failed"
    assert result.get("dry_run") is True
    assert "error" in result
    # The error from validate_workflow is usually a list of dicts.
    # Our implementation will wrap it.
    assert result["error"]["code"] == "VALIDATION_FAILED"
    assert len(result["error"]["details"]) > 0
    assert result["error"]["details"][0]["hint"]

    # Verify NO step recorded
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 0

    execution_service.close()
