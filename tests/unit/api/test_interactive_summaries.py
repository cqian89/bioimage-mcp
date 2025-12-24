from __future__ import annotations

import pytest
from bioimage_mcp.artifacts.models import ArtifactRef


class TestSummarizeArtifact:
    """Tests for summarize_artifact function."""

    def test_summarize_bioimage_with_metadata(self) -> None:
        """Should return full summary for BioImageRef with metadata."""
        from bioimage_mcp.api.interactive_summaries import summarize_artifact

        ref = ArtifactRef(
            ref_id="img1",
            type="BioImageRef",
            uri="file:///tmp/img1.tif",
            format="OME-TIFF",
            mime_type="image/tiff",
            size_bytes=1024,
            created_at=ArtifactRef.now(),
            metadata={"shape": [10, 20, 30], "dtype": "uint16"},
        )

        summary = summarize_artifact(ref)

        assert summary == {
            "type": "BioImageRef",
            "size_bytes": 1024,
            "shape": [10, 20, 30],
            "dtype": "uint16",
        }

    def test_summarize_labelimage_with_metadata(self) -> None:
        """Should return full summary for LabelImageRef with metadata."""
        from bioimage_mcp.api.interactive_summaries import summarize_artifact

        ref = ArtifactRef(
            ref_id="lbl1",
            type="LabelImageRef",
            uri="file:///tmp/lbl1.tif",
            format="OME-TIFF",
            mime_type="image/tiff",
            size_bytes=2048,
            created_at=ArtifactRef.now(),
            metadata={"shape": [512, 512], "dtype": "uint8"},
        )

        summary = summarize_artifact(ref)

        assert summary == {
            "type": "LabelImageRef",
            "size_bytes": 2048,
            "shape": [512, 512],
            "dtype": "uint8",
        }

    def test_summarize_generic_artifact(self) -> None:
        """Should return basic summary for generic artifacts."""
        from bioimage_mcp.api.interactive_summaries import summarize_artifact

        ref = ArtifactRef(
            ref_id="doc1",
            type="TextFile",
            uri="file:///tmp/doc1.txt",
            format="text/plain",
            mime_type="text/plain",
            size_bytes=500,
            created_at=ArtifactRef.now(),
        )

        summary = summarize_artifact(ref)

        assert summary == {"type": "TextFile", "size_bytes": 500}

    def test_summarize_bioimage_missing_metadata(self) -> None:
        """Should handle missing metadata for BioImageRef gracefully."""
        from bioimage_mcp.api.interactive_summaries import summarize_artifact

        ref = ArtifactRef(
            ref_id="img2",
            type="BioImageRef",
            uri="file:///tmp/img2.tif",
            format="OME-TIFF",
            mime_type="image/tiff",
            size_bytes=2048,
            created_at=ArtifactRef.now(),
            metadata={},
        )

        summary = summarize_artifact(ref)

        # Should fall back to generic summary if metadata is missing
        assert summary == {"type": "BioImageRef", "size_bytes": 2048}

    def test_summarize_bioimage_partial_metadata(self) -> None:
        """Should handle partial metadata for BioImageRef."""
        from bioimage_mcp.api.interactive_summaries import summarize_artifact

        ref = ArtifactRef(
            ref_id="img3",
            type="BioImageRef",
            uri="file:///tmp/img3.tif",
            format="OME-TIFF",
            mime_type="image/tiff",
            size_bytes=4096,
            created_at=ArtifactRef.now(),
            metadata={
                "shape": [100, 100]
                # dtype missing
            },
        )

        summary = summarize_artifact(ref)

        # Should include what's available
        assert summary["type"] == "BioImageRef"
        assert summary["size_bytes"] == 4096
        assert summary["shape"] == [100, 100]
        assert "dtype" not in summary
