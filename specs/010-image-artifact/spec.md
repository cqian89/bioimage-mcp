# Spec 010: Standardized Image Artifacts with bioio

## Status
- **Status**: Draft
- **Date**: 2025-12-29
- **Author**: Documentation Specialist
- **Feature Area**: Artifacts, Runtimes

## Summary
Standardize on bioio's `BioImage` as the cross-environment image artifact layer. Instead of building a custom wrapper, tool environments will include `bioio` with format-appropriate plugins to provide a consistent, lazy-loaded interface to microscopy data. This ensures tools receive data in a predictable 5D (TCZYX) format regardless of underlying storage (OME-TIFF, OME-Zarr, proprietary, etc.).

## Key Design Decisions (REVISED)
- **No custom wrapper**: Use `bioio.BioImage` directly instead of a custom `ImageArtifact` class.
- **Format hints via manifests**: Use the existing `Port.format` field in tool manifests (validated by `src/bioimage_mcp/registry/manifest_schema.py`) to declare expected output formats (e.g., `OME-TIFF`, `OME-Zarr`).
- **Plugin minimalism**: Each tool environment installs only the `bioio` plugins it needs for its declared formats/capabilities (e.g., `bioio-ome-tiff` for OME-TIFF, `bioio-ome-zarr` only where OME-Zarr conversion/processing is required).
- **5D normalization**: All images are accessed as TCZYX (Time, Channel, Z, Y, X) via bioio. Singleton dimensions are automatically added for 2D/3D data.
- **Conversion boundary**: The core server orchestrates format matching using artifact metadata and manifest `Port.format` hints, but any actual conversion runs inside a tool environment (primarily `bioimage-mcp-base`) and returns new artifact references.

## Research Findings: bioio Advantages
- **BioImage class**: Unified reader API over multiple formats.
- **Lazy loading**: Native `dask` support prevents memory exhaustion for large datasets.
- **Consistent output**: Normalizes inputs to TCZYX.
- **StandardMetadata**: Normalized access to pixel sizes, channel names, acquisition info.

## Core Requirements
1. **bioio in current tool envs**: Update `envs/bioimage-mcp-base.yaml` and `envs/bioimage-mcp-cellpose.yaml` (and lockfiles) so:
   - Base includes `bioio` + `bioio-ome-tiff` and (for this spec) `bioio-ome-zarr` plus the proprietary reader plugin for CZI ingest: `bioio-czi`.
   - Cellpose includes `bioio` + `bioio-ome-tiff`.
2. **Manifest format hints**: Tool manifests declare expected formats using `Port.format` values `OME-TIFF` / `OME-Zarr` (canonical spelling) where applicable.
3. **Import conversion**: Proprietary formats (CZI, LIF, ND2) are converted to the required interchange format (typically OME-TIFF) before being passed to downstream tools. Conversion is executed within `bioimage-mcp-base`; core only orchestrates by artifact references.
4. **Export preservation**: Outputs are written using standard writers (e.g., `OmeTiffWriter`) so OME metadata (pixel sizes, channel labels) is preserved.
5. **Docs & migration**: Tutorials, AGENTS guidance, and a developer migration guide are updated to enforce the standard `BioImage` I/O pattern and format-hint conventions.
6. **Versioning & migration notes**: Any public-contract change (manifest schema fields/semantics, artifact metadata schema) includes explicit migration notes.

## Compatibility Matrix (UPDATED)

| Environment | Python | Supported Formats (practical) | Required Plugins (for this spec) |
|-------------|--------|-------------------------------|----------------------------------|
| bioimage-mcp-base | 3.13 | OME-TIFF, OME-Zarr, proprietary ingest (CZI via plugin) | `bioio`, `bioio-ome-tiff`, `bioio-ome-zarr`, plus CZI reader plugin(s) |
| bioimage-mcp-cellpose | 3.10 | OME-TIFF | `bioio`, `bioio-ome-tiff` |

Note: This spec intentionally scopes to the currently present tool environments (`base`, `cellpose`). Future tool packs must follow the same plugin + format-hint policy.

## User Stories (REVISED)
1. **Proprietary import**: An agent provides a Zeiss CZI. The system converts it to OME-TIFF in the base environment and stores it as a standard `BioImageRef`.
2. **Cross-env analysis**: Cellpose receives an OME-TIFF artifact reference and loads it via `BioImage(path).data`, receiving a consistent 5D TCZYX array.
3. **Large dataset handling**: The base environment can produce OME-Zarr artifacts for chunked workflows; tools can process lazily via dask-backed access.

## Edge Cases
- **Missing metadata**: If pixel sizes or channel names are unavailable, metadata fields may be `None`; tools must handle this without crashing.
- **Multi-scene files**: Multi-scene CZI/LIF must define a deterministic default (e.g., first scene) or require explicit selection.
- **Conversion failures**: Fail fast with a clear error and a persisted log artifact; do not create partially valid artifacts.
- **Unsupported formats**: Return a validation error before dispatching tool execution.

## Success Criteria (REVISED)
- **SC-001**: Tool environments satisfy the plugin policy in Requirement 1 and are verifiable via `python -m bioimage_mcp doctor`.
- **SC-002**: `BioImage(path).data` yields consistent 5D TCZYX across environments for supported artifacts.
- **SC-003**: A workflow can start from a CZI input and reach phasor analysis by auto-converting to OME-TIFF prior to phasor execution (phasor itself may remain OME-TIFF-only).
- **SC-004**: `StandardMetadata` (pixel sizes, channel names) is preserved through at least one write step (e.g., import -> transform -> export).

## Out of Scope
- **Custom `ImageArtifact` class**
- **OME-Zarr cloud slicing optimizations** (future performance-focused spec)
