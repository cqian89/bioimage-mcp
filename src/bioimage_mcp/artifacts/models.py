from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator


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
    storage_type: str = "file"
    """Storage backing: 'file', 'zarr-temp', or 'memory'"""
    mime_type: str
    size_bytes: int
    checksums: list[ArtifactChecksum] = Field(default_factory=list)
    created_at: str
    metadata: dict = Field(default_factory=dict)

    # Schema version for artifact format versioning
    # Used to track changes in artifact format over time
    schema_version: str | None = None

    @model_validator(mode="after")
    def validate_memory_artifact(self) -> ArtifactRef:
        """Ensure URI and storage_type are consistent for memory artifacts."""
        if self.uri.startswith("mem://"):
            if self.storage_type != "memory":
                raise ValueError("Artifact with mem:// URI must have storage_type='memory'")

            # Validate mem:// URI format: mem://<session_id>/<env_id>/<artifact_id>
            parts = self.uri[6:].split("/")
            if len(parts) != 3 or any(not p for p in parts):
                raise ValueError(
                    "Invalid memory URI format. Expected mem://<session_id>/<env_id>/<artifact_id>"
                )
        elif self.storage_type == "memory":
            if not self.uri.startswith("mem://"):
                raise ValueError("Artifact with storage_type='memory' must have a mem:// URI")
        return self

    def is_memory_artifact(self) -> bool:
        """Check if artifact is memory-backed."""
        return self.uri.startswith("mem://")

    @classmethod
    def now(cls) -> str:
        return datetime.now(timezone.utc).isoformat()
