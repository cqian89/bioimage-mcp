from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from bioimage_mcp.api.schemas import FunctionHints


class IOPattern(str, Enum):
    """Categorization of function I/O behavior."""

    IMAGE_TO_IMAGE = "image_to_image"
    IMAGE_TO_LABELS = "image_to_labels"
    LABELS_TO_LABELS = "labels_to_labels"
    LABELS_TO_TABLE = "labels_to_table"
    SIGNAL_TO_PHASOR = "signal_to_phasor"
    PHASOR_TRANSFORM = "phasor_transform"
    PHASOR_CALIBRATE = "phasor_calibrate"
    PHASOR_TO_OTHER = "phasor_to_other"
    PHASOR_TO_SCALAR = "phasor_to_scalar"
    SCALAR_TO_PHASOR = "scalar_to_phasor"
    PLOT = "plot"
    PHASOR_PLOT = "phasor_plot"  # (real, imag) -> PlotRef
    ARRAY_TO_ARRAY = "array_to_array"
    ARRAY_TO_SCALAR = "array_to_scalar"
    FILE_TO_SIGNAL = "file_to_signal"
    TRAINING = "training"
    OBJECTREF_CHAIN = "objectref_chain"  # ObjectRef/BioImageRef in, ObjectRef out
    CONSTRUCTOR = "constructor"  # BioImageRef in, ObjectRef (da) out
    MULTI_INPUT = "multi_input"  # Multiple BioImageRef in, BioImageRef out
    MULTI_TABLE_INPUT = "multi_table_input"  # Multiple TableRef/ObjectRef in, ObjectRef out
    BINARY = "binary"  # Two BioImageRef in, BioImageRef out
    OBJECT_TO_IMAGE = "object_to_image"  # ObjectRef/BioImageRef in, BioImageRef out
    IMAGE_TO_TABLE = "image_to_table"
    TABLE_TO_TABLE = "table_to_table"
    PURE_CONSTRUCTOR = "pure_constructor"  # No artifact inputs, ObjectRef out
    MATPLOTLIB_SUBPLOTS = "matplotlib_subplots"  # No inputs, FigureRef + AxesRef out
    MATPLOTLIB_AXES_OP = "matplotlib_axes_op"  # AxesRef (+ optional data) in, AxesRef out
    MATPLOTLIB_FIGURE_OP = "matplotlib_figure_op"  # FigureRef in, FigureRef out
    FILE_TO_REF = "file_to_ref"
    REF_TO_JSON = "ref_to_json"
    REF_TO_TABLE = "ref_to_table"
    REF_TO_OBJECT = "ref_to_object"
    REF_TO_FILE = "ref_to_file"
    IMAGE_TO_JSON = "image_to_json"
    IMAGE_AND_LABELS_TO_JSON = "image_and_labels_to_json"
    IMAGE_TO_LABELS_AND_JSON = "image_to_labels_and_json"
    TABLE_TO_JSON = "table_to_json"
    MULTI_TABLE_TO_JSON = "multi_table_to_json"
    PARAMS_TO_JSON = "params_to_json"
    GENERIC = "generic"


class ParameterSchema(BaseModel):
    """JSON Schema definition for a function parameter."""

    name: str
    type: str
    description: str = ""
    default: Any | None = None
    required: bool = True
    enum: list[Any] | None = None
    additionalProperties: Any | None = None
    examples: list[Any] | None = None
    items: dict[str, Any] | None = None


class FunctionMetadata(BaseModel):
    """Result of introspecting a single function."""

    name: str
    module: str
    qualified_name: str
    fn_id: str
    source_adapter: str
    description: str = ""
    parameters: dict[str, ParameterSchema] = Field(default_factory=dict)
    returns: str | None = Field(default=None, description="Return type annotation")
    io_pattern: IOPattern = IOPattern.GENERIC
    tags: list[str] = Field(default_factory=list)
    hints: FunctionHints | None = None


class ApplyUfuncConfig(BaseModel):
    """Configuration for xarray.apply_ufunc execution."""

    input_core_dims: list[list[str]] = Field(
        description="Core dimensions for each input (e.g., [['Y', 'X']] for spatial filters)"
    )
    output_core_dims: list[list[str]] = Field(description="Core dimensions for each output")
    vectorize: bool = Field(default=True, description="Loop over non-core dimensions")
    dask: Literal["forbidden", "allowed", "parallelized"] = Field(
        default="parallelized", description="Dask handling"
    )
    output_dtypes: list[str] | None = Field(default=None, description="Optional output dtype hints")
