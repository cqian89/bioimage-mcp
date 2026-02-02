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
    "PlotRef": "Visualization plots (PNG/SVG/PDF/JPG)",
    "ObjectRef": "Serialized Python object (e.g., ML model)",
    "GroupByRef": "Result of pandas groupby operation",
    "FigureRef": "Matplotlib Figure object in memory",
    "AxesRef": "Matplotlib Axes object in memory",
    "AxesImageRef": "Matplotlib AxesImage object in memory",
    "TTTRRef": "Time-Tagged Time-Resolved photon data (FLIM/FCS)",
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
    pinned: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Schema version for artifact format versioning
    # Used to track changes in artifact format over time
    schema_version: str | None = None

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

    @model_validator(mode="after")
    def validate_dimension_metadata(self) -> ArtifactRef:
        if self.type in ("BioImageRef", "LabelImageRef"):
            meta = self.metadata
            shape = meta.get("shape")
            meta_ndim = meta.get("ndim")
            meta_dims = meta.get("dims")

            if shape:
                if meta_ndim is not None and len(shape) != meta_ndim:
                    raise ValueError(f"shape length ({len(shape)}) != metadata ndim ({meta_ndim})")
                if meta_dims is not None and len(shape) != len(meta_dims):
                    raise ValueError(
                        f"shape length ({len(shape)}) != metadata dims length ({len(meta_dims)})"
                    )
        return self

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Custom serialization that excludes None values and empty collections."""
        # Force exclude_none=True
        kwargs["exclude_none"] = True
        data = super().model_dump(**kwargs)

        # Remove empty checksums
        if "checksums" in data and not data["checksums"]:
            del data["checksums"]

        # Remove empty metadata
        if "metadata" in data and not data["metadata"]:
            del data["metadata"]

        return data

    def is_memory_artifact(self) -> bool:
        """Check if artifact is memory-backed."""
        return self.uri.startswith("mem://")

    @property
    def ndim(self) -> int | None:
        """Expose ndim from metadata when present."""
        return self.metadata.get("ndim")

    @property
    def dims(self) -> list[str] | None:
        """Expose dims from metadata when present."""
        return self.metadata.get("dims")

    @property
    def shape(self) -> list[int] | None:
        """Expose shape from metadata when present."""
        return self.metadata.get("shape")

    @property
    def dtype(self) -> str | None:
        """Expose dtype from metadata when present."""
        return self.metadata.get("dtype")

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
    format: Literal["PNG", "SVG", "PDF", "JPG"] = "PNG"
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


class FigureMetadata(BaseModel):
    figsize: tuple[float, float]
    dpi: int = 100
    facecolor: str | None = None
    edgecolor: str | None = None
    layout: str | None = None
    axes_count: int = 0


class FigureRef(ObjectRef):
    """Reference to a matplotlib.figure.Figure object."""

    type: Literal["FigureRef"] = "FigureRef"
    python_class: str = "matplotlib.figure.Figure"
    metadata: FigureMetadata


class AxesMetadata(BaseModel):
    title: str | None = None
    xlabel: str | None = None
    ylabel: str | None = None
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
    xscale: str = "linear"
    yscale: str = "linear"
    aspect: str | float = "auto"
    is_axis_off: bool = False
    parent_figure_ref_id: str


class AxesRef(ObjectRef):
    """Reference to a matplotlib.axes.Axes object."""

    type: Literal["AxesRef"] = "AxesRef"
    python_class: str = "matplotlib.axes._axes.Axes"
    metadata: AxesMetadata


class AxesImageMetadata(BaseModel):
    cmap: str = "viridis"
    vmin: float | None = None
    vmax: float | None = None
    origin: Literal["upper", "lower"] = "upper"
    interpolation: str = "antialiased"
    parent_axes_ref_id: str


class AxesImageRef(ObjectRef):
    """Reference to a matplotlib.image.AxesImage object."""

    type: Literal["AxesImageRef"] = "AxesImageRef"
    python_class: str = "matplotlib.image.AxesImage"
    metadata: AxesImageMetadata


class TTTRMetadata(BaseModel):
    """Metadata for TTTR photon-stream artifacts."""

    n_valid_events: int | None = None
    used_routing_channels: list[int] | None = None
    macro_time_resolution_s: float | None = None
    micro_time_resolution_s: float | None = None


class TTTRRef(ArtifactRef):
    """Reference to Time-Tagged Time-Resolved photon data."""

    type: Literal["TTTRRef"] = "TTTRRef"
    format: (
        Literal[
            "PTU",
            "HT3",
            "SPC-130",
            "SPC-630_256",
            "SPC-630_4096",
            "PHOTON-HDF5",
            "HDF",
            "CZ-RAW",
            "SM",
        ]
        | None
    ) = None
    metadata: TTTRMetadata = Field(default_factory=TTTRMetadata)

    @model_validator(mode="after")
    def normalize_format_aliases(self) -> TTTRRef:
        if self.format == "HDF":
            self.format = "PHOTON-HDF5"
        return self
