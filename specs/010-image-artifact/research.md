# Research: Image Artifact Wrapper & bioio Standardization

## Background
Bioimage analysis involves a fragmented ecosystem of file formats (OME-TIFF, Zarr, CZI, etc.) and libraries (scikit-image, cellpose, phasorpy). Tools often have strict requirements (e.g., `phasorpy` requiring OME-TIFF files or numpy arrays).

## Findings: bioio Provides What We Need
Research into the `bioio` library reveals it provides a robust, standardized foundation that eliminates the need for a custom wrapper class.

- **BioImage class**: A universal wrapper that auto-detects format and provides a unified API. It handles the complexity of different readers behind a single interface.
- **Consistent 5D output**: All inputs are normalized to TCZYX (Time, Channel, Z, Y, X). This eliminates the common "dimension swap" bugs when moving between different imaging modalities.
- **Multiple access methods**:
  - `.data`: Standard access, returns a dask-backed array that behaves like a numpy array.
  - `.dask_data`: Direct access for custom dask graphs.
  - `.xarray_data`: Returns labeled arrays, preserving axis names and metadata.
- **StandardMetadata**: Normalized access to pixel sizes, channel names, and acquisition info across different formats.
- **Lightweight**: Core dependencies (numpy, dask, xarray, ome-types, fsspec) are standard in the bioimage stack. It avoids heavy ML frameworks, making it safe for the core server.
- **Plugin system**: Format-specific readers (CZI, LIF, ND2, OME-TIFF) are installed as plugins. This allows per-environment customization of format support.

## Cross-Environment Strategy
Instead of a custom `FormatBroker`, we will implement a decentralized but standardized approach:

1. **Universal Installation**: Install `bioio` and the essential `bioio-ome-tiff` plugin in ALL tool environments.
2. **Declaration of Intent**: Each environment/tool declares its preferred interchange format (OME-TIFF or OME-Zarr) in its manifest.
3. **Dispatch Compatibility**: The server ensures format compatibility before dispatching a tool call. If the input artifact is in a proprietary format (e.g., CZI) and the tool environment only supports OME-TIFF, the server performs a one-time conversion.
4. **Standard Loading**: Tools load data via `BioImage(path).data`. This ensures they always receive a consistent 5D array regardless of the file format on disk.

## Conclusion
Standardizing on `bioio.BioImage` provides a more sustainable and interoperable path than building a custom `ImageArtifact` wrapper. It leverages existing community work while satisfying all project requirements for lazy loading, 5D normalization, and metadata preservation.
