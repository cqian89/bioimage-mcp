import json
import sqlite3
from pathlib import Path

import pytest

from bioimage_mcp.api.execution import ExecutionService

# This import will fail until we create the file, but that is expected
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


def test_interactive_call_tool_success_flow(tmp_path: Path, monkeypatch) -> None:
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
resp = {
  'ok': True,
  'outputs': {
    'output': {
      'type': 'LogRef',
      'format': 'text',
      'path': req.get('work_dir', '.') + '/out.txt',
      'content': 'hello interactive',
    }
  },
  'log': 'ran interactive ok'
}
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
    tags: [test]
    inputs: []
    outputs:
      - name: output
        artifact_type: LogRef
        required: true
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

    # Verify manifest loading
    manifests, diags = load_manifests(config.tool_manifest_roots)
    assert not diags
    assert manifests

    # Initialize Services
    # ExecutionService initializes RunStore and ArtifactStore with config
    execution_service = ExecutionService(config)

    # SessionStore initializes DB with config (shared DB file)
    session_store = SessionStore(config)
    session_manager = SessionManager(session_store, config)

    # InteractiveExecutionService
    service = InteractiveExecutionService(session_manager, execution_service)

    # Create session
    session_id = "test_sess_01"
    session_manager.ensure_session(session_id)

    # --- Test Action 1: First Call ---
    result1 = service.call_tool(session_id=session_id, fn_id="fn.test", params={"p": 1}, inputs={})

    # Verify result 1
    assert result1["session_id"] == session_id
    assert "step_id" in result1
    assert result1["outputs"]["output"]["content"] == "hello interactive"

    # Verify step 0 recorded
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 1
    step0 = steps[0]
    assert step0.ordinal == 0
    assert step0.fn_id == "fn.test"
    assert step0.status == "succeeded"

    # --- Test Action 2: Second Call ---
    result2 = service.call_tool(session_id=session_id, fn_id="fn.test", params={"p": 2}, inputs={})

    # Verify result 2
    assert result2["session_id"] == session_id
    assert result2["step_id"] != result1["step_id"]

    # Verify step 1 recorded
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 2
    step1 = steps[1]
    assert step1.ordinal == 1
    assert step1.fn_id == "fn.test"

    # Cleanup
    execution_service.close()
