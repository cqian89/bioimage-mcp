from __future__ import annotations

from pathlib import Path

from bioimage_mcp.config.schema import Config
from bioimage_mcp.runs.store import RunStore


def test_run_store_lifecycle(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    with RunStore(config) as store:
        run = store.create_run(
            workflow_spec={"steps": [{"fn_id": "fn.one"}]},
            inputs={},
            params={},
            provenance={"tool_id": "t", "tool_version": "0", "fn_id": "fn.one", "env_id": "e"},
            log_ref_id="log1",
        )

        assert run.status == "queued"

        store.set_status(run.run_id, "running")
        store.set_status(run.run_id, "succeeded", outputs={"out": {"ref_id": "a"}})

        loaded = store.get(run.run_id)
        assert loaded.status == "succeeded"
        assert loaded.outputs and "out" in loaded.outputs
