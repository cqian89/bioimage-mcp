from __future__ import annotations

from pathlib import Path

import numpy as np
from bioio.writers import OmeTiffWriter

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def _write_test_ome_tiff(path: Path) -> None:
    data = np.zeros((1, 1, 1, 4, 4), dtype=np.uint8)
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")


def test_run_workflow_error_includes_input_metadata(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "test_xr.ome.tiff"
    _write_test_ome_tiff(image_path)

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
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
                        "id": "fn.fail",
                        "params": {},
                        "inputs": {"image": {"ref_id": ref.ref_id}},
                    }
                ]
            }
        )

    assert response["status"] == "failed"
    assert response["hints"]["related_metadata"]["image"] == ref.metadata
