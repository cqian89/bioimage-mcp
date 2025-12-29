# Spec 010: Standardized Image Artifacts with bioio

## Status
- **Status**: Draft
- **Date**: 2025-12-29
- **Author**: Documentation Specialist
- **Feature Area**: Artifacts, Runtimes

## Summary
Standardize on bioio's `BioImage` as the cross-environment image artifact layer. Instead of building a custom wrapper, all tool environments will include `bioio` with format-appropriate plugins to provide a consistent, lazy-loaded interface to microscopy data. This ensures that tools receive data in a predictable 5D (TCZYX) format regardless of the underlying storage (OME-TIFF, OME-Zarr, etc.).

## Key Design Decisions (REVISED)
- **No custom wrapper**: Use `bioio.BioImage` directly instead of a custom `ImageArtifact` class. This leverages a maintained industry standard and reduces project complexity.
- **Interchange format per-env**: Each environment declares its preferred interchange format. OME-TIFF is the default; OME-Zarr is used for high-performance or large-scale data environments.
- **Plugin minimalism**: To keep tool environments lightweight, each environment installs only the `bioio` plugins it strictly needs (e.g., `bioio-ome-tiff` for most, `bioio-bioformats` only where proprietary formats are handled).
- **5D normalization**: All images are accessed as TCZYX (Time, Channel, Z, Y, X) via bioio. Singleton dimensions are automatically added for 2D/3D data to ensure array shape consistency across tools.

## Research Findings: bioio Advantages
Bioio provides the core functionality required for cross-environment image handling:
- **BioImage class**: A universal wrapper that auto-detects formats and provides a unified API.
- **Lazy Loading**: Native support for lazy loading via `dask`, preventing memory exhaustion with large datasets.
- **Consistent Output**: Normalizes all inputs to TCZYX, eliminating "gotchas" with dimension ordering.
- **Multiple Access Methods**:
  - `.data`: Returns a numpy-like array (dask-backed).
  - `.dask_data`: Direct access to the dask graph.
  - `.xarray_data`: Labeled arrays for metadata-aware operations.
- **StandardMetadata**: Provides normalized access to physical pixel sizes, channel names, and acquisition info.
- **Lightweight Core**: Core dependencies (numpy, dask, xarray, ome-types) are already common in bioimaging stacks.

## Core Requirements (REVISED)
1. **bioio in all envs**: Update all `envs/*.yaml` and `envs/*.lock.yml` to include `bioio` and `bioio-ome-tiff`.
2. **Manifest format hints**: Update tool manifests (`manifest.yaml`) to declare supported/preferred formats using `interchange_format: OME-TIFF` or `interchange_format: OME-Zarr`.
3. **Import conversion**: Proprietary formats (CZI, LIF, ND2) are converted to the environment's interchange format (typically OME-TIFF) upon initial import into the artifact store.
4. **Export preservation**: Outputs are saved using standard writers (e.g., `OmeTiffWriter`) to ensure OME metadata (pixel size, channel labels) is preserved for downstream tools.

## Compatibility Matrix (UPDATED)

| Environment | Python | Interchange Format | Plugins |
|-------------|--------|--------------------|---------|
| bioimage-mcp-base | 3.13 | OME-TIFF | bioio, bioio-ome-tiff, bioio-bioformats, bioio-czi |
| bioimage-mcp-cellpose | 3.10 | OME-TIFF | bioio, bioio-ome-tiff |
| bioimage-mcp-stardist | 3.10 | OME-TIFF | bioio, bioio-ome-tiff |

## User Stories (REVISED)
1. **Proprietary Import**: An agent loads a Zeiss CZI file. The base environment uses `BioImage(czi_path)` to read it and immediately saves it as a standard OME-TIFF artifact.
2. **Cross-Env Analysis**: The Cellpose environment receives an OME-TIFF artifact reference. It loads the data via `BioImage(path).data`, receiving a consistent 5D TCZYX array without needing to know about OME-TIFF specifics.
3. **Large Dataset Handling**: An environment configured for OME-Zarr handles a multi-terabyte dataset. Because `bioio` uses dask, the tool can perform chunked processing natively without loading the entire image into RAM.

## Success Criteria (REVISED)
- **SC-001**: All tool environments have `bioio` and the `bioio-ome-tiff` plugin installed and verified via `doctor` check.
- **SC-002**: `BioImage(path).data` returns a consistent 5D TCZYX array (as a dask/numpy array) in all environments for any supported artifact.
- **SC-003**: The Phasor analysis workflow successfully processes a CZI input by auto-converting it to OME-TIFF during the initial ingest step.
- **SC-004**: `StandardMetadata` (physical pixel sizes, channel names) is correctly extracted from input artifacts and preserved through at least one transformation step.

## Out of Scope
- **Custom `ImageArtifact` class**: This spec explicitly replaces the need for a custom wrapper class.
- **Complex `FormatBroker`**: Heavyweight format conversion logic is deferred to bioio's internal plugin handling at the point of import/export.
- **OME-Zarr chunked slicing optimization**: While supported by bioio, specific optimizations for cloud-native Zarr slicing are deferred to a future performance-focused spec.
