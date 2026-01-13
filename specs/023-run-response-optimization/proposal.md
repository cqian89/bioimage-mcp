# Feature Specification: Run Response Token Optimization

**Feature Branch**: `023-run-response-optimization`  
**Created**: 2026-01-13  
**Status**: Draft  
**Input**: Reduce token bloat in `run` tool responses by ~90% through model cleanup and verbosity control, optimized for LLM consumption.

## Executive Summary

The `run` tool currently returns verbose responses (~2000+ tokens) that include redundant metadata, null fields, raw OME XML, checksums, and ancillary outputs that LLMs rarely need for decision-making. This specification introduces a two-layer optimization strategy:

1. **Model-level cleanup**: Eliminate null fields, deduplicate dimension metadata, exclude empty arrays
2. **Response-level verbosity control**: Add a `verbosity` parameter (`minimal`, `standard`, `full`) defaulting to `minimal`

Target outcome: **~90% token reduction** for typical success cases while preserving full detail when explicitly requested.

## Current State Analysis

### Token Bloat Sources

A typical `run` response for `base.io.bioimage.load` contains:

| Source | Tokens | Issue |
|--------|--------|-------|
| OME XML summary | ~200 | Truncated but still included; redundant with extracted fields |
| Duplicate dims/shape/ndim | ~80 | Present at top-level AND in metadata |
| Null fields | ~50 | `schema_version: null`, `python_class: null`, `dtype: null`, `shape: null` |
| Checksums | ~80 | SHA256 per artifact; rarely needed for LLM reasoning |
| workflow_record | ~400 | Full artifact ref for provenance; not needed for chaining |
| log_ref | ~300 | Full artifact ref for logs; only useful on error |
| Empty warnings | ~10 | `warnings: []` always serialized |
| Verbose timestamps | ~30 | Full ISO with microseconds and timezone |
| Full URIs | ~100 | File paths LLM can't access anyway |

**Total overhead: ~1250 tokens** that provide no value for LLM decision-making.

### Current ArtifactRef Structure

```python
# src/bioimage_mcp/artifacts/models.py (lines 32-61)
class ArtifactRef(BaseModel):
    ref_id: str
    type: str
    uri: str
    format: str | None = None
    storage_type: str = "file"
    mime_type: str | None = None
    size_bytes: int | None = None
    checksums: list[ArtifactChecksum] = []
    created_at: str
    metadata: dict[str, Any] = {}
    schema_version: str | None = None
    # Duplicated with metadata:
    ndim: int | None = None
    dims: list[str] | None = None
    physical_pixel_sizes: dict | None = None
    dtype: str | None = None
    shape: list[int] | None = None
    python_class: str | None = None
```

Fields `ndim`, `dims`, `shape`, `dtype`, `physical_pixel_sizes` are duplicated between top-level and `metadata` dict.

### Current Response Structure

```json
{
  "session_id": "sess_001",
  "run_id": "d134151...",
  "status": "success",
  "id": "base.io.bioimage.load",
  "outputs": {
    "image": {
      "ref_id": "3841d5cd...",
      "type": "BioImageRef",
      "uri": "file:///...",
      "format": "TIFF",
      "storage_type": "file",
      "mime_type": "image/tiff",
      "size_bytes": 29548630,
      "checksums": [{"algorithm": "sha256", "value": "d1107de8..."}],
      "created_at": "2026-01-13T14:56:53.366918+00:00",
      "metadata": {
        "axes": "ZYX",
        "ndim": 3,
        "dims": ["Z", "Y", "X"],
        "shape": [56, 512, 512],
        "dtype": "uint16",
        "axes_inferred": true,
        "file_metadata": {
          "ome_xml_summary": "<?xml version=\"1.0\"... (154313 chars)",
          "custom_attributes": {}
        },
        "file_size_bytes": 29548630,
        "physical_pixel_sizes": {"X": 1.1795, "Y": 1.1795, "Z": 0.222909},
        "channel_names": ["Channel:0:0"]
      },
      "schema_version": null,
      "ndim": 3,
      "dims": ["Z", "Y", "X"],
      "physical_pixel_sizes": {"X": 1.1795, "Y": 1.1795, "Z": 0.222909},
      "dtype": null,
      "shape": null,
      "python_class": null,
      "summary": {
        "type": "BioImageRef",
        "size_bytes": 29548630,
        "shape": [56, 512, 512],
        "dtype": "uint16"
      }
    },
    "workflow_record": { /* ~400 tokens */ }
  },
  "warnings": [],
  "log_ref": { /* ~300 tokens */ }
}
```

## Proposed Architecture

### Layer 1: Model-Level Cleanup (Always Applied)

#### 1.1 Remove Top-Level Dimension Fields from ArtifactRef

The `metadata` dict becomes the single source of truth for dimension information. Remove from `ArtifactRef`:

- `ndim` (line 56)
- `dims` (line 57)
- `physical_pixel_sizes` (line 58)
- `dtype` (line 59)
- `shape` (line 60)

These remain in `metadata` only.

#### 1.2 Exclude Null Fields from Serialization

Configure Pydantic models to exclude `None` values:

```python
class ArtifactRef(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"exclude_none": True}
    )
    
    def model_dump(self, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)
```

#### 1.3 Exclude Empty Collections

- `warnings: []` → omit field entirely
- `checksums: []` → omit field entirely
- `custom_attributes: {}` → omit field entirely

#### 1.4 Truncate/Exclude OME XML by Default

Move `file_metadata.ome_xml_summary` to `full` verbosity only. At `minimal`/`standard`, exclude entirely.

### Layer 2: Response-Level Verbosity Control

#### 2.1 Verbosity Parameter

Add optional `verbosity` parameter to `run` tool:

```python
class RunParams(BaseModel):
    fn_id: str
    inputs: dict[str, Any]
    params: dict[str, Any] | None = None
    dry_run: bool = False
    verbosity: Literal["minimal", "standard", "full"] = "minimal"
```

#### 2.2 Verbosity Levels

| Level | Artifact Output | Ancillary Outputs | Metadata |
|-------|-----------------|-------------------|----------|
| `minimal` | summary fields only (flattened) | excluded | excluded |
| `standard` | summary + core metadata | excluded | partial (no file_metadata) |
| `full` | everything | included | full (including ome_xml) |

#### 2.3 Summary Fields (Minimal Output)

The summary becomes the primary output at `minimal` verbosity, flattened directly into the output object:

```json
{
  "ref_id": "3841d5cd...",
  "type": "BioImageRef",
  "shape": [56, 512, 512],
  "dims": ["Z", "Y", "X"],
  "dtype": "uint16",
  "size_mb": 28.2,
  "physical_pixel_sizes": {"X": 1.18, "Y": 1.18, "Z": 0.22},
  "format": "TIFF",
  "channel_names": ["Channel:0:0"]
}
```

**Fields included (if not null):**
- `ref_id` - required for chaining
- `type` - artifact type for validation
- `shape` - array dimensions
- `dims` - axis semantics
- `dtype` - data type
- `size_mb` - human-readable size (converted from bytes)
- `physical_pixel_sizes` - only if available
- `format` - only if available
- `channel_names` - only if available

#### 2.4 Ancillary Output Handling

| Verbosity | status | workflow_record | log_ref | warnings |
|-----------|--------|-----------------|---------|----------|
| `minimal` | any | excluded | excluded | if non-empty |
| `standard` | any | excluded | excluded | if non-empty |
| `full` | any | included | included | always |
| any | error | excluded | **auto-included** | if non-empty |

On error, `log_ref` is automatically included regardless of verbosity level to aid debugging.

### Proposed Response Structure

#### Minimal (Default) - ~150 tokens

```json
{
  "run_id": "d134151...",
  "status": "success",
  "fn_id": "base.io.bioimage.load",
  "outputs": {
    "image": {
      "ref_id": "3841d5cd...",
      "type": "BioImageRef",
      "shape": [56, 512, 512],
      "dims": ["Z", "Y", "X"],
      "dtype": "uint16",
      "size_mb": 28.2,
      "physical_pixel_sizes": {"X": 1.18, "Y": 1.18, "Z": 0.22},
      "format": "TIFF"
    }
  }
}
```

**Changes from current:**
- Removed `session_id` (caller knows it)
- Renamed `id` → `fn_id` for clarity
- Outputs contain only summary fields (flattened)
- No `workflow_record`, `log_ref`, or `warnings`
- No null fields, checksums, URIs, or timestamps

#### Standard - ~300 tokens

```json
{
  "run_id": "d134151...",
  "status": "success",
  "fn_id": "base.io.bioimage.load",
  "outputs": {
    "image": {
      "ref_id": "3841d5cd...",
      "type": "BioImageRef",
      "uri": "file:///mnt/c/.../Embryo.tif",
      "format": "TIFF",
      "storage_type": "file",
      "size_bytes": 29548630,
      "metadata": {
        "axes": "ZYX",
        "ndim": 3,
        "dims": ["Z", "Y", "X"],
        "shape": [56, 512, 512],
        "dtype": "uint16",
        "physical_pixel_sizes": {"X": 1.18, "Y": 1.18, "Z": 0.22},
        "channel_names": ["Channel:0:0"]
      }
    }
  }
}
```

**Adds to minimal:**
- `uri` for artifact access
- `storage_type`
- `size_bytes` (raw)
- Full `metadata` block (excluding `file_metadata`)

#### Full - ~1500 tokens

```json
{
  "run_id": "d134151...",
  "status": "success",
  "fn_id": "base.io.bioimage.load",
  "outputs": {
    "image": {
      "ref_id": "3841d5cd...",
      "type": "BioImageRef",
      "uri": "file:///mnt/c/.../Embryo.tif",
      "format": "TIFF",
      "storage_type": "file",
      "mime_type": "image/tiff",
      "size_bytes": 29548630,
      "checksums": [{"algorithm": "sha256", "value": "d1107de8..."}],
      "created_at": "2026-01-13T14:56:53.366918+00:00",
      "metadata": {
        "axes": "ZYX",
        "ndim": 3,
        "dims": ["Z", "Y", "X"],
        "shape": [56, 512, 512],
        "dtype": "uint16",
        "physical_pixel_sizes": {"X": 1.18, "Y": 1.18, "Z": 0.22},
        "channel_names": ["Channel:0:0"],
        "file_metadata": {
          "ome_xml_summary": "<?xml version=\"1.0\"...",
          "custom_attributes": {}
        }
      }
    },
    "workflow_record": { /* full artifact ref */ }
  },
  "warnings": [],
  "log_ref": { /* full artifact ref */ }
}
```

#### Error Response (Any Verbosity)

```json
{
  "run_id": "d134151...",
  "status": "error",
  "fn_id": "base.io.bioimage.load",
  "error": {
    "code": "EXECUTION_FAILED",
    "message": "File not found: /path/to/image.tif",
    "details": [{"path": "/inputs/image", "hint": "Verify the file path exists"}]
  },
  "log_ref": {
    "ref_id": "1dee9f3a...",
    "type": "LogRef",
    "uri": "file:///...log"
  }
}
```

## User Scenarios & Testing

### User Story 1: LLM Chains Tool Calls Efficiently (Priority: P0)

An LLM executes a multi-step workflow (load → transform → segment) and needs minimal context to chain outputs to inputs.

**Why this priority**: This is the primary use case. Token efficiency directly impacts LLM reasoning quality and cost.

**Acceptance Scenarios**:

1. **Given** an LLM calls `run` with default verbosity, **When** the function succeeds, **Then** the response contains only `ref_id`, `type`, `shape`, `dims`, `dtype`, and optional fields if non-null.

2. **Given** an LLM receives a minimal response, **When** it needs to pass the output to the next function, **Then** it can use `ref_id` directly without parsing nested structures.

3. **Given** a 5-step workflow with default verbosity, **When** all steps succeed, **Then** total response tokens are <1000 (vs ~10000 currently).

### User Story 2: Developer Debugs Failed Run (Priority: P1)

A developer needs full details when a function fails or behaves unexpectedly.

**Acceptance Scenarios**:

1. **Given** a function fails with any verbosity level, **When** the response is returned, **Then** `log_ref` is automatically included for debugging.

2. **Given** a developer calls `run` with `verbosity: "full"`, **When** the function succeeds, **Then** the response includes checksums, timestamps, workflow_record, and full metadata.

### User Story 3: LLM Needs Physical Scale Information (Priority: P1)

An LLM performing scale-aware operations needs physical pixel sizes without requesting full metadata.

**Acceptance Scenarios**:

1. **Given** an image has physical pixel sizes, **When** `run` returns at minimal verbosity, **Then** `physical_pixel_sizes` is included in the output.

2. **Given** an image has no physical metadata, **When** `run` returns, **Then** the `physical_pixel_sizes` field is omitted (not null).

### Edge Cases

- **Missing optional fields**: Fields like `channel_names`, `physical_pixel_sizes`, `format` are omitted when null/empty, not serialized as null.
- **Error + full verbosity**: On error, `log_ref` is included but `workflow_record` follows verbosity rules.
- **Memory artifacts**: ObjectRef and in-memory artifacts still include `uri` (e.g., `obj://...`) at all verbosity levels since it's required for access.
- **Large channel lists**: If `channel_names` exceeds 10 items, truncate with `["Ch1", "Ch2", ..., "Ch48 (48 total)"]`.

## Requirements

### Constitution Constraints

#### 1. Stable MCP Surface (Anti-Context-Bloat)
**Compliance**: This feature directly addresses context bloat by reducing default response size by ~90%. The `verbosity` parameter provides explicit control.

#### 2. Artifact References Only
**Compliance**: No change to artifact reference semantics. Only the serialization verbosity changes.

#### 3. Reproducibility & Provenance
**Compliance**: Workflow records are still generated and stored; they're just excluded from `minimal`/`standard` responses. Full provenance is available via `verbosity: "full"` or `artifact_info`.

### Functional Requirements

#### Model Cleanup

- **FR-001**: System MUST exclude null fields from all `ArtifactRef` serialization by default.
- **FR-002**: System MUST remove top-level `ndim`, `dims`, `shape`, `dtype`, `physical_pixel_sizes` fields from `ArtifactRef` base class; metadata dict is the single source.
- **FR-003**: System MUST exclude empty arrays and objects (`warnings: []`, `checksums: []`, `custom_attributes: {}`) from serialization.
- **FR-004**: System MUST convert `size_bytes` to `size_mb` (rounded to 1 decimal) in minimal/standard responses.

#### Verbosity Control

- **FR-005**: System MUST add optional `verbosity` parameter to `run` tool with values `minimal`, `standard`, `full` and default `minimal`.
- **FR-006**: At `minimal` verbosity, output artifacts MUST contain only: `ref_id`, `type`, `shape`, `dims`, `dtype`, `size_mb`, plus optional `physical_pixel_sizes`, `format`, `channel_names` if non-null.
- **FR-007**: At `minimal` and `standard` verbosity, `workflow_record` and `log_ref` MUST be excluded from success responses.
- **FR-008**: At any verbosity level, when `status: "error"`, `log_ref` MUST be included automatically.
- **FR-009**: At `full` verbosity, all fields including `checksums`, `created_at`, `uri`, `workflow_record`, `log_ref`, and `metadata.file_metadata` MUST be included.
- **FR-010**: Empty `warnings` array MUST be omitted; only include when non-empty.

#### Response Structure

- **FR-011**: System MUST rename response field `id` to `fn_id` for clarity.
- **FR-012**: System MUST remove `session_id` from run responses (caller already knows it).
- **FR-013**: At minimal verbosity, summary fields MUST be flattened directly into the output object (not nested under `summary` key).

### Non-Functional Requirements

- **NFR-001**: Minimal verbosity responses for single-output functions MUST be under 200 tokens.
- **NFR-002**: Verbosity parameter MUST NOT affect function execution behavior, only response serialization.
- **NFR-003**: Backward compatibility: Clients requesting `verbosity: "full"` MUST receive responses compatible with current format (modulo FR-001..FR-003 cleanup).

## Implementation Plan

### Phase 1: Model Cleanup (Breaking Change)

1. Update `ArtifactRef` model:
   - Add `model_config` with `exclude_none=True`
   - Remove top-level dimension fields (`ndim`, `dims`, `shape`, `dtype`, `physical_pixel_sizes`)
   - Update validators to work with metadata-only dimension data

2. Update `extract_image_metadata()` to ensure all dimension data is in metadata dict

3. Update all artifact creation sites to not populate removed fields

4. Add contract tests for null exclusion and deduplication

### Phase 2: Response Serialization

1. Create `RunResponseSerializer` class with verbosity-aware serialization:
   ```python
   class RunResponseSerializer:
       def serialize(
           self,
           result: RunResult,
           verbosity: Literal["minimal", "standard", "full"] = "minimal"
       ) -> dict:
           ...
   ```

2. Implement `_serialize_minimal()`, `_serialize_standard()`, `_serialize_full()` methods

3. Add `size_mb` computation from `size_bytes`

4. Handle ancillary output inclusion rules (log_ref on error)

### Phase 3: MCP Tool Integration

1. Add `verbosity` parameter to `run` tool schema in `src/bioimage_mcp/api/tools.py`

2. Wire serializer into run tool response path

3. Update `dry_run` responses to also respect verbosity

### Phase 4: Testing & Migration

1. Update all existing tests to handle new response format

2. Add verbosity-specific contract tests

3. Update smoke tests to use minimal verbosity by default

4. Add migration notes for clients expecting old format

## File Changes

### Modified Files

```
src/bioimage_mcp/artifacts/models.py
  - Remove ndim, dims, shape, dtype, physical_pixel_sizes from ArtifactRef
  - Add model_config for exclude_none
  - Update validators

src/bioimage_mcp/artifacts/metadata.py
  - No changes (already populates metadata dict)

src/bioimage_mcp/api/tools.py
  - Add verbosity parameter to run tool
  - Wire in RunResponseSerializer

src/bioimage_mcp/api/execution.py (or equivalent)
  - Integrate RunResponseSerializer
  - Handle log_ref auto-inclusion on error

tests/unit/artifacts/test_models.py
  - Update tests for removed fields
  - Add null exclusion tests

tests/contract/test_run_response.py
  - Add verbosity-level contract tests
```

### New Files

```
src/bioimage_mcp/api/serializers.py
  - RunResponseSerializer class
  - Verbosity-aware serialization logic
  - size_mb computation

tests/contract/test_response_verbosity.py
  - Contract tests for each verbosity level
  - Token count assertions
```

## Success Criteria

- **SC-001**: Minimal verbosity responses for `base.io.bioimage.load` are under 200 tokens (currently ~2000).
- **SC-002**: No null fields appear in any verbosity level response.
- **SC-003**: Dimension metadata appears only in `metadata` dict, never at top-level.
- **SC-004**: `log_ref` is included on error regardless of verbosity setting.
- **SC-005**: `verbosity: "full"` responses are backward compatible with current format (minus null fields).
- **SC-006**: All existing smoke tests pass with minimal verbosity.
- **SC-007**: Contract tests verify token bounds for each verbosity level.

## Migration Notes

### Breaking Changes

1. **Removed fields from ArtifactRef**: `ndim`, `dims`, `shape`, `dtype`, `physical_pixel_sizes` no longer appear at top level. Access via `metadata["dims"]` etc.

2. **Response field renames**: `id` → `fn_id`, `session_id` removed.

3. **Default verbosity is minimal**: Clients expecting full responses must explicitly request `verbosity: "full"`.

4. **Null fields excluded**: Clients must handle missing fields gracefully (use `.get()` or optional types).

### Client Migration

```python
# Old
ref.dims  # Top-level field

# New  
ref.metadata.get("dims")  # or artifact_info() for full details

# Old
response["id"]

# New
response["fn_id"]

# Old (always present)
response["warnings"]

# New (omitted when empty)
response.get("warnings", [])
```

## Dependencies

- Pydantic v2 (already in use)
- No new dependencies required

## Out of Scope

1. **Artifact compression**: Binary data compression is not addressed
2. **Streaming responses**: Large responses are not streamed
3. **Per-field verbosity**: Cannot request specific fields only
4. **Client-side caching**: Response caching is client responsibility

---

This proposal addresses the immediate token efficiency problem while maintaining full capability when needed. The layered approach (model cleanup + verbosity control) provides both a cleaner baseline and explicit control for different use cases.
