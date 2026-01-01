import pytest
from pydantic import ValidationError
from bioimage_mcp.artifacts.models import ArtifactRef


class TestMemoryArtifactSchema:
    def test_valid_memory_artifact_creation(self):
        """Test creating a valid memory artifact reference."""
        ref = ArtifactRef(
            ref_id="mem-123",
            type="BioImageRef",
            uri="mem://session-1/env-base/artifact-456",
            format="memory",
            storage_type="memory",
            mime_type="application/x-numpy",
            size_bytes=0,
            created_at=ArtifactRef.now(),
        )
        assert ref.storage_type == "memory"
        assert ref.is_memory_artifact() is True
        assert ref.uri == "mem://session-1/env-base/artifact-456"

    def test_mem_uri_requires_memory_storage_type(self):
        """Test that mem:// URI requires storage_type='memory'."""
        with pytest.raises(
            ValidationError, match="Artifact with mem:// URI must have storage_type='memory'"
        ):
            ArtifactRef(
                ref_id="mem-123",
                type="BioImageRef",
                uri="mem://session-1/env-base/artifact-456",
                format="memory",
                storage_type="file",  # Invalid for mem://
                mime_type="application/x-numpy",
                size_bytes=0,
                created_at=ArtifactRef.now(),
            )

    def test_memory_storage_type_requires_mem_uri(self):
        """Test that storage_type='memory' requires mem:// URI."""
        with pytest.raises(
            ValidationError, match="Artifact with storage_type='memory' must have a mem:// URI"
        ):
            ArtifactRef(
                ref_id="mem-123",
                type="BioImageRef",
                uri="file:///tmp/image.tif",  # Invalid for storage_type='memory'
                format="memory",
                storage_type="memory",
                mime_type="application/x-numpy",
                size_bytes=0,
                created_at=ArtifactRef.now(),
            )

    def test_is_memory_artifact_true_for_mem_uri(self):
        """Test is_memory_artifact() helper for mem:// URIs."""
        ref = ArtifactRef(
            ref_id="mem-123",
            type="BioImageRef",
            uri="mem://s/e/a",
            format="memory",
            storage_type="memory",
            mime_type="application/x-numpy",
            size_bytes=0,
            created_at=ArtifactRef.now(),
        )
        assert ref.is_memory_artifact() is True

    def test_is_memory_artifact_false_for_file_uri(self):
        """Test is_memory_artifact() helper for file:// URIs."""
        ref = ArtifactRef(
            ref_id="file-123",
            type="BioImageRef",
            uri="file:///tmp/test.tif",
            format="OME-TIFF",
            storage_type="file",
            mime_type="image/tiff",
            size_bytes=1024,
            created_at=ArtifactRef.now(),
        )
        assert ref.is_memory_artifact() is False

    def test_memory_artifact_allows_zero_size_bytes(self):
        """Test that memory artifacts can have 0 size_bytes."""
        ref = ArtifactRef(
            ref_id="mem-123",
            type="BioImageRef",
            uri="mem://s/e/a",
            format="memory",
            storage_type="memory",
            mime_type="application/x-numpy",
            size_bytes=0,
            created_at=ArtifactRef.now(),
        )
        assert ref.size_bytes == 0

    def test_memory_artifact_allows_empty_checksums(self):
        """Test that memory artifacts can have empty checksums."""
        ref = ArtifactRef(
            ref_id="mem-123",
            type="BioImageRef",
            uri="mem://s/e/a",
            format="memory",
            storage_type="memory",
            mime_type="application/x-numpy",
            size_bytes=0,
            checksums=[],
            created_at=ArtifactRef.now(),
        )
        assert len(ref.checksums) == 0

    def test_invalid_mem_uri_format_rejected(self):
        """Test that invalid mem:// URI formats are rejected."""
        invalid_uris = [
            "mem://",  # No segments
            "mem://session",  # Only 1 segment
            "mem://session/env",  # Only 2 segments
            "mem:////artifact",  # Empty segments
            "mem://s/e/",  # Empty last segment
            "mem:///e/a",  # Empty first segment
        ]

        for uri in invalid_uris:
            with pytest.raises(ValidationError):
                ArtifactRef(
                    ref_id="mem-123",
                    type="BioImageRef",
                    uri=uri,
                    format="memory",
                    storage_type="memory",
                    mime_type="application/x-numpy",
                    size_bytes=0,
                    created_at=ArtifactRef.now(),
                )
