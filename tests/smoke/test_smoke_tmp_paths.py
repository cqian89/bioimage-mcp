from __future__ import annotations

from pathlib import Path

from bioimage_mcp.config.loader import load_config


def test_smoke_tmp_dir_uses_artifact_store_root(smoke_tmp_dir):
    """Smoke temp files should live under the artifact store work area."""
    config = load_config()
    resolved_tmp = smoke_tmp_dir.resolve()
    artifact_work_root = (config.artifact_store_root / "work").resolve()
    repo_smoke_tmp = (Path.cwd() / "datasets" / "smoke_tmp").resolve()

    assert resolved_tmp.is_relative_to(artifact_work_root)
    assert resolved_tmp != repo_smoke_tmp
    assert not resolved_tmp.is_relative_to(Path.cwd() / "datasets")
