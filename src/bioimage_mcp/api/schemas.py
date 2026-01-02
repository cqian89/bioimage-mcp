from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

AxisName = Annotated[str, Field(pattern="^[A-Z]$")]
ArtifactType = Literal[
    "BioImageRef",
    "LabelImageRef",
    "TableRef",
    "LogRef",
    "NativeOutputRef",
    "PlotRef",
]
StorageType = Literal["file", "zarr-temp"]


class DimensionRequirement(BaseModel):
    """Requirements for image dimensions and axes."""

    min_ndim: int | None = None
    max_ndim: int | None = None
    expected_axes: list[str] | None = None
    spatial_axes: list[str] = ["Y", "X"]
    squeeze_singleton: bool = True
    slice_strategy: str | None = None
    preprocessing_instructions: list[str] | None = None


class InputRequirement(BaseModel):
    """Schema for a single input requirement."""

    type: ArtifactType
    required: bool
    description: str
    expected_axes: list[AxisName] | None = None
    preprocessing_hint: str | None = None
    supported_storage_types: list[StorageType] | None = None
    dimension_requirements: DimensionRequirement | None = None


class OutputDescription(BaseModel):
    """Schema for a single output description."""

    type: ArtifactType
    description: str


class NextStepHint(BaseModel):
    """Suggested next step in workflow."""

    fn_id: str
    reason: str
    required_inputs: list[str] | None = None


class SuggestedFix(BaseModel):
    """Suggested fix for an error."""

    fn_id: str
    params: dict
    explanation: str


class SuccessHints(BaseModel):
    """Hints returned on successful execution."""

    next_steps: list[NextStepHint] = Field(default_factory=list)
    common_issues: list[str] = Field(default_factory=list)


class ErrorHints(BaseModel):
    """Hints returned on error."""

    diagnosis: str | None = None
    suggested_fix: SuggestedFix | None = None
    related_metadata: dict | None = None


class FunctionHints(BaseModel):
    """Hints defined per-function in manifest.yaml."""

    inputs: dict[str, InputRequirement] = Field(default_factory=dict)
    outputs: dict[str, OutputDescription] = Field(default_factory=dict)
    success_hints: SuccessHints | None = None
    error_hints: dict[str, ErrorHints] = Field(default_factory=dict)


class LLMHints(FunctionHints):
    """Structured hints for LLM workflow guidance."""


class PermissionMode(str, Enum):
    """How to interpret file access permissions."""

    EXPLICIT = "explicit"
    INHERIT = "inherit"
    HYBRID = "hybrid"


class OverwritePolicy(str, Enum):
    """How to handle overwriting existing files."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionDecision(BaseModel):
    """Recorded decision for a permission check."""

    operation: Literal["read", "write"]
    path: str
    mode: PermissionMode | None = None
    decision: Literal["ALLOWED", "DENIED", "ASK"]
    reason: str | None = None
    timestamp: datetime


class ToolHierarchyNode(BaseModel):
    """Single node in the tool hierarchy tree."""

    name: str
    full_path: str
    type: Literal["environment", "package", "module", "function"]
    has_children: bool
    fn_id: str | None = None
    summary: str | None = None


class ListToolsResponse(BaseModel):
    """Response for hierarchical tool listing."""

    tools: list[ToolHierarchyNode]
    next_cursor: str | None = None
    expanded_from: str | None = None


class ScoredFunction(BaseModel):
    """Search result entry with ranking score."""

    fn_id: str
    name: str
    description: str
    score: float
    match_count: int
    tags: list[str] = Field(default_factory=list)


class SearchFunctionsRequest(BaseModel):
    """Search request for discovery API."""

    keywords: list[str] | str
    query: str | None = None
    tags: list[str] | None = None
    limit: int = 20
    cursor: str | None = None


class SearchFunctionsResponse(BaseModel):
    """Search response with ranked functions."""

    functions: list[ScoredFunction]
    next_cursor: str | None = None
