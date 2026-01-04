from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_get_artifact_includes_dimension_metadata(tmp_path: Path) -> None:
    """T024: get_artifact response includes dimension metadata fields."""
    # Given an artifact stored in the system
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
    )

    # 1. Test Image Artifact
    image_path = tmp_path / "test.tiff"
    data = np.zeros((1, 2, 3, 4, 5), dtype=np.uint16)
    tifffile.imwrite(image_path, data)

    with ArtifactStore(config) as store:
        ref = store.import_file(image_path, artifact_type="BioImageRef", format="OME-TIFF")
        service = ArtifactsService(store)

        # When get_artifact is called
        response = service.get_artifact(ref.ref_id)

        # Then response includes ndim, dims, shape in metadata
        artifact_ref = response["ref"]
        metadata = artifact_ref["metadata"]

        assert "ndim" in metadata
        assert "dims" in metadata
        assert "shape" in metadata
        assert metadata["ndim"] == 5
        assert list(metadata["shape"]) == [1, 2, 3, 4, 5]

    # 2. Test Table Artifact
    table_path = tmp_path / "test.csv"
    table_path.write_text("label,area\n1,100\n2,200\n")

    with ArtifactStore(config) as store:
        ref = store.import_file(table_path, artifact_type="TableRef", format="csv")
        service = ArtifactsService(store)

        response = service.get_artifact(ref.ref_id)
        metadata = response["ref"]["metadata"]

        # This is expected to fail as TableRef metadata extraction is not implemented
        assert "columns" in metadata
        assert "row_count" in metadata
