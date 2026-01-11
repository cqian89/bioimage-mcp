from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ArtifactChecksum(BaseModel):
    algorithm: str
    value: str


# Canonical artifact types
# Note: These are semantic role identifiers, not format specifications
ARTIFACT_TYPES = {
    "BioImageRef": "Multi-dimensional bioimaging data (input/intermediate)",
    "LabelImageRef": "Instance segmentation labels (integer-valued image)",
    "TableRef": "Measurement/feature tables (CSV format)",
    "ScalarRef": "Single numeric values (thresholds, statistics)",
    "LogRef": "Execution log output",
    "NativeOutputRef": "Tool-native output bundle (format is tool-dependent)",
    "PlotRef": "Visualization plots (PNG/SVG)",
    "ObjectRef": "Serialized Python object (e.g., ML model)",
    "GroupByRef": "Result of pandas groupby operation",
}


class ArtifactRef(BaseModel):
    """Typed, file-backed pointer for all inter-tool I/O.

    The `format` field is open and extensible - values are tool-dependent.
    Examples: OME-TIFF, OME-Zarr, workflow-record-json, cellpose-seg-npy.
    """

    ref_id: str
    type: str
    uri: str
    format: str | None = None
    storage_type: str = "file"
    """Storage backing: 'file', 'zarr-temp', or 'memory'"""
    mime_type: str | None = None
    size_bytes: int | None = None
    checksums: list[ArtifactChecksum] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Schema version for artifact format versioning
    # Used to track changes in artifact format over time
    schema_version: str | None = None

    # T008: Add ndim, dims, physical_pixel_sizes fields
    ndim: int | None = None
    dims: list[str] | None = None
    physical_pixel_sizes: dict | None = None
    dtype: str | None = None
    shape: list[int] | None = None
    python_class: str | None = None

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
            if not (self.uri.startswith("mem://") or self.uri.startswith("obj://")):
                raise ValueError(
                    "Artifact with storage_type='memory' must have a mem:// or obj:// URI"
                )
        return self

    # T011: Add model_validator for dimension metadata consistency
    @model_validator(mode="after")
    def validate_dimension_metadata(self) -> ArtifactRef:
        if self.type in ("BioImageRef", "LabelImageRef"):
            meta = self.metadata
            shape = meta.get("shape")
            meta_ndim = meta.get("ndim")
            meta_dims = meta.get("dims")

            # 1. Validate metadata['shape'] vs internal metadata ndim/dims
            if shape:
                if meta_ndim is not None and len(shape) != meta_ndim:
                    raise ValueError(f"shape length ({len(shape)}) != metadata ndim ({meta_ndim})")
                if meta_dims is not None and len(shape) != len(meta_dims):
                    raise ValueError(
                        f"shape length ({len(shape)}) != metadata dims length ({len(meta_dims)})"
                    )

            # 2. Validate top-level fields vs metadata['shape']
            if shape:
                if self.ndim is not None and len(shape) != self.ndim:
                    raise ValueError(f"shape length ({len(shape)}) != top-level ndim ({self.ndim})")
                if self.dims is not None and len(shape) != len(self.dims):
                    raise ValueError(
                        f"shape length ({len(shape)}) != top-level dims length ({len(self.dims)})"
                    )

            # 3. Cross-check between top-level ndim and metadata["ndim"]
            if self.ndim is not None and meta_ndim is not None and self.ndim != meta_ndim:
                raise ValueError(f"top-level ndim ({self.ndim}) != metadata ndim ({meta_ndim})")

            # 4. Cross-check top-level ndim vs top-level dims
            if self.ndim is not None and self.dims is not None and self.ndim != len(self.dims):
                raise ValueError(
                    f"top-level ndim ({self.ndim}) != top-level dims length ({len(self.dims)})"
                )
        return self

    def is_memory_artifact(self) -> bool:
        """Check if artifact is memory-backed."""
        return self.uri.startswith("mem://")

    @classmethod
    def now(cls) -> str:
        return datetime.now(UTC).isoformat()


# T010: Add ColumnMetadata and TableMetadata classes
class ColumnMetadata(BaseModel):
    name: str
    dtype: str  # "int64", "float64", "string", "bool"


class TableMetadata(BaseModel):
    columns: list[ColumnMetadata]
    row_count: int
    delimiter: str | None = None
    schema_id: str | None = None
    source_fn_id: str | None = None


class PlotMetadata(BaseModel):
    """Metadata for plot artifacts."""

    width_px: int
    height_px: int
    dpi: int = 100
    plot_type: str | None = None
    title: str | None = None


class PlotRef(ArtifactRef):
    """Reference to a matplotlib plot artifact."""

    type: Literal["PlotRef"] = "PlotRef"
    format: Literal["PNG", "SVG"] = "PNG"
    metadata: PlotMetadata


class TableRef(ArtifactRef):
    """Reference to a tabular data artifact."""

    type: Literal["TableRef"] = "TableRef"
    columns: list[str]
    row_count: int
    delimiter: str = ","
    schema_id: str | None = None
    metadata: TableMetadata


# T009: Add ScalarRef class with JSON format and ScalarMetadata
class ScalarMetadata(BaseModel):
    value: float | int | bool
    dtype: str  # "float64", "int64", "bool"
    unit: str | None = None
    computed_from: str | None = None  # fn_id that produced this value
    source_ref_id: str | None = None  # Input artifact ref_id


class ScalarRef(ArtifactRef):
    type: Literal["ScalarRef"] = "ScalarRef"
    format: Literal["json"] = "json"
    mime_type: Literal["application/json"] = "application/json"
    metadata: ScalarMetadata


class PhasorMetadata(BaseModel):
    """Extended metadata for phasor artifacts."""

    component: Literal["mean", "real", "imag"]
    harmonic: int = 1
    frequency_hz: float | None = None
    is_calibrated: bool = False
    reference_lifetime_ns: float | None = None


class ObjectRef(ArtifactRef):
    """Reference to a serialized Python object (e.g., ML model)."""

    type: Literal["ObjectRef"] = "ObjectRef"
    python_class: str  # e.g., "cellpose.models.CellposeModel"
    mime_type: str = "application/x-python-pickle"
    size_bytes: int = 0

    @model_validator(mode="after")
    def validate_object_ref(self) -> ObjectRef:
        # Validate obj:// URI format
        if self.uri.startswith("obj://"):
            if self.storage_type != "memory":
                raise ValueError("ObjectRef with obj:// URI must have storage_type='memory'")
            parts = self.uri[6:].split("/")
            if not (2 <= len(parts) <= 3) or any(not p for p in parts):
                raise ValueError("Invalid object URI format")
        elif self.storage_type == "memory":
            if not self.uri.startswith("obj://"):
                raise ValueError("ObjectRef with storage_type='memory' must have an obj:// URI")
        return self


class GroupByMetadata(BaseModel):
    grouped_by: list[str]
    groups_count: int
    source_ref_id: str | None = None


class GroupByRef(ObjectRef):
    """Reference to a result of groupby operation (pandas GroupBy)."""

    type: Literal["GroupByRef"] = "GroupByRef"
    metadata: GroupByMetadata
