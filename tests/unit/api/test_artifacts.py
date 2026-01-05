from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_artifacts_service_artifact_info(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    src = tmp_path / "test.txt"
    src.write_text("Hello World!")

    with ArtifactStore(config) as store:
        ref = store.import_file(src, artifact_type="LogRef", format="text")
        svc = ArtifactsService(store)

        # Test artifact_info with preview
        info = svc.artifact_info(ref.ref_id, text_preview_bytes=5)
        assert info["ref_id"] == ref.ref_id
        assert info["type"] == "LogRef"
        assert info["text_preview"] == "Hello"
        assert info["mime_type"] == "text/plain"
        assert len(info["checksums"]) > 0

        # Test artifact_info without preview
        info = svc.artifact_info(ref.ref_id)
        assert "text_preview" not in info

        # Test artifact_info not found
        info = svc.artifact_info("missing")
        assert info["error"]["code"] == "NOT_FOUND"
