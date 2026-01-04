# Research: Bioimage I/O Functions

**Feature**: 015-bioio-functions  
**Date**: 2026-01-04

## Research Tasks Completed

### 1. BioIO API for Metadata Extraction

**Question**: How to extract metadata without loading full pixel data?

**Decision**: Use `BioImage(path)` with lazy loading properties
- `img.dims` - dimension order (e.g., "TCZYX")
- `img.shape` - array shape
- `img.physical_pixel_sizes` - (Z, Y, X) in microns
- `img.channel_names` - list of channel names
- `img.metadata` - full OME metadata dict

**Rationale**: BioIO uses lazy loading by default. These properties access metadata without computing pixel arrays.

**Alternatives Considered**:
- tifffile direct access - less consistent across formats
- ome-types parsing - requires knowing format upfront

### 2. Slicing Multi-dimensional Images

**Question**: Best approach for dimension-aware slicing with metadata preservation?

**Decision**: Use xarray-backed loading with `.isel()` for named dimension slicing
- Load via `img.reader.xarray_data` for native dimensions
- Apply `.isel()` with dimension names (T, C, Z, Y, X)
- Preserve `attrs` for physical metadata

**Rationale**: xarray provides named dimension indexing with coordinate/attribute preservation. Aligns with existing `base.xarray.*` tools.

**Alternatives Considered**:
- Raw numpy slicing - loses dimension names and metadata
- Custom indexing wrapper - unnecessary complexity

### 3. Format Support Discovery

**Question**: How to query available format readers?

**Decision**: Use `bioio.plugins.entry_points()` or `bioio.BioImage.determine_reader()` introspection
- Get list of installed reader plugins
- Map to user-friendly format names (CZI, LIF, OME-TIFF, etc.)

**Rationale**: BioIO's plugin architecture exposes registered readers.

**Alternatives Considered**:
- Hardcoded list - becomes stale
- Try/catch on file extensions - unreliable

### 4. File Validation Approach

**Question**: What validation checks are meaningful for bioimages?

**Decision**: Multi-level validation:
1. **Existence**: File exists and is readable
2. **Format**: BioIO can instantiate a reader
3. **Metadata**: At least 2 spatial dimensions (Y, X)
4. **Integrity**: No truncation warnings from reader

**Rationale**: Catches common issues before pipeline execution.

**Alternatives Considered**:
- Deep pixel validation - too expensive for pre-flight check
- Extension-only check - misses corrupt files

### 5. Export Format Strategy

**Question**: How to handle export to different formats?

**Decision**: Reuse existing export.py logic with format routing:
- OME-TIFF: `bioio.writers.OmeTiffWriter` (expand to 5D)
- OME-Zarr: `bioio_ome_zarr.writers.OMEZarrWriter` (native dims)
- PNG: PIL for 2D uint8/uint16
- CSV: pandas/shutil for TableRef

**Rationale**: Existing implementation is robust. Just needs reorganization.

**Alternatives Considered**:
- New export implementation - unnecessary work
- Format plugins - over-engineered for 4 formats

### 6. Removing base.bioio.export

**Question**: What references need updating?

**Decision**: 
- Remove from manifest.yaml (line ~255-281)
- Remove ops/export.py file (or rename to io.py)
- Update entrypoint.py dispatch table
- No external dependencies found on `base.bioio.export`

**Rationale**: Clean break acceptable per Early Development Policy (Constitution VII).

## Dependencies Verified

| Dependency | Version | Purpose | Status |
|------------|---------|---------|--------|
| bioio | >=0.1.0 | Core image I/O | ✅ Already in base env |
| bioio-ome-tiff | >=0.1.0 | OME-TIFF read/write | ✅ Already in base env |
| bioio-ome-zarr | >=0.1.0 | OME-Zarr read/write | ✅ Already in base env |
| pydantic | >=2.0 | Schema validation | ✅ Already in base env |
| pillow | any | PNG export | ✅ Already in base env |

## Open Questions (None)

All technical unknowns resolved. Ready for Phase 1 design.
