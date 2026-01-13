from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from bioimage_mcp.artifacts.models import (
    ArtifactChecksum,
    ArtifactRef,
)

AxisName = Annotated[str, Field(pattern="^[A-Z]$")]
ArtifactType = Literal[
    "BioImageRef",
    "LabelImageRef",
    "TableRef",
    "LogRef",
    "NativeOutputRef",
    "PlotRef",
    "ObjectRef",
    "GroupByRef",
    "FigureRef",
    "AxesRef",
    "AxesImageRef",
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


# --- New 8-Tool surface models (T004-T024) ---


class NodeType(str, Enum):
    ENVIRONMENT = "environment"
    PACKAGE = "package"
    MODULE = "module"
    FUNCTION = "function"


class ChildCounts(BaseModel):
    """Child count statistics for non-leaf nodes."""

    total: int
    by_type: dict[str, int]  # Use str keys for JSON compatibility


class IOPort(BaseModel):
    """Lightweight I/O port summary for function nodes."""

    name: str
    type: str  # e.g., "BioImageRef", "LabelImageRef"
    required: bool = True


class IOSummary(BaseModel):
    """Lightweight I/O summary included in list results."""

    inputs: list[IOPort]
    outputs: list[IOPort]


class CatalogNode(BaseModel):
    """Any catalog item (environment, package, module, function)."""

    id: str
    type: NodeType
    name: str
    summary: str | None = None
    children: ChildCounts | None = None
    io: IOSummary | None = None


class InputHints(BaseModel):
    """Hints for input artifact expectations."""

    expected_axes: list[str] | None = None
    min_ndim: int | None = None
    max_ndim: int | None = None
    squeeze_singleton: bool = False


class InputPort(BaseModel):
    """Full input port definition."""

    type: str
    required: bool = True
    hints: InputHints | None = None


class OutputPort(BaseModel):
    """Full output port definition."""

    type: str


class FunctionExample(BaseModel):
    """Example invocation for documentation."""

    inputs: dict[str, str]
    params: dict[str, Any]


class NextStep(BaseModel):
    """Suggested follow-up function."""

    id: str
    reason: str


class FunctionDescriptor(BaseModel):
    """Full function description for describe responses."""

    id: str
    type: Literal["function"] = "function"
    summary: str
    tags: list[str] = Field(default_factory=list)
    inputs: dict[str, InputPort]
    outputs: dict[str, OutputPort]
    params_schema: dict[str, Any]
    examples: list[FunctionExample] = Field(default_factory=list)
    next_steps: list[NextStep] = Field(default_factory=list)


class ArtifactTypeEnum(str, Enum):
    """Artifact type enumeration for the new API."""

    BIO_IMAGE = "BioImageRef"
    LABEL_IMAGE = "LabelImageRef"
    TABLE = "TableRef"
    SCALAR = "ScalarRef"
    OBJECT = "ObjectRef"
    GROUP_BY = "GroupByRef"
    MODEL = "ModelRef"
    LOG = "LogRef"
    NATIVE_OUTPUT = "NativeOutputRef"
    FIGURE = "FigureRef"
    AXES = "AxesRef"
    AXES_IMAGE = "AxesImageRef"


class ErrorDetail(BaseModel):
    """Single validation error detail."""

    path: str  # JSON Pointer
    expected: str | None = None
    actual: str | None = None
    hint: str


class StructuredError(BaseModel):
    """Standard error response shape."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


# List
class ListRequest(BaseModel):
    path: str | None = None
    cursor: str | None = None
    limit: int = 50
    types: list[NodeType] | None = None
    include_counts: bool = True


class ListResponse(BaseModel):
    items: list[CatalogNode]
    next_cursor: str | None = None
    expanded_from: str | None = None


# Describe (use Union return type in handler)
class DescribeRequest(BaseModel):
    id: str


# Search
class SearchRequest(BaseModel):
    query: str | None = None
    keywords: list[str] | None = None
    tags: list[str] | None = None
    io_in: str | None = None
    io_out: str | None = None
    limit: int = 20
    cursor: str | None = None


class SearchResult(BaseModel):
    id: str
    type: Literal["function"] = "function"
    name: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    io: IOSummary
    score: float
    match_count: int


class SearchResponse(BaseModel):
    results: list[SearchResult]
    next_cursor: str | None = None


# Run
class RunRequest(BaseModel):
    id: str
    inputs: dict[str, str]
    params: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    dry_run: bool = False


class RunResponse(BaseModel):
    session_id: str
    run_id: str
    status: Literal["success", "running", "failed", "validation_failed"]
    id: str
    outputs: dict[str, ArtifactRef] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    log_ref: ArtifactRef | None = None
    dry_run: bool | None = None
    error: StructuredError | None = None


# Status
class StatusRequest(BaseModel):
    run_id: str


class Progress(BaseModel):
    completed: int
    total: int


class StatusResponse(BaseModel):
    run_id: str
    status: Literal["running", "success", "failed"]
    progress: Progress | None = None
    outputs: dict[str, ArtifactRef] = Field(default_factory=dict)
    log_ref: ArtifactRef | None = None


# ArtifactInfo
class ArtifactInfoRequest(BaseModel):
    ref_id: str
    text_preview_bytes: int | None = None


class ArtifactInfoResponse(BaseModel):
    ref_id: str
    type: str
    uri: str
    mime_type: str | None = None
    size_bytes: int | None = None
    checksums: list[ArtifactChecksum] = Field(default_factory=list)
    text_preview: str | None = None
    dims: list[str] | None = None
    ndim: int | None = None
    dtype: str | None = None
    shape: list[int] | None = None


# Session Export
class SessionExportRequest(BaseModel):
    session_id: str
    dest_path: str | None = None


class SessionExportResponse(BaseModel):
    session_id: str
    workflow_ref: ArtifactRef


# Session Replay
class SessionReplayRequest(BaseModel):
    workflow_ref: ArtifactRef
    inputs: dict[str, str]
    params_overrides: dict[str, dict[str, Any]] | None = None
    step_overrides: dict[str, dict[str, Any]] | None = None
    mode: Literal["strict", "lenient"] = "strict"
    dry_run: bool = False


class SessionReplayResponse(BaseModel):
    run_id: str
    session_id: str
    status: Literal["running", "ready", "validation_failed"]
    workflow_ref: ArtifactRef
    log_ref: ArtifactRef | None = None
    error: StructuredError | None = None


# Workflow Models
class ExternalInput(BaseModel):
    """Caller-provided artifact reference."""

    type: str
    first_seen: dict[str, Any]


class InputSource(BaseModel):
    """Tagged reference to input origin."""

    source: Literal["external", "step"]
    key: str | None = None
    step_index: int | None = None
    port: str | None = None


class StepProvenance(BaseModel):
    """Provenance metadata for a step."""

    tool_pack_id: str
    tool_pack_version: str
    lock_hash: str | None = None


class WorkflowStep(BaseModel):
    """Single step in a workflow record."""

    index: int
    id: str
    inputs: dict[str, InputSource]
    params: dict[str, Any]
    outputs: dict[str, ArtifactRef]
    status: Literal["success", "failed", "skipped"]
    started_at: str | None = None
    ended_at: str | None = None
    provenance: StepProvenance | None = None
    log_ref: ArtifactRef | None = None


class WorkflowRecord(BaseModel):
    """Complete workflow for export/replay."""

    schema_version: str = "2026-01"
    session_id: str
    external_inputs: dict[str, ExternalInput]
    steps: list[WorkflowStep]
