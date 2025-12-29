# Implementation Plan: 010-image-artifact (Bioio-based)

This plan implements standardized image artifact handling using `bioio` across all environments. Instead of custom wrappers, we leverage `bioio.BioImage` for consistent, lazy-loaded, 5D TCZYX access to microscopy data.

## Phase 1: Environment Updates (Foundation)
- **Location**: `envs/*.yaml`
- **Tasks**:
    - Update `bioimage-mcp-base.yaml`: Ensure `bioio`, `bioio-ome-tiff`, `bioio-bioformats`, and `bioio-czi` are present (verified: already mostly done).
    - Update `bioimage-mcp-cellpose.yaml`: Add `bioio` and `bioio-ome-tiff`.
    - Update any other tool environment YAMLs to include at least `bioio` and `bioio-ome-tiff`.
    - Regenerate lockfiles for all updated environments using `conda-lock`.
- **Tests**: 
    - Run `python -m bioimage_mcp doctor` to verify environment health.
    - Scripted bioio import tests in each environment (verify `import bioio`).

## Phase 2: Manifest Schema Updates
- **Location**: `src/bioimage_mcp/registry/manifest_schema.py`
- **Tasks**:
    - Update `FunctionDefinition` Pydantic model to include an `interchange_format` field.
    - Define `InterchangeFormat` Enum: `OME_TIFF` (default), `OME_ZARR`.
    - Update manifest validation logic to handle these new fields.
    - Update `tools/base/manifest.yaml` and `tools/cellpose/manifest.yaml` to explicitly declare their preferred format (hinting for potential auto-conversion).
- **Tests**: 
    - Manifest validation unit tests in `tests/unit/registry/test_manifest_schema.py`.

## Phase 3: Tool Code Standardization
- **Location**: `tools/` packages
- **Tasks**:
    - **Cellpose**: Replace `tifffile.imread` or other direct I/O with `BioImage(path).data`.
    - **Base Tools**: Ensure consistent use of `BioImage` for all input reading.
    - **Standard Pattern**: Implement and document the pattern:
      ```python
      from bioio import BioImage
      img = BioImage(path)
      data = img.data # 5D TCZYX dask-backed array
      # Process data...
      ```
    - Ensure tools handle the 5D normalization (adding/squeezing dimensions as needed for specific algorithms).
- **Tests**: 
    - Integration tests for `cellpose.segment` and base tools with OME-TIFF inputs.

## Phase 4: Import/Export Flow Updates
- **Location**: `tools/base/bioimage_mcp_base/io.py`, `src/bioimage_mcp/api/`
- **Tasks**:
    - Simplify `load_image_fallback` to use `BioImage` directly for all supported formats.
    - Update `export_ome_tiff` helper to use `BioImage` and `OmeTiffWriter` for consistent metadata preservation.
    - Implement `ensure_interchange_format(path, target_format)` helper in the server-side runtime/api to handle on-the-fly conversion if a tool receives a format it doesn't explicitly list as supported (using the manifest hints).
- **Tests**: 
    - Round-trip integration tests: `proprietary format -> import (conversion) -> tool process -> export`.

## Phase 5: Artifact Metadata Enrichment
- **Location**: `src/bioimage_mcp/artifacts/models.py`, `src/bioimage_mcp/api/artifacts.py`
- **Tasks**:
    - Create a helper function to extract `StandardMetadata` from a `BioImage` instance.
    - Update `ArtifactRef` creation logic to populate the `metadata` field with:
        - `shape`: 5D TCZYX shape
        - `pixel_sizes`: Physical units (microns, etc.)
        - `channel_names`: Labels for channels
        - `dtype`: Data type (uint8, float32, etc.)
    - Ensure this metadata is available to the LLM via `describe_artifact`.
- **Tests**: 
    - Unit tests for metadata extraction from various formats (CZI, OME-TIFF).

## Phase 6: Documentation & Migration
- **Tasks**:
    - Update `docs/tutorials/` (e.g., `cellpose_segmentation.md`, `flim_phasor.md`) to reflect the new `BioImage` usage pattern.
    - Update `AGENTS.md` with the standard `BioImage` loading pattern for tool developers.
    - Create a "Migration Guide for Tool Developers" in `docs/developer/image_handling.md`.
- **Deliverables**: 
    - Updated tutorials, AGENTS.md, and new developer guide.

## Testing Strategy
- **Unit**: Verify `BioImage` loading and metadata extraction in isolation.
- **Contract**: Validate manifest schemas with the new `interchange_format` field.
- **Integration**: Full workflow tests starting from tiffs (e.g., `datasets/FLUTE_FLIM_data_tif`) through to analysis.

## Dependencies
- `bioio >= 1.0`
- `bioio-ome-tiff`
- `bioio-bioformats` (for the base environment to handle proprietary formats)

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| `bioio` version conflicts with `torch` in Cellpose env | Pin compatible versions in `conda-lock`; test isolation. |
| Large dependency footprint in simple tool envs | `bioio` core is lightweight; only install required plugins per env. |
| Python version incompatibility | `bioio` supports 3.9+, ensuring compatibility with all current environments (3.10 and 3.13). |
