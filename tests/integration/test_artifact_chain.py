"""Integration test for artifact chain: load -> consume -> export.

Validates that artifacts stored by the MCP server can be read by downstream
functions. This is the critical test for the file extension fix.
"""

from __future__ import annotations

import pytest
from pathlib import Path

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestArtifactChain:
    """Test that artifacts flow correctly through the MCP pipeline."""

    @pytest.fixture
    def test_image_path(self) -> Path:
        """Path to a test TIFF image."""
        # Use the FLUTE FLIM dataset that revealed the bug
        dataset_path = Path(__file__).parent.parent.parent / "datasets" / "FLUTE_FLIM_data_tif"
        tif_path = dataset_path / "hMSC control.tif"
        if not tif_path.exists():
            pytest.skip(f"Test dataset not found: {tif_path}")
        return tif_path

    def test_load_artifact_has_extension(self, test_image_path: Path, tmp_path: Path):
        """Loaded artifacts should have file extensions in their storage path."""
        from bioimage_mcp.config.schema import Config
        from bioimage_mcp.artifacts.store import ArtifactStore

        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[],
            fs_allowlist_read=[test_image_path.parent],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        with ArtifactStore(config) as store:
            ref = store.import_file(
                test_image_path,
                artifact_type="BioImageRef",
                format="TIFF",
            )

            # Verify the stored artifact has the correct extension
            artifact_path = Path(ref.uri.replace("file://", ""))
            assert artifact_path.suffix == ".tif", (
                f"Expected .tif extension, got: {artifact_path.name}"
            )
            assert artifact_path.exists(), f"Artifact file should exist: {artifact_path}"

    def test_artifact_readable_by_bioimage(self, test_image_path: Path, tmp_path: Path):
        """Stored artifacts should be readable by BioImage without symlink workarounds."""
        from bioio import BioImage
        from bioimage_mcp.config.schema import Config
        from bioimage_mcp.artifacts.store import ArtifactStore

        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[],
            fs_allowlist_read=[test_image_path.parent],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        with ArtifactStore(config) as store:
            ref = store.import_file(
                test_image_path,
                artifact_type="BioImageRef",
                format="TIFF",
            )

            # This is the critical test: BioImage should be able to read the artifact
            artifact_path = Path(ref.uri.replace("file://", ""))

            # This should NOT raise "BioImage does not support the image"
            img = BioImage(artifact_path)
            data = img.data

            assert data is not None
            assert len(data.shape) >= 2  # At least 2D image

    def test_full_artifact_chain(self, test_image_path: Path, tmp_path: Path):
        """Full chain: import -> read artifact -> verify data matches."""
        from bioio import BioImage
        from bioimage_mcp.config.schema import Config
        from bioimage_mcp.artifacts.store import ArtifactStore

        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[],
            fs_allowlist_read=[test_image_path.parent],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        # Load original image
        original_img = BioImage(test_image_path)
        original_shape = original_img.data.shape

        with ArtifactStore(config) as store:
            # Import as artifact
            ref = store.import_file(
                test_image_path,
                artifact_type="BioImageRef",
                format="TIFF",
            )

            # Read artifact and verify shape matches
            artifact_path = Path(ref.uri.replace("file://", ""))
            artifact_img = BioImage(artifact_path)
            artifact_shape = artifact_img.data.shape

            assert artifact_shape == original_shape, (
                f"Shape mismatch: original {original_shape} vs artifact {artifact_shape}"
            )
