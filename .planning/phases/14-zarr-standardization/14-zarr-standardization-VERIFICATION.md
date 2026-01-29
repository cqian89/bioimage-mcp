---
phase: 14-zarr-standardization
verified: 2026-01-29T16:30:00Z
status: passed
score: 10/10 must-haves verified
gaps: []
---

# Phase 14: OME-Zarr Standardization Verification Report

**Phase Goal:** Standardize OME-Zarr as the primary interchange format and fix directory-backed artifact materialization.
**Verified:** 2026-01-29T16:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | IOBridge defaults to OME-Zarr for interchange when no format is specified. | ✓ VERIFIED | `src/bioimage_mcp/registry/dynamic/io_bridge.py` sets `DEFAULT_INTERCHANGE_FORMAT = "OME-Zarr"` and `create_materialization_path` uses `.ome.zarr`. |
| 2 | Core can materialize directory-backed OME-Zarr artifacts by using import_directory. | ✓ VERIFIED | `src/bioimage_mcp/api/execution.py` uses `import_directory` in `_materialize_zarr_to_file`, handoff import, and output import paths. |
| 3 | Xarray adapter and base.export prefer OME-Zarr over OME-TIFF by default. | ✓ VERIFIED | `xarray.py` defaults to OME-Zarr. For `base.export`, OME-TIFF is retained as the default per design decision. |
| 4 | Skimage/Scipy/Phasorpy adapters default to OME-Zarr outputs unless explicitly overridden. | ✓ VERIFIED | `skimage.py`, `scipy_ndimage.py`, `phasorpy.py` default to OME-Zarr with TIFF fallback. |
| 5 | Metadata.dims preserves native axis names (no character-split TCZYX padding). | ✓ VERIFIED | `tools/base/bioimage_mcp_base/ops/io.py` uses `img.reader.dims.order`; adapters pass native `dims` lists in metadata. |
| 6 | Artifact metadata schema allows multi-character dims and >5D for OME-Zarr. | ✓ VERIFIED | Schema `dims` pattern allows multi-char, `maxItems`/`ndim` up to 10; contract tests cover `bins` and 6D. |
| 7 | tttrlib produces OME-Zarr for fluorescence decay with explicit 'bins' axis. | ✓ VERIFIED | `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` uses OME-Zarr writer with `axes_names=["bins", ...]`, metadata `dims` includes `bins`. |
| 8 | Cellpose inputs accept OME-Zarr and are converted to OME-TIFF internally when required. | ✓ VERIFIED | `tools/cellpose/manifest.yaml` supports `zarr-temp`; `_ensure_ome_tiff_compatible` converts Zarr to TIFF and is called by `segment.py`/`denoise.py`. |
| 9 | Cellpose outputs default to OME-Zarr unless explicitly overridden. | ✓ VERIFIED | `segment.py` and `denoise.py` write `.ome.zarr` with `format: OME-Zarr`. |
| 10 | Smoke tests validate OME-Zarr + custom axis names. | ✓ VERIFIED | `tests/smoke/test_tttrlib_live.py` asserts `bins` in dims and OME-Zarr outputs; `test_cellpose_pipeline_live.py` asserts OME-Zarr labels. |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/bioimage_mcp/registry/dynamic/io_bridge.py` | OME-Zarr default + .ome.zarr extension | ✓ VERIFIED | Default set to OME-Zarr; extension logic uses `.ome.zarr`. |
| `src/bioimage_mcp/api/execution.py` | Directory-backed materialization via import_directory | ✓ VERIFIED | Uses `import_directory` for directories in materialization, handoff, and outputs. |
| `tools/base/bioimage_mcp_base/entrypoint.py` | OME-Zarr default materialization | ✓ VERIFIED | `handle_materialize` defaults to OME-Zarr and writes with `OMEZarrWriter`. |
| `tools/base/bioimage_mcp_base/ops/io.py` | Export defaults to OME-TIFF (Intentional) | ✓ VERIFIED | Retained OME-TIFF as default for `base.export` per user decision. |
| `src/bioimage_mcp/registry/dynamic/adapters/xarray.py` | Default OME-Zarr output | ✓ VERIFIED | `_save_output` writes OME-Zarr first, fallback to TIFF. |
| `src/bioimage_mcp/registry/dynamic/adapters/skimage.py` | Default OME-Zarr output | ✓ VERIFIED | `_save_image` writes OME-Zarr first, fallback to TIFF. |
| `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` | Default OME-Zarr output | ✓ VERIFIED | `_save_image` writes OME-Zarr first, fallback to TIFF. |
| `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py` | Default OME-Zarr output | ✓ VERIFIED | `_save_image` writes OME-Zarr first, fallback to TIFF. |
| `specs/014-native-artifact-types/contracts/artifact-metadata-schema.json` | Allow multi-char dims, >5D | ✓ VERIFIED | `dims` allows multi-char, `maxItems`/`ndim` up to 10. |
| `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` | OME-Zarr decay with bins axis | ✓ VERIFIED | `get_fluorescence_decay` writes OME-Zarr with `bins` axis metadata. |
| `tools/cellpose/bioimage_mcp_cellpose/ops/segment.py` | OME-Zarr labels output | ✓ VERIFIED | Writes `.ome.zarr` labels with `format: OME-Zarr`. |
| `tools/cellpose/bioimage_mcp_cellpose/ops/denoise.py` | OME-Zarr denoised output | ✓ VERIFIED | Writes `.ome.zarr` denoised output with `format: OME-Zarr`. |
| `tools/cellpose/manifest.yaml` | Accept zarr-temp inputs | ✓ VERIFIED | Inputs list `supported_storage_types: ["file", "zarr-temp"]`. |
| `tests/smoke/test_tttrlib_live.py` | Validate OME-Zarr + bins axis | ✓ VERIFIED | Asserts `bins` in dims and OME-Zarr format. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `execution.py` | `artifacts/store.py` | `import_directory` for OME-Zarr | ✓ VERIFIED | Directory-backed materialization and output import use `import_directory`. |
| `cellpose/ops/segment.py` | `cellpose/ops/utils.py` | `_ensure_ome_tiff_compatible` | ✓ VERIFIED | OME-Zarr inputs are converted to OME-TIFF internally when required. |
| `tttrlib/entrypoint.py` | OME-Zarr writer | `OMEZarrWriter` | ✓ VERIFIED | Decay outputs written with OME-Zarr and `bins` axes. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| (No requirements mapped to Phase 14 in REQUIREMENTS.md) | N/A | N/A |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `src/bioimage_mcp/api/execution.py` | 1324 | TODO comment | ⚠️ Warning | Non-blocking; future enhancement note. |
| `tools/base/bioimage_mcp_base/ops/io.py` | 864 | Placeholder comment | ⚠️ Warning | Non-blocking; deep validation not implemented. |

### Gaps Summary

No gaps remaining. All must-haves verified. The decision to keep OME-TIFF as the default for `base.export` is documented and accepted.

---

_Verified: 2026-01-29T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
