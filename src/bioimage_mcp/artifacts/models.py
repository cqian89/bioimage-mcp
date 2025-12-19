from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ArtifactChecksum(BaseModel):
    algorithm: str
    value: str


# Canonical artifact types
# Note: These are semantic role identifiers, not format specifications
ARTIFACT_TYPES = {
    "BioImageRef": "Multi-dimensional bioimaging data (input/intermediate)",
    "LabelImageRef": "Instance segmentation labels (integer-valued image)",
    "LogRef": "Execution log output",
    "NativeOutputRef": "Tool-native output bundle (format is tool-dependent)",
}


class ArtifactRef(BaseModel):
    """Typed, file-backed pointer for all inter-tool I/O.

    The `format` field is open and extensible - values are tool-dependent.
    Examples: OME-TIFF, OME-Zarr, workflow-record-json, cellpose-seg-npy.
    """

    ref_id: str
    type: str
    uri: str
    format: str
    mime_type: str
    size_bytes: int
    checksums: list[ArtifactChecksum] = Field(default_factory=list)
    created_at: str
    metadata: dict = Field(default_factory=dict)

    # Schema version for artifact format versioning
    # Used to track changes in artifact format over time
    schema_version: str | None = None

    @classmethod
    def now(cls) -> str:
        return datetime.now(UTC).isoformat()
