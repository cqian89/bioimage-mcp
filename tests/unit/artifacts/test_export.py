from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.export import export_artifact
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_export_artifact_exports_file(tmp_path: Path) -> None:
    """Test that export_artifact correctly wraps store.export()."""
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    with ArtifactStore(config) as store:
        # Create a test file and import it
        src = tmp_path / "test.txt"
        src.write_text("test content")
        ref = store.import_file(src, artifact_type="LogRef", format="text")

        # Export using the export_artifact function
        dest = tmp_path / "exported.txt"
        result = export_artifact(store, ref_id=ref.ref_id, dest_path=dest)

        assert result == dest
        assert dest.exists()
        assert dest.read_text() == "test content"


def test_export_artifact_rejects_conversion(tmp_path: Path) -> None:
    """Test that export_artifact rejects format conversion."""
    import pytest

    from bioimage_mcp.errors import ArtifactStoreError

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
    )

    with ArtifactStore(config) as store:
        src = tmp_path / "test.tiff"
        src.write_text("dummy")
        ref = store.import_file(src, artifact_type="BioImageRef", format="TIFF")

        dest = tmp_path / "exported.png"
        with pytest.raises(ArtifactStoreError, match="Format conversion not supported in core"):
            export_artifact(store, ref_id=ref.ref_id, dest_path=dest, format="PNG")
