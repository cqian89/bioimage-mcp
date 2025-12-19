from __future__ import annotations

from pathlib import Path

from bioimage_mcp.config.schema import Config
from bioimage_mcp.runs.store import RunStore


def test_run_store_sets_native_output_ref(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
    )
    store = RunStore(config)
    run = store.create_run(
        workflow_spec={"steps": []},
        inputs={},
        params={},
        provenance={},
        log_ref_id="log",
    )

    store.set_native_output_ref(run.run_id, "ref-123")
    loaded = store.get(run.run_id)
    assert loaded.native_output_ref_id == "ref-123"
