from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


def test_interactive_tool_error(tmp_path: Path, monkeypatch) -> None:
    # Setup directories
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    tool_root.mkdir()

    # Create failing tool entrypoint and manifest
    entrypoint = tmp_path / "fail_tool.py"
    entrypoint.write_text(
        """
import json
import sys

print(json.dumps({'command': 'ready', 'version': '0.1'}), flush=True)

for line in sys.stdin:
    if not line.strip():
        continue
    req = json.loads(line)
    if req.get('command') != 'execute':
        resp = {
            'command': 'execute_result',
            'ok': False,
            'ordinal': req.get('ordinal'),
            'error': {'code': 'bad_command', 'message': 'unsupported command'},
        }
        print(json.dumps(resp), flush=True)
        continue

    resp = {
        'command': 'execute_result',
        'ok': False,
        'ordinal': req.get('ordinal'),
        'error': {'code': 'tool_failed', 'message': 'intentional failure'},
    }
    print(json.dumps(resp), flush=True)
""".lstrip()
    )

    (tool_root / "manifest.yaml").write_text(
        f"""
manifest_version: '0.0'
tool_id: tools.fail
tool_version: '0.0.0'
name: Fail
description: Fail tool
env_id: bioimage-mcp-base
entrypoint: {entrypoint}
platforms_supported: [linux-64]
functions:
  - fn_id: fn.fail
    tool_id: tools.fail
    name: Fail
    description: Fail
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

    # Services
    execution_service = ExecutionService(config)
    session_store = SessionStore(config)
    session_manager = SessionManager(session_store, config)
    service = InteractiveExecutionService(session_manager, execution_service)

    # Create session
    session_id = "sess_error_01"
    session_manager.ensure_session(session_id)

    # Call tool
    result = service.call_tool(session_id=session_id, fn_id="fn.fail", params={}, inputs={})

    # Verify result
    assert result["status"] == "failed"
    assert "error" in result
    assert result["error"] is not None
    assert result["error"].get("code") == "tool_failed"

    # Verify session step recorded as failed
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 1
    step = steps[0]
    assert step.fn_id == "fn.fail"
    assert step.status == "failed"
    assert step.error is not None

    # Cleanup
    execution_service.close()
