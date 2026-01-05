# Tool Reference

## Tools.Base (`bioimage-mcp-base`)

General purpose image processing tools for bioimage analysis.

### Image I/O & Export

*   `base.io.bioimage.export`: Export image to file-backed artifact (OME-TIFF or OME-Zarr). Used for explicit materialization or cross-environment handoff.
    *   **Inputs**: `image` (BioImageRef, required)
    *   **Params**:
        *   `format` (string): Output format (`OME-TIFF` or `OME-Zarr`). Default: `OME-TIFF`.
        *   `path` (string, optional): Target file path.
    *   **Outputs**: `output` (BioImageRef, file-backed)

### Axis Manipulation (xarray-based)

> **Note**: These tools produce memory-backed artifacts (`mem://`) by default for efficient chaining within the same tool environment. Use `base.io.bioimage.export` to materialize to disk when needed.

#### `base.xarray.rename`
Description: Rename dimension labels (e.g., Z -> T) while preserving metadata.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `mapping` (object, required): Map of `old_dim` -> `new_dim`.
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.rename(image=<ref>, mapping={"Z": "T"})
```

#### `base.xarray.squeeze`
Description: Remove singleton (size=1) dimensions.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, optional): Specific dimension name to squeeze. If omitted, squeezes all singleton dimensions.
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.squeeze(image=<ref>, dim="C")
```

#### `base.xarray.expand_dims`
Description: Add a new dimension at a specified position.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Name for the new dimension.
*   `axis` (integer, optional): Position to insert new dimension (0=first, -1=before last).
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.expand_dims(image=<ref>, dim="T", axis=0)
```

#### `base.xarray.transpose`
Description: Reorder dimensions (replaces `base.moveaxis`, `base.swap_axes`).
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dims` (array of strings, required): Ordered list of dimension names.
Outputs:
*   `output` (BioImageRef, mem://)
Example usage:
```
base.xarray.transpose(image=<ref>, dims=["T", "C", "Z", "Y", "X"])
```

### Reductions (xarray-based)

#### `base.xarray.sum`
Description: Reduce along a named dimension using sum projection.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Dimension to reduce.
Outputs:
*   `output` (BioImageRef, mem://)

#### `base.xarray.max`
Description: Reduce along a named dimension using maximum projection.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Dimension to reduce.
Outputs:
*   `output` (BioImageRef, mem://)

#### `base.xarray.mean`
Description: Reduce along a named dimension using mean average.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `dim` (string, required): Dimension to reduce.
Outputs:
*   `output` (BioImageRef, mem://)

### Transforms (xarray-based)

#### `base.xarray.isel`
Description: Select along dimensions by integer indexing or slices (replaces `base.crop`).
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `selections` (kwargs): Dimension names mapped to indices or slices (e.g., `Y={"start": 10, "stop": 50}`).
Outputs:
*   `output` (BioImageRef, mem://)

#### `base.xarray.pad`
Description: Pad along dimensions.
Inputs:
*   `image` (BioImageRef, required)
Parameters:
*   `padding` (kwargs): Dimension names mapped to padding widths (e.g., `Y=[10, 10]`).
Outputs:
*   `output` (BioImageRef, mem://)

### Pre-processing & Filters
*   `base.normalize_intensity`: Normalize intensities.
*   `base.gaussian`: Gaussian filter.
*   `base.median`: Median filter.
*   `base.bilateral`: Bilateral filter.
*   `base.denoise_nl_means`: Non-local means denoising.
*   `base.unsharp_mask`: Unsharp mask sharpening.
*   `base.equalize_adapthist`: Adaptive histogram equalization (CLAHE).
*   `base.sobel`: Sobel edge detection.
*   `base.threshold_otsu`: Otsu thresholding.
*   `base.threshold_yen`: Yen thresholding.
*   `base.morph_opening`: Morphological opening.
*   `base.morph_closing`: Morphological closing.
*   `base.remove_small_objects`: Remove small connected components.
*   `base.denoise_image`: General denoising tool.

### FLIM Analysis
*   `base.phasor_from_flim`: Compute phasor coordinates (G, S) and intensity from FLIM data.
*   `base.phasor_calibrate`: Calibrate phasor coordinates using a known reference lifetime.

### Legacy Tools (Deprecated)

> ⚠️ **DEPRECATED**: The following legacy tools are deprecated and will be removed in v1.0.0. Use the new `base.xarray.*` or `base.io.bioimage.*` tools instead.

*   `base.convert_to_ome_zarr` -> Use `base.io.bioimage.export(format="OME-Zarr")`
*   `base.export_ome_tiff` -> Use `base.io.bioimage.export(format="OME-TIFF")`
*   `base.project_sum` -> Use `base.xarray.sum`
*   `base.project_max` -> Use `base.xarray.max`
*   `base.crop` -> Use `base.xarray.isel`
*   `base.pad` -> Use `base.xarray.pad`
*   `base.relabel_axes` -> Use `base.xarray.rename`
*   `base.squeeze` -> Use `base.xarray.squeeze`
*   `base.expand_dims` -> Use `base.xarray.expand_dims`
*   `base.moveaxis` -> Use `base.xarray.transpose`
*   `base.swap_axes` -> Use `base.xarray.transpose`

---

## Tools.Cellpose (`bioimage-mcp-cellpose`)

Deep learning-based segmentation using the Cellpose framework.

*   `cellpose.segment`: Segment cells or nuclei.
    *   **Inputs**: `BioImageRef`
    *   **Outputs**: `LabelImageRef` (mask), `cellpose_bundle` (npy)
    *   **Params**: `model_type` (e.g., 'cyto3', 'nuclei'), `diameter`, `channels`, `flow_threshold`, `cellprob_threshold`.

---

## MCP Tool Interface (v0.2.0)

BioImage-MCP exposes 8 MCP tools for LLM interaction:

| Tool | Purpose |
|------|---------|
| `list` | Browse catalog with child counts |
| `describe` | Get full function/node details |
| `search` | Find functions by query/criteria |
| `run` | Execute a function |
| `status` | Poll run status |
| `artifact_info` | Get artifact metadata + preview |
| `session_export` | Export workflow for replay |
| `session_replay` | Replay workflow on new data |

---

## Migration Guide (v0.1.x → v0.2.0)

### Breaking Changes

This release redesigns the MCP tool surface from 13 tools to 8 tools. This breaking change is justified by the **Early Development Policy (Pre-1.0)**, which permits breaking API changes to ensure the final surface is clean and consistent.

### Tool Mapping

| Old Tool | New Tool | Change |
|----------|----------|--------|
| `list_tools` | `list` | Renamed + added child counts |
| `describe_function` | `describe` | Renamed + extended to all node types |
| `describe_tool` | _(removed)_ | Removed (broken/redundant) |
| `search_functions` | `search` | Renamed + added I/O summaries |
| `run_function` | `run` | Renamed + consolidated |
| `run_workflow` | _(removed)_ | Removed (use `run` + sessions) |
| `get_run_status` | `status` | Renamed |
| `get_artifact` | `artifact_info` | Renamed + added text preview |
| `export_artifact` | _(removed)_ | Removed (use URI from artifact_info) |
| `export_session` | `session_export` | Renamed + added external_inputs tracking |
| _(new)_ | `session_replay` | Added workflow replay on new data |
| `activate_functions` | _(removed)_ | Removed |
| `deactivate_functions` | _(removed)_ | Removed |
| `resume_session` | _(merged)_ | Merged into session handling |

### Key Changes

1. **Unified naming**: All tools use short, verb-based names
2. **Child counts**: `list` now returns child counts for navigation decisions
3. **Separated ports/params**: `describe` returns `inputs`, `outputs`, `params_schema` as separate fields
4. **Single execution**: `run` replaces both `run_function` and `run_workflow`
5. **Workflow replay**: New `session_replay` enables re-running workflows on different data
6. **Structured errors**: All tools return JSON Pointer paths with actionable hints

### Removed Tools

The following tools have been removed and should be migrated:

- `describe_tool` → Use `describe` with tool ID
- `run_workflow` → Use `run` in a session, then `session_export` + `session_replay`
- `export_artifact` → Use `artifact_info` to get URI, access file directly
- `activate_functions` / `deactivate_functions` → Removed (unnecessary complexity)
- `resume_session` → Use `session_replay` with workflow reference
