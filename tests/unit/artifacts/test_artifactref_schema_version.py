"""Unit tests for ArtifactRef schema_version field (T008b).

Tests that ArtifactRef includes schema_version for artifact format versioning.
"""

from __future__ import annotations

from bioimage_mcp.artifacts.models import ArtifactRef


class TestArtifactRefSchemaVersion:
    """Tests for ArtifactRef.schema_version field."""

    def test_artifact_ref_has_schema_version_field(self) -> None:
        """Test that ArtifactRef has schema_version field."""
        ref = ArtifactRef(
            ref_id="test-ref-1",
            type="LabelImageRef",
            uri="file:///path/to/labels.ome.tiff",
            format="OME-TIFF",
            mime_type="image/tiff",
            size_bytes=1024,
            created_at="2025-01-01T00:00:00Z",
            schema_version="1.0",
        )
        assert ref.schema_version == "1.0"

    def test_schema_version_optional(self) -> None:
        """Test that schema_version is optional."""
        ref = ArtifactRef(
            ref_id="test-ref-2",
            type="BioImageRef",
            uri="file:///path/to/image.tiff",
            format="TIFF",
            mime_type="image/tiff",
            size_bytes=2048,
            created_at="2025-01-01T00:00:00Z",
        )
        assert ref.schema_version is None

    def test_serialization_includes_schema_version(self) -> None:
        """Test that schema_version is included in model_dump."""
        ref = ArtifactRef(
            ref_id="test-ref-3",
            type="NativeOutputRef",
            uri="file:///path/to/record.json",
            format="workflow-record-json",
            mime_type="application/json",
            size_bytes=512,
            created_at="2025-01-01T00:00:00Z",
            schema_version="0.1",
        )
        data = ref.model_dump()
        assert "schema_version" in data
        assert data["schema_version"] == "0.1"
