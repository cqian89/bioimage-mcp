from pathlib import Path

import numpy as np
from bioio.writers import OmeTiffWriter

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def _write_test_ome_tiff(path: Path) -> None:
    data = np.zeros((1, 1, 1, 4, 4), dtype=np.uint8)
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")


def _write_test_manifest(tool_root: Path, entrypoint: Path) -> None:
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
  - fn_id: fn.success
    tool_id: tools.test
    name: Success
    description: Success
    tags: [test]
    inputs: []
    outputs:
      - name: output
        artifact_type: LogRef
        required: true
    params_schema: {{type: object}}
    hints:
      success_hints:
        next_steps:
          - id: base.next
            reason: "Continue with next step"
        common_issues:
          - "Watch for downstream validation"
  - fn_id: fn.fail
    tool_id: tools.test
    name: Fail
    description: Fail
    tags: [test]
    inputs:
      - name: image
        artifact_type: BioImageRef
        required: true
    outputs: []
    params_schema: {{type: object}}
    hints:
      error_hints:
        GENERAL:
          diagnosis: "Input axes do not match expected order."
          suggested_fix:
            id: base.relabel_axes
            params:
              axis_mapping:
                Z: "T"
                T: "Z"
            explanation: "Relabel axes before retrying."
""".lstrip()
    )


def _make_config(tmp_path: Path, tool_root: Path) -> Config:
    return Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )


def test_run_workflow_success_includes_hints(tmp_path: Path, monkeypatch) -> None:
    tool_root = tmp_path / "tools"
    tool_root.mkdir()
    entrypoint = tmp_path / "entrypoint.py"
    entrypoint.write_text("print('unused')\n")
    _write_test_manifest(tool_root, entrypoint)

    config = _make_config(tmp_path, tool_root)

    def _fake_execute_step(**kwargs):
        work_dir = Path(kwargs["work_dir"])
        output_path = work_dir / "out.txt"
        return (
            {
                "ok": True,
                "outputs": {
                    "output": {
                        "type": "LogRef",
                        "format": "text",
                        "path": str(output_path),
                        "content": "ok",
                    }
                },
            },
            "ok",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _fake_execute_step)

    with ExecutionService(config) as svc:
        response = svc.run_workflow({"steps": [{"id": "fn.success", "params": {}, "inputs": {}}]})

    assert response["status"] == "success"
    assert response["hints"]["next_steps"]
    assert response["hints"]["common_issues"]


def test_run_workflow_error_includes_hints(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "test_xr.ome.tiff"
    _write_test_ome_tiff(image_path)

    tool_root = tmp_path / "tools"
    tool_root.mkdir()
    entrypoint = tmp_path / "entrypoint.py"
    entrypoint.write_text("print('unused')\n")
    _write_test_manifest(tool_root, entrypoint)

    config = _make_config(tmp_path, tool_root)

    with ArtifactStore(config) as store:
        ref = store.import_file(image_path, artifact_type="BioImageRef", format="OME-TIFF")

        def _fake_execute_step(**_kwargs):
            return ({"ok": False, "error": {"message": "boom"}}, "log", 1)

        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _fake_execute_step)

        svc = ExecutionService(config, artifact_store=store)
        response = svc.run_workflow(
            {
                "steps": [
                    {
                        "id": "fn.fail",
                        "params": {},
                        "inputs": {"image": {"ref_id": ref.ref_id}},
                    }
                ]
            }
        )

    assert response["status"] == "failed"
    assert response["hints"]["diagnosis"] == "Input axes do not match expected order."
    assert response["hints"]["suggested_fix"]["id"] == "base.relabel_axes"
    assert response["hints"]["related_metadata"]["image"] == ref.metadata
