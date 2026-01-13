from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioimage_mcp.artifacts.models import ArtifactRef


def test_validate_dimension_consistency_ndim() -> None:
    # ndim (3) does not match shape length (2)
    with pytest.raises(ValidationError, match="shape length.*ndim"):
        ArtifactRef(
            ref_id="test",
            type="BioImageRef",
            uri="file:///test.tif",
            format="OME-TIFF",
            mime_type="image/tiff",
            size_bytes=0,
            created_at="2025-01-01T00:00:00Z",
            metadata={"shape": [10, 20], "ndim": 3, "dims": ["Y", "X"]},
        )


def test_validate_dimension_consistency_dims() -> None:
    # dims length (3) does not match shape length (2)
    with pytest.raises(ValidationError, match="shape length.*dims length"):
        ArtifactRef(
            ref_id="test",
            type="BioImageRef",
            uri="file:///test.tif",
            format="OME-TIFF",
            mime_type="image/tiff",
            size_bytes=0,
            created_at="2025-01-01T00:00:00Z",
            metadata={"shape": [10, 20], "ndim": 2, "dims": ["Y", "X", "Z"]},
        )


def test_validate_valid_dimensions() -> None:
    # This should pass once implemented
    ArtifactRef(
        ref_id="test",
        type="BioImageRef",
        uri="file:///test.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=0,
        created_at="2025-01-01T00:00:00Z",
        metadata={"shape": [10, 20], "ndim": 2, "dims": ["Y", "X"]},
    )
