# Spec 011: Wrapper Consolidation (Zero-Wrapper Architecture)

- **Branch**: `feat/011-wrapper-consolidation`
- **Date**: 2025-12-31
- **Status**: Proposed

## 1. Executive Summary

This feature eliminates the maintenance burden and performance overhead of manual "wrapper" tools in `bioimage-mcp`. By adopting a **Zero-Wrapper Architecture**, we replace 16+ custom axis and I/O utilities with a unified data adapter and a coordinated decentralized handoff. This transition ensures that dimension names (T, C, Z, Y, X) are preserved natively across library calls and that format compatibility (e.g., CZI to OME-TIFF) is handled transparently via source-env materialization rather than manual by the user.

## 2. User Scenarios & Testing

### [P1] Axis-Independent Image Processing
- **Why this priority**: Eliminates the need for users to understand internal memory layouts (TCZYX vs TZCYX) or write boilerplate loops, significantly reducing errors in multi-dimensional analysis.
- **Independent Test**: A workflow that processes both a 5D OME-TIFF and a 2D TIFF using the same Gaussian blur tool call, verifying both produce valid results with correct dimensionality preserved.
- **Acceptance Scenario**:
  - **Given**: A multi-dimensional image artifact with dimensions (T, C, Z, Y, X).
  - **When**: The user applies a spatial filter (like Gaussian blur) without specifying dimensions.
  - **Then**: The filter is applied to every spatial plane (YX) across all other dimensions (T, C, Z).
  - **And**: The output artifact is a memory-backed reference (`mem://...`) that retains the original dimension names and coordinate metadata.

### [P1] Transparent Format Interoperability & Persistent Workers
- **Why this priority**: Proprietary formats (CZI, LIF) are common in microscopy but rarely supported by specialized deep learning tools. Manual conversion is a major friction point for researchers. Persistent workers reduce the overhead of loading large datasets repeatedly.
- **Independent Test**: A pipeline that loads a `.czi` file and passes it directly to an OME-TIFF-only tool (like Cellpose), verifying success without any manual conversion steps in the workflow; the server coordinates a handoff where the source environment materializes the data. Subsequent calls to the same environment reuse the same worker process.
- **Acceptance Scenario**:
  - **Given**: A tool that explicitly requires OME-TIFF input.
  - **When**: The user provides an image artifact in a different format (e.g., Zeiss CZI).
  - **Then**: The system automatically negotiates an interchange format (defaulting to OME-TIFF) and performs the handoff (source-env materialization) before execution.
  - **And**: Subsequent calls to tools in the same environment reuse the same persistent worker.
  - **And**: The handoff event is recorded in the workflow provenance metadata.

### [P2] Efficient Axis Manipulation
- **Why this priority**: Different analysis libraries have different dimension expectations. Users need simple, standardized ways to reshape data without losing metadata or writing custom scripts.
- **Independent Test**: A test case that renames 'Z' to 'T' and removes singleton dimensions using `base.xarray.rename` and `base.xarray.squeeze`, verifying the resulting memory-backed artifact has the updated metadata while the data remains bit-identical.
- **Acceptance Scenario**:
  - **Given**: An image artifact with a singleton dimension 'C' and a spatial dimension 'Z'.
  - **When**: The user requests to "remove singleton dimensions" and "rename Z to T".
  - **Then**: A new `mem://` artifact is created where 'C' is gone and 'Z' is now 'T'.
  - **And**: The underlying data remains in memory within the worker process.
  - **And**: The user can explicitly call `base.bioio.export` to materialize it to a file-backed OME-TIFF.

## 3. Edge Cases
- **Format conversion failure**: If the I/O bridge cannot write the required format (e.g., target format not supported by the writer or disk space exceeded), the tool call fails with a specific `ConversionError` explaining the incompatibility, rather than a generic subprocess crash.
- **Missing dimension for rename**: If a user attempts to rename dimension 'Z' to 'T' but the artifact only contains 'Y' and 'X', the system returns a validation error before attempting execution, identifying the missing source dimension.
- **Restricted method access**: If a user attempts to call a data manipulation method that is not on the allowlist (e.g., one that would force a full memory load or insecure code execution), the system returns a "Method not permitted" error to protect server stability and security.

## 4. Requirements

### Constitution Constraints
1. **Stable MCP Surface**: The tool registry MUST be simplified. All `base.wrapper.*` tools must be deleted and replaced by a curated set of native-like data manipulation methods under the `base.xarray.*` namespace.
2. **Isolated Tool Execution via Persistent Workers**: Tools run in isolated `bioimage-mcp-*` environments. To support efficient memory-backed artifacts, the server maintains persistent worker processes per MCP session/environment.
3. **Managed Memory Artifacts**: Tools in the `base.xarray.*` namespace produce managed session-memory artifacts (`mem://<session_id>/<env_id>/<artifact_id>`). These are ephemeral across server restarts.
4. **Reproducibility & Provenance**: Every automatic format conversion or dimension transformation MUST be recorded in the workflow run logs. `mem://` outputs record minimal provenance (dims/shape/dtype); full provenance is recorded when materialized to file.
5. **Safety & Observability**: No explicit memory cap; rely on OS OOM. If a worker crashes, the server restarts it and invalidates all `mem://` references for that environment with a clear error.
6. **Cross-Env Handoff**: When passing data between different environments, the system negotiates an interchange format (defaulting to OME-TIFF). The source environment performs the export, and the target environment performs the import.
7. **Explicit Export**: Provide a `base.bioio.export` (agent tool) to force materialization of `mem://` artifacts to file-backed artifacts (e.g., OME-TIFF).

### Functional Requirements
1. **Delete all `base.wrapper.*` tools**: Remove implementation and manifest entries for axis, transform, and I/O wrappers.
2. **`input_mode: xarray` Support**: Update the tool execution layer to resolve `BioImageRef` (file or `mem://`) to `xarray.DataArray`.
3. **Declarative Dimension Mapping**: Allow tool manifests to define axis-unaware library calls (e.g., `skimage`) using parameters like `input_core_dims` and `vectorize`.
4. **Data Manipulation Adapter**: Implement a generic adapter that exposes an allowlist of dimension-aware methods as individual MCP tools under the `base.xarray.*` namespace (e.g., `base.xarray.rename`, `base.xarray.squeeze`).
5. **Persistent Worker System**: Implement lazy-started, per-session, per-env persistent workers to maintain in-memory state.
6. **Managed Memory Artifact System**: Implement the `mem://` URI scheme and artifact tracking. Handle worker crash recovery and reference invalidation.
7. **Cross-Env I/O Handoff**: Implement negotiated decentralized handoff (default OME-TIFF unless otherwise declared), where the source environment performs materialization to a file-backed artifact.
8. **Export Tool**: Implement `base.bioio.export` (agent tool) for explicit materialization of memory artifacts.
9. **CWD-Relative Paths**: Standardize `artifact_store_root` and allowlists to be relative to the Current Working Directory (CWD) by default.

### Key Entities
- **xarray.DataArray**: The internal data structure for axis-aware processing.
- **apply_ufunc Configuration**: Metadata in `manifest.yaml` governing how numpy functions are wrapped.
- **Decentralized Handoff**: Coordinated cross-env format negotiation where the source environment performs materialization to a file-backed artifact.
- **Persistent Worker**: A background process maintaining tool environment state and in-memory data.
- **mem:// Artifact**: A reference to image data residing in a persistent worker's memory.
- **BioImageRef**: The persistent, file-backed or memory-backed reference for image data.

## 5. Success Criteria

1. **Registry Simplification**: The total count of registered utility tools is reduced by at least 15 while maintaining all existing capabilities.
2. **Standardized Interface**: All axis and format manipulations use a unified, standard interface instead of many specialized wrapper tools.
3. **Feature Parity**: 100% of the functionality previously provided by specialized wrappers (renaming, squeezing, transposing) remains accessible to users.
4. **Automated Interop**: Workflows involving mismatched image formats (e.g., proprietary input to a specialized analysis tool) execute successfully via negotiated interchange formats without explicit conversion steps.
5. **Improved Efficiency**: Workflow execution for complex pipelines is faster due to reduced disk I/O through persistent workers and `mem://` artifacts.
6. **Safety & Resilience**: If memory limits are hit (OS OOM), the system recovers by restarting workers and providing clear feedback, preventing server-wide failure.
7. **Traceability**: 100% of automatic data transformations and format conversions are recorded in the workflow provenance artifacts. Final file-backed outputs contain full history.
