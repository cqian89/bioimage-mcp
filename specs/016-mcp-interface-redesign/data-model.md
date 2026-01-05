# Data Model: MCP Interface Redesign

**Feature**: 016-mcp-interface-redesign  
**Date**: 2026-01-05  
**Status**: Draft

## Overview

This document defines the Pydantic models for the 8 MCP tools. All models use Pydantic v2 and generate valid JSON Schema.

---

## Core Entities

### 1. CatalogNode

Represents any item in the catalog hierarchy.

```python
class NodeType(str, Enum):
    ENVIRONMENT = "environment"
    PACKAGE = "package"
    MODULE = "module"
    FUNCTION = "function"

class ChildCounts(BaseModel):
    """Child count statistics for non-leaf nodes."""
    total: int
    by_type: dict[NodeType, int]

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
    id: str  # Unique stable identifier (e.g., "base.skimage.filters.gaussian")
    type: NodeType
    name: str  # Display name
    summary: str | None = None
    
    # Non-leaf nodes include children info
    children: ChildCounts | None = None
    
    # Function nodes include I/O summary
    io: IOSummary | None = None
```

**Validation Rules**:
- `id` is globally unique and stable
- `children` is present only for non-leaf nodes
- `io` is present only for function nodes

**State Transitions**: None (immutable catalog data)

---

### 2. FunctionDescriptor

Full description of a callable function. Returned by `describe` for function nodes.

```python
class InputHints(BaseModel):
    """Hints for input artifact expectations."""
    expected_axes: list[str] | None = None  # e.g., ["Y", "X"]
    min_ndim: int | None = None
    max_ndim: int | None = None
    squeeze_singleton: bool = False

class InputPort(BaseModel):
    """Full input port definition."""
    type: str  # "BioImageRef", "LabelImageRef", "TableRef"
    required: bool = True
    hints: InputHints | None = None

class OutputPort(BaseModel):
    """Full output port definition."""
    type: str  # "BioImageRef", "LabelImageRef", "TableRef"

class FunctionExample(BaseModel):
    """Example invocation for documentation."""
    inputs: dict[str, str]  # Port name -> artifact description
    params: dict[str, Any]

class NextStep(BaseModel):
    """Suggested follow-up function."""
    id: str
    reason: str

class FunctionDescriptor(BaseModel):
    """Full function description for describe responses."""
    id: str
    type: Literal[NodeType.FUNCTION] = NodeType.FUNCTION
    summary: str
    tags: list[str] = []
    
    # Separated artifact ports and params
    inputs: dict[str, InputPort]
    outputs: dict[str, OutputPort]
    params_schema: dict[str, Any]  # JSON Schema for params
    
    # Documentation aids
    examples: list[FunctionExample] = []
    next_steps: list[NextStep] = []
```

**Validation Rules**:
- `inputs` and `outputs` MUST NOT duplicate keys from `params_schema.properties`
- `params_schema` MUST be valid JSON Schema with correct types
- All `id` references in `next_steps` MUST be valid function IDs

---

### 3. ArtifactRef

Typed reference to a file-backed artifact. Used in `run` responses.

```python
class ArtifactType(str, Enum):
    BIO_IMAGE = "BioImageRef"
    LABEL_IMAGE = "LabelImageRef"
    TABLE = "TableRef"
    SCALAR = "ScalarRef"
    MODEL = "ModelRef"
    LOG = "LogRef"

class ArtifactChecksum(BaseModel):
    """Integrity verification."""
    algorithm: str  # "sha256"
    value: str

class ArtifactRef(BaseModel):
    """Reference to a stored artifact with bounded metadata."""
    ref_id: str
    type: ArtifactType
    uri: str  # file:///... or mem://...
    
    # Bounded metadata (never large payloads)
    mime_type: str | None = None
    format: str | None = None  # "OME-TIFF", "OME-Zarr"
    size_bytes: int | None = None
    
    # Image-specific metadata
    dims: list[str] | None = None  # e.g., ["Y", "X"]
    ndim: int | None = None
    dtype: str | None = None  # "uint16", "float32"
    shape: list[int] | None = None
    
    # Integrity
    checksums: list[ArtifactChecksum] = []
```

**Validation Rules**:
- `uri` must match `storage_type` (file:// vs mem://)
- `dims`, `ndim`, `dtype`, `shape` present for image types

---

### 4. WorkflowRecord

Exportable session record for replay.

```python
class ExternalInput(BaseModel):
    """Caller-provided artifact reference."""
    type: ArtifactType
    first_seen: dict[str, Any]  # {"step_index": 0, "port": "image"}

class InputSource(BaseModel):
    """Tagged reference to input origin."""
    source: Literal["external", "step"]
    key: str | None = None  # For external: key in external_inputs
    step_index: int | None = None  # For step: source step
    port: str | None = None  # For step: output port name

class StepProvenance(BaseModel):
    """Provenance metadata for a step."""
    tool_pack_id: str
    tool_pack_version: str
    lock_hash: str | None = None

class WorkflowStep(BaseModel):
    """Single step in a workflow record."""
    index: int
    id: str  # Function ID
    inputs: dict[str, InputSource]  # Port name -> source
    params: dict[str, Any]
    outputs: dict[str, ArtifactRef]
    status: Literal["success", "failed", "skipped"]
    started_at: str | None = None  # ISO timestamp
    ended_at: str | None = None
    provenance: StepProvenance | None = None
    log_ref: ArtifactRef | None = None

class WorkflowRecord(BaseModel):
    """Complete workflow for export/replay."""
    schema_version: str = "2026-01"
    session_id: str
    external_inputs: dict[str, ExternalInput]
    steps: list[WorkflowStep]
```

**Validation Rules**:
- Each `inputs[port].key` for `source="external"` MUST exist in `external_inputs`
- Each `inputs[port].step_index` for `source="step"` MUST reference a prior step

---

### 5. StructuredError

Unified error model for all tools.

```python
class ErrorDetail(BaseModel):
    """Single validation error detail."""
    path: str  # JSON Pointer (e.g., "/inputs/image")
    expected: str | None = None
    actual: str | None = None
    hint: str  # Actionable guidance

class StructuredError(BaseModel):
    """Standard error response shape."""
    code: str  # Stable, enumerable (e.g., "VALIDATION_FAILED", "NOT_FOUND")
    message: str  # Human-readable summary
    details: list[ErrorDetail] = []
```

**Error Codes** (enumerable):
- `VALIDATION_FAILED`: Request validation error
- `NOT_FOUND`: Catalog node or artifact not found
- `EXECUTION_FAILED`: Tool execution error
- `PERMISSION_DENIED`: Filesystem access denied
- `SCHEMA_MISMATCH`: Workflow record schema incompatibility

---

## Request/Response Models

### list

```python
class ListRequest(BaseModel):
    path: str | None = None  # Root if None
    cursor: str | None = None
    limit: int = 50
    types: list[NodeType] | None = None
    include_counts: bool = True

class ListResponse(BaseModel):
    items: list[CatalogNode]
    next_cursor: str | None = None
    expanded_from: str | None = None
```

### describe

```python
class DescribeRequest(BaseModel):
    id: str

class DescribeResponse(BaseModel):
    """Union type: FunctionDescriptor | CatalogNode with details."""
    # For functions: full FunctionDescriptor
    # For non-functions: CatalogNode with child preview
    pass  # Implemented as Union[FunctionDescriptor, CatalogNodeDetail]
```

### search

```python
class SearchRequest(BaseModel):
    query: str | None = None
    keywords: list[str] | None = None  # Exactly one of query/keywords required
    tags: list[str] | None = None
    io_in: str | None = None  # Input type filter
    io_out: str | None = None  # Output type filter
    limit: int = 20
    cursor: str | None = None

class SearchResult(BaseModel):
    id: str
    type: Literal[NodeType.FUNCTION]
    name: str
    summary: str
    tags: list[str]
    io: IOSummary
    score: float
    match_count: int

class SearchResponse(BaseModel):
    results: list[SearchResult]
    next_cursor: str | None = None
```

### run

```python
class RunRequest(BaseModel):
    id: str  # Function ID
    inputs: dict[str, str]  # Port name -> artifact ref_id
    params: dict[str, Any] = {}
    session_id: str | None = None
    dry_run: bool = False

class RunResponse(BaseModel):
    session_id: str
    run_id: str
    status: Literal["success", "running", "failed", "validation_failed"]
    id: str  # Function ID
    outputs: dict[str, ArtifactRef]
    warnings: list[str] = []
    log_ref: ArtifactRef | None = None
    error: StructuredError | None = None  # Present if validation_failed
```

### status

```python
class StatusRequest(BaseModel):
    run_id: str

class Progress(BaseModel):
    completed: int
    total: int

class StatusResponse(BaseModel):
    run_id: str
    status: Literal["running", "success", "failed"]
    progress: Progress | None = None
    outputs: dict[str, ArtifactRef]
    log_ref: ArtifactRef | None = None
```

### artifact_info

```python
class ArtifactInfoRequest(BaseModel):
    ref_id: str
    text_preview_bytes: int | None = None  # Max bytes for text preview

class ArtifactInfoResponse(BaseModel):
    ref_id: str
    type: ArtifactType
    uri: str
    mime_type: str | None = None
    size_bytes: int | None = None
    checksums: list[ArtifactChecksum] = []
    
    # Optional text preview (safe types only)
    text_preview: str | None = None
    
    # Image metadata
    dims: list[str] | None = None
    ndim: int | None = None
    dtype: str | None = None
    shape: list[int] | None = None
```

### session_export

```python
class SessionExportRequest(BaseModel):
    session_id: str
    dest_path: str | None = None  # Optional file output path (allowed roots enforced)

class SessionExportResponse(BaseModel):
    session_id: str
    workflow_ref: ArtifactRef  # type=TableRef, format=workflow-record-json
```

### session_replay

```python
class SessionReplayRequest(BaseModel):
    workflow_ref: ArtifactRef  # Reference to exported workflow
    inputs: dict[str, str]  # External input key -> new artifact ref_id
    params_overrides: dict[str, dict[str, Any]] | None = None  # fn_id -> params
    step_overrides: dict[str, dict[str, Any]] | None = None  # "step:N" -> {params: ...}
    mode: Literal["strict", "lenient"] = "strict"
    dry_run: bool = False

class SessionReplayResponse(BaseModel):
    run_id: str
    session_id: str
    status: Literal["running", "ready", "validation_failed"]
    workflow_ref: ArtifactRef
    log_ref: ArtifactRef | None = None
    error: StructuredError | None = None  # Present if validation_failed
```

---

## Relationships

```
CatalogNode (hierarchy)
    ├── environment
    │     └── package
    │           └── module
    │                 └── function → FunctionDescriptor (via describe)
    │
    └── children: ChildCounts (non-leaf nodes only)

FunctionDescriptor
    ├── inputs: dict[str, InputPort] → ArtifactRef (execution)
    ├── outputs: dict[str, OutputPort] → ArtifactRef (execution)
    └── params_schema: JSON Schema (no artifact ports)

WorkflowRecord
    ├── external_inputs: dict[str, ExternalInput] → ArtifactRef (provided by caller)
    └── steps: list[WorkflowStep]
          ├── inputs: dict[str, InputSource] → references external_inputs OR prior steps
          └── outputs: dict[str, ArtifactRef] → produced artifacts

StructuredError (all tools on failure)
    └── details: list[ErrorDetail] → JSON Pointer paths
```