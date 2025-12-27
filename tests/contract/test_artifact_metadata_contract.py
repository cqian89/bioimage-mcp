from __future__ import annotations

from pathlib import Path

from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_image_metadata(tmp_path: Path) -> dict:
    repo_root = _repo_root()
    src = repo_root / "test_xr.ome.tiff"
    assert src.exists(), f"Missing test image: {src}"

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[repo_root],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    with ArtifactStore(config) as store:
        ref = store.import_file(src, artifact_type="BioImageRef", format="OME-TIFF")
    return ref.metadata


def test_artifact_metadata_has_required_fields(tmp_path: Path) -> None:
    metadata = _load_image_metadata(tmp_path)

    for key in ("shape", "dtype", "axes"):
        assert key in metadata, f"Expected '{key}' in artifact metadata"


def test_artifact_metadata_has_axes_inferred(tmp_path: Path) -> None:
    metadata = _load_image_metadata(tmp_path)

    assert "axes_inferred" in metadata
    assert isinstance(metadata["axes_inferred"], bool)


def test_artifact_metadata_has_file_metadata(tmp_path: Path) -> None:
    metadata = _load_image_metadata(tmp_path)

    assert "file_metadata" in metadata
    file_metadata = metadata["file_metadata"]
    assert isinstance(file_metadata, dict)
    assert "ome_xml_summary" in file_metadata
    assert "custom_attributes" in file_metadata


def test_artifact_metadata_has_physical_pixel_sizes(tmp_path: Path) -> None:
    metadata = _load_image_metadata(tmp_path)

    assert "physical_pixel_sizes" in metadata
    assert isinstance(metadata["physical_pixel_sizes"], dict)
