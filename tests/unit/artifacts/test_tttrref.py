"""Unit tests for TTTRRef artifact model validation (Phase 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioimage_mcp.artifacts.models import ArtifactRef

# We expect TTTRRef to be implemented in src/bioimage_mcp/artifacts/models.py
# If not yet present, these imports will fail.
try:
    from bioimage_mcp.artifacts.models import TTTRMetadata, TTTRRef
except ImportError:
    # During TDD, we might need to mock or define these locally if we want to run the tests
    # before they are added to the core library, but the instruction is to write failing tests.
    TTTRRef = None
    TTTRMetadata = None


@pytest.mark.unit
class TestTTTRRefValidation:
    """Tests for TTTRRef Pydantic model validation."""

    def test_tttrref_imports(self):
        """Verify TTTRRef can be imported from models."""
        assert TTTRRef is not None, "TTTRRef must be defined in bioimage_mcp.artifacts.models"
        assert TTTRMetadata is not None, (
            "TTTRMetadata must be defined in bioimage_mcp.artifacts.models"
        )

    def test_valid_tttrref_minimal(self):
        """Test valid TTTRRef with only required fields."""
        ref = TTTRRef(ref_id="test-tttr-1", uri="file:///data/sample.ptu", format="PTU")
        assert ref.type == "TTTRRef"
        assert ref.format == "PTU"
        assert ref.uri == "file:///data/sample.ptu"

    def test_valid_tttrref_full(self):
        """Test valid TTTRRef with all fields and metadata."""
        metadata = TTTRMetadata(
            n_valid_events=1000000,
            used_routing_channels=[0, 1],
            macro_time_resolution_s=1.0e-8,
            micro_time_resolution_s=1.0e-12,
        )
        ref = TTTRRef(
            ref_id="test-tttr-2",
            uri="file:///data/sample.ht3",
            format="HT3",
            metadata=metadata,
            size_bytes=1024 * 1024,
        )
        assert ref.metadata.n_valid_events == 1000000
        assert ref.metadata.used_routing_channels == [0, 1]
        assert ref.format == "HT3"

    @pytest.mark.parametrize(
        "valid_format",
        [
            "PTU",
            "HT3",
            "SPC-130",
            "SPC-630_256",
            "SPC-630_4096",
            "PHOTON-HDF5",
            "HDF",
            "CZ-RAW",
            "SM",
        ],
    )
    def test_valid_tttr_formats(self, valid_format):
        """Test TTTRRef with each valid format."""
        ref = TTTRRef(
            ref_id=f"test-{valid_format}",
            uri=f"file:///data/sample.{valid_format.lower()}",
            format=valid_format,
        )
        if valid_format == "HDF":
            assert ref.format == "PHOTON-HDF5"
        else:
            assert ref.format == valid_format

    def test_invalid_tttr_format(self):
        """Test TTTRRef rejects invalid formats."""
        with pytest.raises(ValidationError):
            TTTRRef(ref_id="test-invalid", uri="file:///data/sample.txt", format="INVALID_FORMAT")

    def test_optional_metadata_fields(self):
        """Test that metadata fields are indeed optional."""
        # Only n_valid_events
        meta1 = TTTRMetadata(n_valid_events=100)
        assert meta1.used_routing_channels is None

        # Only channels
        meta2 = TTTRMetadata(used_routing_channels=[0])
        assert meta2.n_valid_events is None

    def test_inheritance(self):
        """Test TTTRRef inherits from ArtifactRef properly."""
        assert issubclass(TTTRRef, ArtifactRef)
        ref = TTTRRef(
            ref_id="test-inherit", uri="file:///data/sample.ptu", format="PTU", size_bytes=123
        )
        assert ref.size_bytes == 123
        assert hasattr(ref, "created_at")
