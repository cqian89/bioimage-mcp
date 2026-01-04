# Implementation Plan: Native Artifact Types and Dimension Preservation

**Branch**: `014-native-artifact-types` | **Date**: 2026-01-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-native-artifact-types/spec.md`

## Summary

Shift from forced 5D (TCZYX) output normalization to a native artifact model where artifacts preserve their actual dimensionality, data types, and rich metadata. The core change uses `img.reader.data` instead of `img.data` to preserve native dimensions (avoiding bioio's default 5D normalization behavior), extends `ArtifactRef` with first-class dimension fields (`ndim`, `dims`, `shape`), switches internal interchange to OME-Zarr for flexible N-D support, and adds multi-format export capabilities.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic>=2.0`, `bioio`, `zarr`, `bioio-ome-zarr`, `bioio-ome-tiff`  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Testing**: `pytest` + `pytest-asyncio` (contract, unit, integration tests)  
**Target Platform**: Local/on-prem; Linux-first (macOS/Windows best-effort)  
**Project Type**: Python service + CLI  
**Performance Goals**: Bounded MCP payload sizes; metadata inspection without data loading  
**Constraints**: No large binary payloads in MCP; artifact references only  
**Scale/Scope**: Tool catalog can grow; discovery must remain paginated

### Current State Analysis

| Component | File | Current Behavior |
|-----------|------|------------------|
| ArtifactRef model | `src/bioimage_mcp/artifacts/models.py` | `metadata` dict contains `axes`, `shape`, `dtype` but lacks first-class `ndim`, `dims` fields |
| XarrayAdapter | `src/bioimage_mcp/registry/dynamic/adapters/xarray.py` | Lines 121-127 force ALL outputs to 5D TCZYX before saving |
| SkimageAdapter | `src/bioimage_mcp/registry/dynamic/adapters/skimage.py` | Uses bioio (5D on read), infers axes from ndim on save |
| Metadata extraction | `src/bioimage_mcp/artifacts/metadata.py` | Extracts axes, shape, dtype via BioImage; missing ndim, dims list |
| DimensionRequirement | `src/bioimage_mcp/api/schemas.py` | Already exists for tool hints (min_ndim, max_ndim, expected_axes) |
| Artifact store | `src/bioimage_mcp/artifacts/store.py` | Supports file/directory import, memory artifacts, metadata extraction |

### Key Technical Decisions (from research)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Image loading pattern | `img.reader.data` (native) | `BioImage.data` forces 5D; reader preserves native dims |
| OME-Zarr writer | `bioio_ome_zarr.writers.OMEZarrWriter` with `axes_names`/`axes_types` | Constitution-compliant; supports N-D natively |
| Metadata access | `BioImage` wrapper for physical_pixel_sizes, channel_names | Wrapper provides safe defaults; reader may return None |
| ScalarRef implementation | New artifact type with JSON storage | Consistent with artifact-only I/O model |
| TableRef column metadata | `columns` field in metadata dict | List of {name, dtype} objects |

### NEEDS CLARIFICATION (resolved in research.md)

1. **OME-Zarr writer compatibility**: Resolved: Use bioio-ome-zarr (not ome-zarr-py) per Constitution III amendment.
2. **Backward compatibility for 5D tools**: How should tools that genuinely need 5D declare this?
3. **Default export format inference**: What heuristics determine PNG vs OME-TIFF vs OME-Zarr?
4. **Memory artifact dimension preservation**: How do mem:// artifacts carry dimension metadata?

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Stable MCP surface**: Additive changes only (new metadata fields in `describe_function` and `get_artifact` responses). No new endpoints required. Backward-compatible—existing clients can ignore new fields.
- [x] **Summary-first responses**: Full dimension metadata fetched via existing `describe_function(fn_id)` and `get_artifact(ref_id)` endpoints—no changes to pagination model.
- [x] **Tool execution isolated**: Changes affect adapters in base/cellpose environments only. No new dependencies in core server. Heavy OME-Zarr I/O stays in tool envs.
- [x] **Artifact references only**: All dimension/shape metadata in artifact references. No array payloads in MCP messages. OME-Zarr used for cross-env interchange (Constitution III alignment).
- [x] **Reproducibility**: Artifact metadata (`shape`, `dims`, `dtype`) recorded in provenance. Export format selection logged as operation parameter. Lockfiles unchanged.
- [x] **Safety + debuggability**: Invalid dimension operations produce clear errors. All metadata changes logged. Comprehensive tests for new behavior.

**Constitution Gate Status**: ✅ PASS (no violations identified)
- Constitution III amended (v0.9.0) to support native dimension preservation via `img.reader.data`

## Project Structure

### Documentation (this feature)

```text
specs/014-native-artifact-types/
├── plan.md              # This file
├── proposal.md          # Initial proposal (reference)
├── research.md          # Phase 0 output - technical research
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - getting started guide
├── contracts/           # Phase 1 output - API contracts
│   └── artifact-metadata-schema.json
└── checklists/
    └── checklist.md     # Phase 2 output - implementation checklist
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── artifacts/
│   ├── models.py        # MODIFY: Add ndim, dims, ScalarRef; enhance BioImageRef
│   ├── metadata.py      # MODIFY: Add ndim, dims extraction; table column metadata
│   └── store.py         # MODIFY: Support OME-Zarr import; format-aware export
├── registry/
│   └── dynamic/
│       └── adapters/
│           ├── xarray.py    # MODIFY: Remove 5D forcing; add native dimension output
│           └── skimage.py   # MODIFY: Native dimension handling; dimension hints
├── api/
│   └── schemas.py       # MINOR: May add OutputDimensionHints if needed

tools/
├── base/
│   ├── manifest.yaml    # MODIFY: Add dimension_requirements to function definitions
│   └── bioimage_mcp_base/
│       ├── ops/
│       │   └── export.py    # NEW: Multi-format export function
│       └── native_io.py     # NEW: Native dimension loading helpers
└── cellpose/
    └── manifest.yaml    # MODIFY: Add dimension_requirements

tests/
├── contract/
│   ├── test_artifact_native_dims.py     # NEW: Contract tests for native dimensions
│   └── test_dimension_requirements.py   # NEW: Dimension hints contract tests
├── integration/
│   ├── test_squeeze_threshold_pipeline.py  # NEW: End-to-end pipeline test
│   └── test_cross_env_dim_preservation.py  # NEW: Cross-environment test
└── unit/
    ├── artifacts/
    │   └── test_native_metadata.py      # NEW: Metadata extraction tests
    └── adapters/
        └── test_xarray_native_dims.py   # NEW: Xarray adapter tests
```

**Structure Decision**: Single project structure (Option 1). Changes are surgical modifications to existing modules with new test files.

## Complexity Tracking

> No Constitution violations requiring justification. All changes align with existing principles.

| Concern | Resolution |
|---------|------------|
| OME-TIFF output compatibility | OME-TIFF export still supported; 5D expansion happens ONLY at export boundary |
| Existing workflow replay | Recorded workflows preserve dimension metadata; replay should work unchanged |
| Tool manifest updates | Dimension hints are optional/additive; existing manifests continue to work |

## Implementation Phases

### Phase 1: Core Model & Storage
- Extend `ArtifactRef` with `ndim`, `dims` fields
- Add `ScalarRef` artifact type
- Implement `load_native()` helper using `img.reader.data`
- Extend metadata extraction for native dimensions
- Implement OME-Zarr writer in artifact store

### Phase 2: Adapter Refactoring
- Switch to native loading pattern in `XarrayAdapter`
- Update `SkimageAdapter` for native output
- Add dimension hints to adapters

### Phase 3: Export & Discovery
- Multi-format export function
- Tool manifest dimension requirements
- Enhanced `describe_function` response

### Phase 4: Integration & Testing
- End-to-end pipeline tests
- Cross-environment transfer tests
- Backward compatibility verification
