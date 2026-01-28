from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


def test_interactive_retry_canonical(tmp_path: Path, monkeypatch) -> None:
    # Setup directories
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    tool_root.mkdir()

    # Create flaky tool entrypoint and manifest
    # Fails if state file doesn't exist, succeeds if it does
    entrypoint = tmp_path / "flaky_tool.py"
    state_file = tmp_path / "state.txt"
    entrypoint.write_text(
        f"""
import json
import sys
from pathlib import Path

state_file = Path("{state_file}")

print(json.dumps({{'command': 'ready', 'version': '0.1'}}), flush=True)

for line in sys.stdin:
    if not line.strip():
        continue
    req = json.loads(line)
    if req.get('command') != 'execute':
        resp = {{
            'command': 'execute_result',
            'ok': False,
            'ordinal': req.get('ordinal'),
            'error': {{'code': 'bad_command', 'message': 'unsupported command'}},
        }}
        print(json.dumps(resp), flush=True)
        continue

    if not state_file.exists():
        state_file.write_text('1')
        resp = {{
            'command': 'execute_result',
            'ok': False,
            'ordinal': req.get('ordinal'),
            'error': {{'code': 'tool_failed', 'message': 'transient failure'}},
        }}
    else:
        resp = {{
            'command': 'execute_result',
            'ok': True,
            'ordinal': req.get('ordinal'),
            'outputs': {{}},
            'log': 'success',
        }}
    print(json.dumps(resp), flush=True)
""".lstrip()
    )

    (tool_root / "manifest.yaml").write_text(
        f"""
manifest_version: '0.0'
tool_id: tools.flaky
tool_version: '0.0.0'
name: Flaky
description: Flaky tool
env_id: bioimage-mcp-base
entrypoint: {entrypoint}
platforms_supported: [linux-64]
functions:
  - fn_id: fn.flaky
    tool_id: tools.flaky
    name: Flaky
    description: Flaky
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
    session_id = "sess_retry_01"
    session_manager.ensure_session(session_id)

    # Attempt 1: Should fail
    # Note: explicit ordinal=0 to indicate we are working on Step 0
    try:
        result1 = service.call_tool(
            session_id=session_id, fn_id="fn.flaky", params={}, inputs={}, ordinal=0
        )
    except TypeError:
        # If ordinal not supported yet, catch for now or fail?
        # TDD: We WANT it to fail or we assert expectations.
        # For now, let's call it and assert result.
        # If API doesn't support ordinal, this test will Error, which is Correct (Red phase).
        result1 = service.call_tool(
            session_id=session_id, fn_id="fn.flaky", params={}, inputs={}, ordinal=0
        )

    assert result1["status"] == "failed"

    # Check step 0 exists and is canonical (only one attempt so far)
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 1
    attempt1 = steps[0]
    assert attempt1.ordinal == 0
    assert attempt1.status == "failed"
    # Canonical is False because the run failed
    assert attempt1.canonical is False

    # Attempt 2: Should succeed (state file now exists)
    # Retry Step 0
    result2 = service.call_tool(
        session_id=session_id, fn_id="fn.flaky", params={}, inputs={}, ordinal=0
    )

    assert result2["status"] == "success"

    # Check attempts
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 2

    # Sort by stored order or ID? usually list_step_attempts returns in order of creation
    a1, a2 = steps

    assert a1.ordinal == 0
    assert a2.ordinal == 0

    # Verify canonical switch
    # Previous failed attempt should now be non-canonical
    assert a1.canonical is False
    # New successful attempt should be canonical
    assert a2.canonical is True

    # Cleanup
    execution_service.close()
