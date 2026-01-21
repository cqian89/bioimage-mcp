# Phase 0 Prerequisites: ScipyNdimageAdapter Migration and Dataset Inventory

This document covers two Phase 0 prerequisites mentioned in the proposal.md but missing from tasks.md.

---

## SECTION 1: ScipyNdimageAdapter Migration to OmeTiffWriter

### Current State (Bug)
The current `scipy_ndimage.py` adapter at `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py`:
- Uses `tifffile.imwrite(path, array)` for saving images (line 179)
- But labels the artifact as `format: OME-TIFF` (line 191)
- This is a correctness bug - it claims to be OME-TIFF but isn't

### Target State
Migrate to use `bioio.writers.OmeTiffWriter` like the `SkimageAdapter` does.

### Migration Pattern (based on skimage.py lines 357-388)
Document this exact pattern from skimage.py:

```python
def _save_image(self, array: np.ndarray, work_dir: Path | None = None, axes: str | None = None) -> dict:
    """Save image array to file and return artifact reference dict."""
    ext = ".ome.tiff"  # Use .ome.tiff extension
    
    # Handle dtype conversion for 64-bit integers
    if array.dtype == np.int64 or array.dtype == np.uint64:
        array = array.astype(np.uint32)
    
    # Create output path
    if work_dir is None:
        fd, path_str = tempfile.mkstemp(suffix=ext)
        import os
        os.close(fd)
        path = Path(path_str)
    else:
        work_dir.mkdir(parents=True, exist_ok=True)
        path = work_dir / f"output{ext}"
    
    # Infer axes from array dimensions
    def _infer_axes(array: np.ndarray) -> str:
        axes_map = {2: "YX", 3: "ZYX", 4: "CZYX", 5: "TCZYX"}
        return axes_map.get(array.ndim, "")
    
    if axes and len(axes) == array.ndim:
        inferred_axes = axes
    else:
        inferred_axes = _infer_axes(array)
    
    # Save using OmeTiffWriter with tifffile fallback
    saved = False
    try:
        from bioio.writers import OmeTiffWriter
        if len(inferred_axes) == array.ndim:
            OmeTiffWriter.save(array, str(path), dim_order=inferred_axes)
            saved = True
    except Exception:
        pass
    
    if not saved:
        if tifffile is None:
            raise RuntimeError("tifffile is required for saving images")
        metadata = {"axes": inferred_axes} if inferred_axes else None
        tifffile.imwrite(path, array, metadata=metadata, photometric="minisblack")
    
    # Return artifact reference
    return {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": path.absolute().as_uri(),
        "path": str(path.absolute()),
        "metadata": {
            "axes": inferred_axes,
            "dims": list(inferred_axes) if inferred_axes else [],
            "ndim": array.ndim,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
        },
    }
```

### Key Changes Required
1. Change extension from `.tif` to `.ome.tiff`
2. Add dtype conversion for int64/uint64 to uint32
3. Import and use `OmeTiffWriter.save()` with `dim_order` parameter
4. Add fallback to `tifffile.imwrite` for edge cases
5. Update metadata structure to include `axes` field

### Testing
- Run existing contract tests: `pytest tests/contract/test_scipy_adapter.py -v`
- Run unit tests: `pytest tests/unit/adapters/test_scipy_ndimage_objectref.py -v`

---

## SECTION 2: Dataset Inventory and LFS Verification

### Available Datasets

| Dataset Path | Size | LFS Status | Suitable For |
|-------------|------|------------|--------------|
| `datasets/synthetic/test.tif` | 32 KB | In repo | smoke_minimal, scipy/skimage equivalence tests |
| `datasets/FLUTE_FLIM_data_tif/Embryo.tif` | Large | LFS | PhasorPy equivalence, FLIM workflows |
| `datasets/FLUTE_FLIM_data_tif/hMSC control.tif` | Large | LFS | Cellpose equivalence tests |
| `datasets/FLUTE_FLIM_data_tif/Fluorescein_Embryo.tif` | Large | LFS | PhasorPy calibration reference |
| `datasets/tttr-data/` | 109 MB | LFS | tttrlib integration tests |
| `datasets/sample_czi/` | 42 MB | LFS | CZI format validation |
| `datasets/sample_data/*.csv` | <1 MB | In repo | Pandas equivalence tests |

### LFS Configuration
- All files under `datasets/**` are tracked by Git LFS (see `.gitattributes`)
- Users must run `git lfs install && git lfs pull` to fetch actual content
- Tests MUST use the LFS pointer detection pattern to skip gracefully

### LFS Pointer Detection Pattern (from research.md)
```python
def is_lfs_pointer(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size > 1024:
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(100).decode("utf-8", errors="ignore")
            return "version https://git-lfs.github.com/spec/v1" in head
    except Exception:
        return False

def skip_if_lfs_pointer(path: Path):
    if is_lfs_pointer(path):
        pytest.skip(f"Dataset '{path}' is a Git LFS pointer (content not fetched)")
```

### Dataset Recommendations per Library

| Library | Dataset for smoke_minimal | Dataset for smoke_full |
|---------|---------------------------|------------------------|
| scipy.ndimage | `datasets/synthetic/test.tif` | Same (deterministic) |
| skimage | `datasets/synthetic/test.tif` | Same (deterministic) |
| phasorpy | Synthetic 3D array (code-gen) | `datasets/FLUTE_FLIM_data_tif/Embryo.tif` |
| cellpose | N/A (skip in minimal) | `datasets/FLUTE_FLIM_data_tif/hMSC control.tif` |
| matplotlib | N/A (plot validation) | Same (semantic only) |
| xarray | Synthetic DataArray (code-gen) | Same (deterministic) |
| pandas | `datasets/sample_data/*.csv` | Same |

### Additional Datasets If Needed

For certain tests, open-license datasets under 100 MB can be obtained from:

1. **Cell Image Library** (http://cellimagelibrary.org/) - CC licenses, various cell types
2. **Broad Bioimage Benchmark Collection** (https://bbbc.broadinstitute.org/) - CC0/CC-BY, <100MB per dataset
3. **Zenodo microscopy datasets** - Search for "fluorescence microscopy" with size filter
4. **PhasorPy test data** - Bundled with PhasorPy package (small synthetic files)

If adding new datasets:
1. Place in `datasets/<dataset-name>/`
2. Include a README.md with provenance and license
3. LFS tracking is automatic (via .gitattributes)
4. Add to this inventory table

---

## Summary: Phase 0 Task Definitions

### T000a: Migrate ScipyNdimageAdapter to OmeTiffWriter
**File**: `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py`
**Changes**:
1. Update `_save_image()` method following the skimage.py pattern
2. Change extension to `.ome.tiff`
3. Add dtype handling for int64/uint64
4. Use OmeTiffWriter with tifffile fallback
5. Verify with existing tests

### T000b: Verify Dataset LFS Status
**Checklist**:
- [ ] Confirm `.gitattributes` tracks `datasets/**`
- [ ] Document all datasets in this inventory
- [ ] Verify each dataset folder has README with provenance
- [ ] Add missing LICENSE files where needed
- [ ] Test LFS pointer detection works correctly
