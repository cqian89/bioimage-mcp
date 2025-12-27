from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_run_workflow_error_includes_input_metadata(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_root()
    image_path = repo_root / "test_xr.ome.tiff"
    assert image_path.exists(), f"Missing test image: {image_path}"

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[repo_root],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    with ArtifactStore(config) as store:
        ref = store.import_file(image_path, artifact_type="BioImageRef", format="OME-TIFF")

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            lambda **_kw: ({"ok": False, "error": {"message": "boom"}}, "log", 1),
        )

        svc = ExecutionService(config, artifact_store=store)
        response = svc.run_workflow(
            {
                "steps": [
                    {
                        "fn_id": "fn.fail",
                        "params": {},
                        "inputs": {"image": {"ref_id": ref.ref_id}},
                    }
                ]
            }
        )

    assert response["status"] == "failed"
    assert "input_metadata" in response
    assert response["input_metadata"]["image"] == ref.metadata
