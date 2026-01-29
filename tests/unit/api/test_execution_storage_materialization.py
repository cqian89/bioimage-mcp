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


def test_run_workflow_resolves_ref_id_to_full_artifact(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(manifest_dir, ["file"])
    config = _build_config(tmp_path, manifest_dir)

    config.artifact_store_root.mkdir(parents=True, exist_ok=True)
    source = config.artifact_store_root / "input.txt"
    source.write_text("data")

    with ExecutionService(config) as svc:
        ref = svc.artifact_store.import_file(source, artifact_type="BioImageRef", format="text")
        inputs = {"image": {"ref_id": ref.ref_id}}

        captured: dict[str, object] = {}

        def _fake_execute_step(*, inputs: dict, **kwargs):
            captured["inputs"] = inputs
            return {"ok": True, "outputs": {}, "provenance": {}}, "ok", 0

        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _fake_execute_step)

        result = svc.run_workflow(
            {"steps": [{"id": "storage.fn", "inputs": inputs, "params": {}}]},
            skip_validation=True,
        )

        assert result["status"] == "success"
        assert captured["inputs"]["image"]["ref_id"] == ref.ref_id
        assert captured["inputs"]["image"]["uri"] == ref.uri


def test_run_workflow_materializes_zarr_temp_input(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(manifest_dir, ["file"])
    config = _build_config(tmp_path, manifest_dir)

    config.artifact_store_root.mkdir(parents=True, exist_ok=True)
    source = config.artifact_store_root / "input.txt"
    source.write_text("data")

    with ExecutionService(config) as svc:
        ref = svc.artifact_store.import_file(source, artifact_type="BioImageRef", format="text")
        inputs = {"image": {**ref.model_dump(), "storage_type": "zarr-temp"}}

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

        def _fake_execute_step(*, inputs: dict, **kwargs):
            captured["inputs"] = inputs
            return {"ok": True, "outputs": {}, "provenance": {}}, "ok", 0

        monkeypatch.setattr(
            "bioimage_mcp.api.execution._materialize_zarr_to_file", _fake_materialize
        )
        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _fake_execute_step)

        result = svc.run_workflow(
            {"steps": [{"id": "storage.fn", "inputs": inputs, "params": {}}]},
            skip_validation=True,
        )

        assert result["status"] == "success"
        assert captured["inputs"]["image"]["ref_id"] == "mat1"

        run = svc._run_store.get(result["run_id"])
        assert run.provenance["materialized_inputs"] == {"image": ref.ref_id}


def test_run_workflow_skips_materialization_when_supported(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(manifest_dir, ["file", "zarr-temp"])
    config = _build_config(tmp_path, manifest_dir)

    config.artifact_store_root.mkdir(parents=True, exist_ok=True)
    source = config.artifact_store_root / "input.txt"
    source.write_text("data")

    with ExecutionService(config) as svc:
        ref = svc.artifact_store.import_file(source, artifact_type="BioImageRef", format="text")
        inputs = {"image": {**ref.model_dump(), "storage_type": "zarr-temp"}}

        called = {"materialize": False}

        def _fake_materialize(*args, **kwargs) -> dict:
            called["materialize"] = True
            return {}

        def _fake_execute_step(*, inputs: dict, **kwargs):
            return {"ok": True, "outputs": {}, "provenance": {}}, "ok", 0

        monkeypatch.setattr(
            "bioimage_mcp.api.execution._materialize_zarr_to_file", _fake_materialize
        )
        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _fake_execute_step)

        result = svc.run_workflow(
            {"steps": [{"id": "storage.fn", "inputs": inputs, "params": {}}]},
            skip_validation=True,
        )

        assert result["status"] == "success"
        assert called["materialize"] is False
