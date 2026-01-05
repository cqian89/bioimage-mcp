from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_run_workflow_contract_shape(tmp_path: Path, monkeypatch) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    store = ArtifactStore(config)

    # Make executor deterministic for contract test.
    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        lambda **_kw: ({"ok": True, "outputs": {}}, "log1", 0),
    )

    svc = ExecutionService(config, artifact_store=store)
    response = svc.run_workflow({"steps": [{"fn_id": "fn.one", "params": {}, "inputs": {}}]})

    allowed_keys = {
        "run_id",
        "status",
        "workflow_record_ref_id",
        "hints",
        "session_id",
        "id",
        "outputs",
        "log_ref",
        "warnings",
        "error",
    }
    # workflow_record_ref_id might be inside outputs or native output ref, checking essential keys
    required_keys = {"run_id", "status", "outputs"}
    assert required_keys.issubset(response.keys())
    assert set(response.keys()).issubset(allowed_keys)


def test_get_artifact_contract_shape(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    store = ArtifactStore(config)
    src = tmp_path / "in.txt"
    src.write_text("hello")
    ref = store.import_file(src, artifact_type="LogRef", format="text")

    payload = store.get_payload(ref.ref_id)
    assert set(payload.keys()) == {"ref"}
    assert payload["ref"]["ref_id"] == ref.ref_id
