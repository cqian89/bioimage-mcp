from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_artifact_store_persists_file_and_metadata(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    read_root = tmp_path / "data"
    read_root.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[read_root],
        fs_allowlist_write=[artifact_root],
        fs_denylist=[],
    )

    src = read_root / "in.txt"
    src.write_text("hello")

    with ArtifactStore(config) as store:
        ref = store.import_file(src, artifact_type="BioImageRef", format="text")

        loaded = store.get(ref.ref_id)
        assert loaded.ref_id == ref.ref_id
        assert loaded.size_bytes == 5
        assert loaded.checksums[0].algorithm in {"sha256", "sha256-tree"}


def test_artifact_store_exports_and_verifies_checksum(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    tool_root = tmp_path / "tools"
    read_root = tmp_path / "data"
    export_root = tmp_path / "exports"
    read_root.mkdir()
    export_root.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[tool_root],
        fs_allowlist_read=[read_root],
        fs_allowlist_write=[artifact_root, export_root],
        fs_denylist=[],
    )

    src = read_root / "in.txt"
    src.write_text("hello")

    with ArtifactStore(config) as store:
        ref = store.import_file(src, artifact_type="LogRef", format="text")

        dest = export_root / "out.txt"
        exported_path = store.export(ref.ref_id, dest)

        assert exported_path == dest
        assert dest.read_text() == "hello"
