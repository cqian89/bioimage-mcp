from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests


def test_run_workflow_e2e_with_test_toolpack(tmp_path: Path, monkeypatch) -> None:
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    tool_root.mkdir()

    # Create a minimal tool entrypoint script that echoes a produced artifact.
    entrypoint = tmp_path / "tool_entrypoint.py"
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

    # Return a fake output ref + log metadata
    resp = {
        'command': 'execute_result',
        'ok': True,
        'ordinal': req.get('ordinal'),
        'outputs': {
            'output': {
                'type': 'LogRef',
                'format': 'text',
                'path': req.get('work_dir', '.') + '/out.txt',
                'content': 'hello',
            }
        },
        'log': 'ran ok',
    }
    print(json.dumps(resp), flush=True)
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

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    # Avoid calling micromamba/conda in tests.
    monkeypatch.setattr("bioimage_mcp.runtimes.executor.detect_env_manager", lambda: None)

    # Ensure registry can load the tool manifest.
    manifests, diags = load_manifests(config.tool_manifest_roots)
    assert not diags
    assert manifests

    with ExecutionService(config) as svc:
        resp = svc.run_workflow({"steps": [{"id": "fn.test", "params": {}, "inputs": {}}]})
        assert resp["status"] in {"queued", "running", "success"}

        status = svc.get_run_status(resp["run_id"])
        assert status["status"] in {"running", "success", "failed"}
        assert "log_ref" in status
