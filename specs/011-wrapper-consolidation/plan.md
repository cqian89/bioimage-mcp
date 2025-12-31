# Implementation Plan: Spec 011: Wrapper Consolidation

**Branch**: `011-wrapper-consolidation` | **Date**: 2025-12-31 | **Spec**: `specs/011-wrapper-consolidation/spec.md`

## Summary

Eliminate 16 manual wrapper tools (`base.wrapper.*`) by introducing per-session persistent workers (per environment) and exposing a curated set of axis-aware operations as individual tools under `base.xarray.*`. These tools produce managed session-memory artifacts (`mem://`) by default for efficient same-env chaining. For cross-environment handoff, the runtime negotiates an interchange format (default OME-TIFF unless otherwise declared) and the source tool environment materializes to file-backed OME-TIFF/OME-Zarr using `bioio`; the target environment imports via `bioio` and may re-materialize to `mem://`.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic>=2.0`, `bioio`, `xarray`, `numpy`  
**Storage**: Local filesystem artifact store + SQLite index + Session-scoped memory (`mem://`)  
**Testing**: `pytest`, `pytest-asyncio`  
**Target Platform**: Local/on-prem; Linux-first (macOS/Windows best-effort)
**Project Type**: Python service + CLI  
**Performance Goals**: Avoid redundant disk I/O using persistent workers and memory-backed artifacts; minimize memory footprint by using xarray views where possible.  
**Constraints**: 
- Tool processes are persistent per MCP session and environment to allow in-memory data reuse.
- Default output for `base.xarray.*` is a `mem://` reference.
- Cross-env data transfer requires negotiated materialization to disk (OME-TIFF/Zarr).
- No large binary payloads in MCP messages; all I/O via `ArtifactRef`.
- Xarray operations must be restricted to a curated allowlist for safety.

## Constitution Check

- [x] **Stable MCP surface**: Consolidated 16 tools into dynamic `base.xarray.*` functions.
- [x] **Summary-first responses**: Dynamic tool definitions follow the standard summary/describe pattern.
- [x] **Tool execution isolated**: Compute-heavy tools run in persistent subprocesses per environment.
- [x] **Artifact references only**: All outputs use `ArtifactRef` (file or `mem://`).
- [x] **Reproducibility**: Automatic format conversions and axis transforms are recorded in the workflow provenance. `mem://` refs are ephemeral.
- [x] **Safety + debuggability**: Curated xarray method allowlist; OS OOM handled via worker restart and ref invalidation.

## Project Structure

### Documentation

```text
specs/011-wrapper-consolidation/
├── plan.md              # This file
├── research.md          # Feature research and wrapper audit
├── data-model.md        # Updated ToolManifest and XarrayAdapter models
├── quickstart.md        # Examples of using consolidated tools
├── spec.md              # Requirements and architecture decisions
└── contracts/           # New schemas for dynamic tool calling
```

### Source Code

```text
src/bioimage_mcp/
├── api/
│   ├── execution.py       # Updated ExecutionBridge for persistent workers & mem://
│   └── artifacts.py       # Support for mem:// URI scheme
├── artifacts/
│   ├── models.py          # Updated ArtifactRef for mem://
│   └── memory.py          # NEW: Memory-backed artifact store
├── registry/
│   ├── manifest_schema.py # Schema for input_mode and apply_ufunc
│   └── dynamic/
│       ├── models.py      # Pydantic models for dynamic functions
│       ├── xarray_adapter.py # NEW: Curated xarray method execution
│       └── io_bridge.py      # NEW: Coordinated cross-env handoff & negotiation
├── runtimes/
│   └── persistent.py      # NEW: Persistent worker management
│   └── executor.py        # Resolve ArtifactRef to requested view in worker
```


**Structure Decision**: Integrated logic into the existing `registry/dynamic/` pattern to avoid project fragmentation.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Persistent Workers | To enable `mem://` artifacts and avoid repeated disk I/O/decoding for large images. | Re-reading from disk for every axis operation is too slow and wastes space. |
| Managed Memory Artifacts | To provide a standard way to reference data residing in a worker's memory. | Using raw memory addresses is unsafe; custom serialization is complex. |
| Coordinated I/O Handoff | To allow seamless transition between formats (CZI, OME-TIFF) and environments. | Forcing every tool to handle CZI would bloat tool environments. |

## Implementation Steps

### Phase 1: Infrastructure & Data Models
1. **Pydantic Updates**: 
   - Add `input_mode` (Literal["path", "numpy", "xarray"]) to `FunctionDef` in `src/bioimage_mcp/registry/manifest_schema.py`.
   - Update `ArtifactRef` in `src/bioimage_mcp/artifacts/models.py` to support `mem://` URIs and storage type "memory".
2. **Persistent Worker System**:
   - Implement `PersistentWorkerManager` in `src/bioimage_mcp/runtimes/persistent.py`.
   - Logic for lazy startup, per-session/per-env lifecycle, and worker restart.
3. **Memory Artifact Registry**:
   - Implement `MemoryArtifactStore` in `src/bioimage_mcp/artifacts/memory.py` to track `mem://` references within a session.
   - Link artifact invalidation to worker crashes.

### Phase 2: Execution Engine & Adapter Updates
1. **Xarray Adapter**: 
   - Implement `XarrayAdapter` in `src/bioimage_mcp/registry/dynamic/xarray_adapter.py`.
   - Expose individual tools: `base.xarray.rename`, `base.xarray.squeeze`, etc.
2. **I/O Bridge & Cross-Env Handoff**: 
   - Implement `IOBridge` in `src/bioimage_mcp/registry/dynamic/io_bridge.py`.
   - Logic for negotiating required interchange format (default: OME-TIFF unless otherwise declared) and coordinating cross-env handoff (source export via bioio; target import via bioio).
   - Implement `base.bioio.export` for explicit materialization (agent tool).
3. **Dispatch Logic**: 
   - Update `ExecutionBridge` to use persistent workers and handle `mem://` artifacts.
   - Within the environment worker (executor), resolve `ArtifactRef` (file or mem://) to the requested view (`BioImage.data` vs `BioImage.xarray_data`) based on `input_mode`.

### Phase 3: Migration (The "Big Delete")
1. **Manifest Update**: 
   - Re-define Axis tools (`base.axis.squeeze`, etc.) using the new dynamic adapter.
   - Re-define Transform/Denoise tools using `apply_ufunc` or direct xarray methods.
2. **Wrapper Deletion**: 
   - Remove 16 files/modules in `tools/base/bioimage_mcp_base/wrapper/`.
   - Clean up `pyproject.toml` dependencies in `tools/base` if any were specific to wrappers.

### Phase 4: Verification & Logging
1. **Provenance Testing**: Verify that a "CZI -> Squeeze -> Denoise" chain correctly records the intermediate conversion and axis transformation.
2. **Integration Tests**: 
   - Test CZI input for a tool that only expects OME-TIFF.
   - Test complex axis remapping (e.g., `TCZYX` -> `ZCYX`).
3. **Performance Audit**: Ensure server-side processing doesn't block the main MCP event loop (use thread pools for I/O).
