from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config


def test_run_workflow_uses_run_scoped_work_dir(tmp_path: Path, monkeypatch) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    (tmp_path / "tools").mkdir()

    captured = {}

    def _fake_execute_step(*, work_dir: Path, **kwargs):
        captured["work_dir"] = work_dir
        return {"ok": True, "outputs": {}}, "ok", 0

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _fake_execute_step)

    with ExecutionService(config) as svc:
        result = svc.run_workflow(
            {"steps": [{"fn_id": "base.project_sum", "inputs": {}, "params": {}}]},
            skip_validation=True,
        )

        assert result["status"] == "succeeded"
        assert "work_dir" in captured
        expected_root = config.artifact_store_root / "work" / "runs" / result["run_id"]
        assert captured["work_dir"] == expected_root
