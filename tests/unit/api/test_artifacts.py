from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_artifacts_service_get_artifact(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    src = tmp_path / "test.txt"
    src.write_text("content")

    with ArtifactStore(config) as store:
        ref = store.import_file(src, artifact_type="LogRef", format="text")

        svc = ArtifactsService(store)

        # Test get_artifact
        payload = svc.get_artifact(ref.ref_id)
        assert "ref" in payload
        assert payload["ref"]["ref_id"] == ref.ref_id
        assert payload["ref"]["type"] == "LogRef"
