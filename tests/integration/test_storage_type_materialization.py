from __future__ import annotations

from pathlib import Path

import yaml

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config


def _write_manifest(manifest_dir: Path, supported_storage_types: list[str]) -> None:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "manifest_version": "0.0",
                "tool_id": "tools.storage",
                "tool_version": "0.1.0",
                "name": "Storage Tool",
                "description": "Tool for storage tests",
                "env_id": "bioimage-mcp-storage",
                "entrypoint": "storage/entrypoint.py",
                "functions": [
                    {
                        "id": "storage.fn",
                        "tool_id": "tools.storage",
                        "name": "Storage Function",
                        "description": "Function for storage tests",
                        "tags": ["test"],
                        "inputs": [
                            {
                                "name": "image",
                                "artifact_type": "BioImageRef",
                                "required": True,
                                "description": "Input image",
                            }
                        ],
                        "outputs": [
                            {
                                "name": "output",
                                "artifact_type": "BioImageRef",
                                "required": True,
                                "description": "Output image",
                            }
                        ],
                        "params_schema": {"type": "object", "properties": {}},
                        "hints": {
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "required": True,
                                    "description": "Input image",
                                    "supported_storage_types": supported_storage_types,
                                }
                            }
                        },
                    }
                ],
            }
        )
    )


def _build_config(tmp_path: Path, manifest_dir: Path) -> Config:
    return Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[manifest_dir],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )


def test_materializes_zarr_temp_input_to_file(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(manifest_dir, ["file"])

    config = _build_config(tmp_path, manifest_dir)
    config.artifact_store_root.mkdir(parents=True, exist_ok=True)

    zarr_root = tmp_path / "input.zarr"
    zarr_root.mkdir()
    (zarr_root / "data.txt").write_text("zarr")

    captured: dict[str, object] = {}

    def _fake_materialize(artifact_ref: dict, work_dir: Path, artifact_store) -> dict:
        captured["materialize"] = artifact_ref
        return {
            "ref_id": "mat1",
            "type": "BioImageRef",
            "uri": (work_dir / "materialized.ome.zarr").as_uri(),
            "format": "OME-Zarr",
            "storage_type": "file",
        }

    def _fake_execute_step(*, inputs: dict, **_kwargs):
        captured["inputs"] = inputs
        return {"ok": True, "outputs": {}, "provenance": {}}, "ok", 0

    monkeypatch.setattr("bioimage_mcp.api.execution._materialize_zarr_to_file", _fake_materialize)
    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _fake_execute_step)

    with ExecutionService(config) as svc:
        ref = svc.artifact_store.import_directory(
            zarr_root, artifact_type="BioImageRef", format="OME-ZARR"
        )
        inputs = {"image": ref.model_dump()}

        result = svc.run_workflow(
            {"steps": [{"id": "storage.fn", "inputs": inputs, "params": {}}]},
            skip_validation=True,
        )

    assert result["status"] == "success"
    assert captured["materialize"]["storage_type"] == "zarr-temp"
    assert captured["inputs"]["image"]["storage_type"] == "file"
