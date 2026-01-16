# Proposal: OME-Zarr Backed Artifact References for High-Dimensional Data

## Context and Problem Statement

### 1. Current OME-TIFF Limitations for TCSPC/FLIM Data
The current `bioimage-mcp` implementation primarily uses OME-TIFF as the interchange format for `BioImageRef`. While widely supported, the *current system conventions* strongly assume single-letter `TCZYX`-style axes and a small fixed number of dimensions in artifact metadata. This creates significant challenges for Time-Tagged Time-Resolved (TTTR) data derivatives such as FLIM decay histograms:

- **Dimension Hijacking**: There is no native dimension for microtime bins. Current tools (like `tttrlib`) are forced to hijack the `T` (Time) axis to store decay histograms.
- **Semantic Ambiguity**: When `T` is used for microtime bins, the semantic meaning of the axis becomes ambiguous. Is it a time-lapse (seconds/minutes) or a microtime decay (nanoseconds)?
- **Fragile Metadata Hints**: We currently use a metadata hint `microtime_axis: "T"` to resolve this ambiguity. This is a non-standard workaround documented in `specs/025-tttrlib/addendum.md` that requires every downstream consumer to check for this specific flag.
- **Metadata Contract Rigidity**: Even when the underlying file format can store additional dimensions, this repo’s artifact metadata contracts and some loaders assume `TCZYX`-like axes and reject multi-character axes such as `bins`.

### 2. OME-Zarr (NGFF) Advantages
OME-Zarr (Next Generation File Format) based on Zarr offers a flexible, N-dimensional alternative that directly addresses these issues:

- **Arbitrary Axis Names**: Allows explicit naming such as `bins`, `microtime`, or `harmonic`.
- **Explicit Axis Types**: Supports defining axis types (`time`, `channel`, `space`, or custom) and per-axis units (e.g., `nanoseconds` vs `seconds`).
- **N-Dimensional Support**: Not limited to 5 or 6 dimensions.
- **Cloud-Native & Chunked**: Better performance for very large datasets and remote storage.
- **Ecosystem Support**: `bioio` and `bioio-ome-zarr` already provide robust support for reading and writing OME-Zarr with custom axes.

---

## Scope Options to Evaluate

### Option A: OME-Zarr only for TTTRRef derivatives (Minimal Change)
Focus OME-Zarr usage specifically on FLIM/TTTR outputs where the OME-TIFF 5D limit is most painful.
- **Pros**: Minimal disruption to existing workflows; solves the immediate FLIM ambiguity.
- **Cons**: Creates a bifurcated artifact system where some images are TIFF and others are Zarr.

### Option B: OME-Zarr as Primary Interchange Format (Large Migration)
Transition the entire system to prefer OME-Zarr for all internal artifact references.
- **Pros**: Uniform system; future-proof for all modalities.
- **Cons**: Significant migration effort; potentially breaks tools that expect local TIFF files (like some older Cellpose versions or Fiji users).

### Option C: Format Negotiation (Flexible, Complex)
Allow tools to declare their preferred input/output formats in their `manifest.yaml`.
- **Pros**: Maximum flexibility; allows the system to choose the best format for each step.
- **Cons**: High implementation complexity in the core server for negotiation and auto-conversion.

---

## Technical Feasibility

### bioio Integration Assessment
The project already relies on `bioio` for abstraction.
- `bioio_ome_zarr.writers.OMEZarrWriter` already supports:
  - Custom `axes_names` (e.g., `["bins", "z", "y", "x"]`)
  - Custom `axes_types` (e.g., `["other", "space", "space", "space"]`)
  - Zarr v2 and v3 formats.
- `bioio.BioImage` handles OME-Zarr seamlessly, and its `xarray` reader preserves dimension names.

### Current OME-Zarr Usage in Codebase
OME-Zarr is already present in several areas:
- `slice_image` (in `tools/base/bioimage_mcp_base/ops/io.py`) uses OME-Zarr to persist sliced results with native dimension names.
- The `xarray` adapter fallback (`src/bioimage_mcp/registry/dynamic/adapters/xarray.py`) uses OME-Zarr for results that don't fit the OME-TIFF 5D model.
- `storage_type: "zarr-temp"` is already a recognized field in the artifact store.

### Impact on Existing Workflows
- **Cellpose**: Requires OME-TIFF (or similar local file). If an artifact is Zarr, it would need conversion before being passed to Cellpose.
- **PhasorPy**: Works with `xarray` and `numpy`, so OME-Zarr is actually more native to its internal data model than OME-TIFF.
- **Workflow Replay**: OME-Zarr directories are slightly more complex to manage than single-file TIFFs but are fully supported by the current artifact store.

---

## Recommended Approach: Option A with Enhancements

We recommend **Option A (Targeted OME-Zarr)** with the following enhancements:

1.  **Schema + metadata normalization (prefer NGFF-native axes)**: OME-Zarr already carries axis names/types in NGFF metadata, and `bioio` preserves them when loading via `img.reader.xarray_data`. The missing piece in this repo is that artifact metadata contracts and some loaders assume single-letter `TCZYX`. Update artifact metadata to allow `dims: list[str]` with arbitrary names (e.g., `"bins"`) so agents and non-xarray tools can reason about axes *without opening the file*.
2.  **Explicit FLIM Axis Support**: Use OME-Zarr for all `get_fluorescence_decay` outputs, using the axis name `bins` (or `microtime`) instead of hijacking `T`.
3.  **Conversion policy: user-facing export only**: Keep format conversion agent-visible via `base.io.bioimage.export`, which already supports `OME-TIFF`, `OME-Zarr`, `PNG`, and `NPY`. If helper utilities are added, keep them internal to tool implementations (not exposed via the MCP run interface).
4.  **Preserve OME-TIFF Default**: Keep OME-TIFF as the default for standard 2D/3D/5D intensity images to maintain compatibility with the majority of external tools.

---

## Implementation Plan

### Phase 1: Schema + Metadata Normalization (Medium Risk)
- Update the artifact metadata contract schema to allow arbitrary `dims: list[str]` (including multi-character names like `"bins"`) and to relax the current 5D/`TCZYX` constraints for OME-Zarr-backed artifacts.
- Normalize loaders/metadata extraction to avoid character-splitting dimension strings (e.g., `list("TCZYX")`) so multi-character axes are representable in `BioImageRef.metadata`.
- Add `.ome.zarr`/`.zarr` detection in base I/O format sniffing so Zarr-backed artifacts report `format="OME-Zarr"` consistently (otherwise `base.io.bioimage.load` will likely report `format="Unknown"` for Zarr directories).

### Phase 2: OME-Zarr for FLIM Data (Medium Risk)
- **Prerequisite**: Phase 1 schema changes merged (artifact metadata must allow axes like `bins`).
- Update `tttrlib.CLSMImage.get_fluorescence_decay` to write OME-Zarr with axes `['bins', ...]` and axis type `"other"` for bins.
- Preserve axis units (nanoseconds/picoseconds) and pixel sizes when writing OME-Zarr (plumb from TTTR header and/or input image metadata where available).
- Update smoke tests to validate the new output (OME-Zarr + bins axis) and stop asserting `microtime_axis: "T"`.

### Phase 3: Internal-only Conversion Helpers (Low Risk)
- If conversion helpers are needed to simplify tool implementation, keep them internal to the base tool pack (do not add them to `tools/base/manifest.yaml`).
- Keep the public/agent-facing conversion workflow as `base.io.bioimage.export`.

---

## Constitution Compliance
- **Principle III: Artifact References Only**: OME-Zarr is an industry-standard, typed, file-backed format.
- **Principle II: Isolated Tool Execution**: Format conversion logic will reside within the tool environments or the base toolkit, ensuring the core server remains lightweight.
- **Principle VI: Test-Driven Development**: All new metadata and conversion logic will be verified with contract tests before implementation.

---

## Risks and Mitigations
| Risk | Mitigation |
| :--- | :--- |
| **Tool Compatibility** | Convert Zarr-backed artifacts to OME-TIFF using `base.io.bioimage.export` when a legacy tool requires a TIFF path (optionally wrapped by internal-only helpers). |
| **Directory Overhead** | OME-Zarr creates many small files. For small datasets, we can continue using OME-TIFF. |
| **User Complexity** | Ensure `export` function remains the primary way users interact with files, supporting both formats. |

---

## Success Criteria
- FLIM decay histograms produced by `tttrlib` use OME-Zarr with an explicit `bins` axis.
- No further use of `microtime_axis: "T"` hijacking in new code.
- Existing workflows (Cellpose, basic image ops) continue to work without modification.
- Agents can infer axis semantics from a combination of NGFF metadata (when opening the file) and artifact metadata (`metadata.dims` for offline reasoning) without relying on ad-hoc per-tool hints.

---

## Appendix A: Current Codebase Analysis

### Files Requiring Modification for Phase 1 (Schema + Metadata Normalization)
| File | Change Required |
|------|-----------------|
| `specs/014-native-artifact-types/contracts/artifact-metadata-schema.json` | Relax `dims` and `ndim` constraints so OME-Zarr artifacts can represent axes like `bins` and >5D outputs |
| `tools/base/bioimage_mcp_base/ops/io.py` | Ensure `base.io.bioimage.load` reports `metadata.dims` as `list[str]` (not character-split); detect `.ome.zarr` as `format="OME-Zarr"`; preserve units/pixel sizes when writing OME-Zarr in `slice`/`export` paths where possible |
| `src/bioimage_mcp/registry/dynamic/adapters/xarray.py` | Preserve units/pixel sizes when writing fallback OME-Zarr (currently hardcoded units=None and pixel size=1.0) |

### Files Requiring Modification for Phase 2 (tttrlib OME-Zarr)
| File | Change Required |
|------|-----------------|
| `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` | Replace `OmeTiffWriter` decay writing with `OMEZarrWriter` and write a `bins` axis |
| `tools/tttrlib/manifest.yaml` | Ensure decay outputs declare `format: OME-Zarr` (and update any schema/contracts if present) |
| `tests/smoke/test_tttrlib_live.py` | Update assertions from `microtime_axis=="T"` to OME-Zarr + `bins` axis validation |

### Files Requiring Modification for Phase 3 (Internal conversion helpers)
| File | Change Required |
|------|-----------------|
| `tools/base/bioimage_mcp_base/` | Add internal helper(s) as needed (do not expose via `tools/base/manifest.yaml`) |

Note: Conversion is already exposed via `base.io.bioimage.export` and core export is copy-only (format conversion is intentionally not supported in core).

---

## Appendix B: OME-Zarr Writer Configuration for FLIM Data

### Recommended Axis Configuration for Decay Histograms

Note: This is the target configuration. Several current code paths in this repo write OME-Zarr without units/pixel sizes (or hardcode defaults), so preserving `axes_units` and physical scale requires plumbing work as part of Phase 1/2.

```python
from bioio_ome_zarr.writers import OMEZarrWriter

# For stacked decay: shape (n_bins, Y, X)
writer = OMEZarrWriter(
    store=str(out_path),
    level_shapes=[decay_data.shape],
    dtype=decay_data.dtype,
    axes_names=["bins", "y", "x"],        # NOT ["t", "y", "x"]!
    axes_types=["other", "space", "space"],
    axes_units=["nanoseconds", "micrometer", "micrometer"],
    zarr_format=2,
)
writer.write_full_volume(decay_data)
```

### Recommended Axis Configuration for Multi-frame Decay

```python
# For multi-frame decay: shape (n_bins, Z, Y, X)
writer = OMEZarrWriter(
    store=str(out_path),
    level_shapes=[decay_data.shape],
    dtype=decay_data.dtype,
    axes_names=["bins", "z", "y", "x"],
    axes_types=["other", "space", "space", "space"],
    axes_units=["nanoseconds", "micrometer", "micrometer", "micrometer"],
    zarr_format=2,
)
```

---

## Appendix C: Comparison with Current T-Axis Hijacking

### Current Implementation (specs/025-tttrlib)
```python
# entrypoint.py lines 671-686
if decay_data.ndim == 3:  # (Y, X, bins) - stacked
    decay_data = np.moveaxis(decay_data, -1, 0)  # (bins, Y, X)
    dim_order = "TYX"  # WRONG SEMANTICS!
elif decay_data.ndim == 4:  # (Z, Y, X, bins)
    decay_data = np.moveaxis(decay_data, -1, 0)  # (bins, Z, Y, X)
    dim_order = "TZYX"  # WRONG SEMANTICS!

OmeTiffWriter.save(decay_data, str(out_path), dim_order=dim_order)
# Metadata workaround:
output["metadata"]["microtime_axis"] = "T"  # Fragile hint
```

### Proposed Implementation
```python
# No axis hijacking needed!
axes_names = ["bins", "y", "x"] if decay_data.ndim == 3 else ["bins", "z", "y", "x"]
axes_types = ["other"] + ["space"] * (len(axes_names) - 1)

writer = OMEZarrWriter(
    store=str(out_path),
    axes_names=axes_names,
    axes_types=axes_types,
    ...
)
# Metadata is semantically correct by default
# (NGFF carries the axis names/types; artifact metadata should mirror dims so agents can reason
# about axes without re-opening the file.)
output["metadata"]["dims"] = axes_names
# Optional: add an explicit role mapping for offline reasoning
output["metadata"]["axis_roles"] = {"bins": "microtime_histogram"}
```

---

## Appendix D: Downstream Tool Compatibility Matrix

| Tool | Current Format | OME-Zarr Compatible | Auto-Convert Needed |
|------|----------------|---------------------|---------------------|
| PhasorPy | OME-TIFF (via numpy) | ✅ Yes (works with xarray) | No |
| Cellpose | OME-TIFF | ❌ No (requires local file) | Yes → OME-TIFF |
| napari | Both | ✅ Yes | No |
| ImageJ/Fiji | OME-TIFF | ❌ No | Yes → OME-TIFF |
| base.xarray ops | Both | ✅ Yes | No |
| base.skimage ops | Both (via bioio) | ✅ Yes | No |

---

## Appendix E: Migration Path for Existing Workflows

### Backward Compatibility Guarantee
All existing workflows that use OME-TIFF will continue to work unchanged. The migration is strictly additive:

1. **No breaking changes to existing `BioImageRef` consumers**: new fields remain optional, and existing `TCZYX` metadata stays valid.
2. **No changes to export behavior**: `base.io.bioimage.export` continues to support exporting to `OME-TIFF` (and now also `OME-Zarr`, `PNG`, `NPY`).
3. **No changes to Cellpose workflows**: Cellpose continues to receive OME-TIFF as before.

### Gradual Rollout
1. **Phase 1**: Relax artifact metadata contract schema for OME-Zarr-backed artifacts and normalize loaders to support multi-character axes.
2. **Phase 2**: Switch tttrlib decay outputs to OME-Zarr with `bins` axis; remove reliance on `microtime_axis`.
3. **Phase 3**: Add internal-only conversion helpers if needed, keeping the public interface as `base.io.bioimage.export`.

---

## Appendix F: Open Questions

1. **Should phasor outputs also use OME-Zarr?** Currently stored as OME-TIFF with C=2 (g, s channels). Could benefit from explicit axis names.
2. **What about multi-harmonic phasors?** Could use axis name "harmonic" with type "other".
3. **Do we need any extra axis semantics beyond NGFF?** Prefer relying on NGFF axis names/types/units when possible. If we add anything to artifact metadata, keep it small and optional (e.g., `metadata.axis_roles: dict[str, str]`) for offline agent reasoning.
4. **How to handle axis unit preservation in cross-format conversion?** OME-TIFF has limited unit support; units may be lost on conversion.
