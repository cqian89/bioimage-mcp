from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def _assert_no_pixel_arrays(payload: object) -> None:
    if isinstance(payload, dict):
        forbidden_keys = {"pixels", "pixel_data", "image", "label_image", "array", "ndarray"}
        for key, value in payload.items():
            key_str = str(key).lower()
            assert key_str not in forbidden_keys
            _assert_no_pixel_arrays(value)
        return

    if isinstance(payload, list | tuple):
        for value in payload:
            _assert_no_pixel_arrays(value)
        return


def test_run_workflow_payload_contains_refs_only(tmp_path: Path, monkeypatch) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        lambda **_kw: (
            {
                "ok": True,
                "outputs": {
                    "labels": {
                        "type": "LabelImageRef",
                        "format": "ome-tiff",
                        "path": str(tmp_path / "x.tif"),
                    }
                },
            },
            "log",
            0,
        ),
    )

    (tmp_path / "x.tif").write_bytes(b"not_a_real_tiff_but_fine_for_contract_test")

    svc = ExecutionService(config, artifact_store=store)
    resp = svc.run_workflow({"steps": [{"fn_id": "fn.one", "params": {}, "inputs": {}}]})
    _assert_no_pixel_arrays(resp)
