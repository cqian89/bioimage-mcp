# Quick Task 006: Enable Image Previews for PlotRef in artifact_info

## Summary

Added image preview support for PlotRef artifacts in `artifact_info()`, following the same pattern as BioimageRef and LabelimageRef but without projection/scaling—just max-size capping.

## Changes Made

### Task 1: Add PlotRef preview generator
**File:** `src/bioimage_mcp/artifacts/preview.py`
- Added `generate_plot_preview(path, max_size, width_px, height_px)` function
- For raster (PNG/JPG): resize to fit `max_size` maintaining aspect ratio, encode as base64 PNG
- For SVG: base64-encode raw bytes, parse dimensions from width/height attributes or viewBox, cap reported dimensions to `max_size`
- Fail-silent: returns `None` on any exception

### Task 2: Wire PlotRef → image_preview in artifact_info
**File:** `src/bioimage_mcp/api/artifacts.py`
- Added PlotRef-specific branch in `artifact_info()` 
- Exposes `width_px`, `height_px`, `dpi` from PlotRef metadata
- Calls `generate_plot_preview()` when `include_image_preview=True`
- Handles both `file://` and `mem://` URI schemes

### Task 3: Add unit test
**File:** `tests/unit/api/test_artifacts.py`
- Added `test_artifact_info_plot_image_preview()` 
- Creates 500x300 PNG, imports as PlotRef
- Verifies `image_preview` exists and respects `image_preview_size=128`

## Verification

```bash
pytest tests/unit/api/test_artifacts.py -k "plot" -v
# 1 passed
```

## Decisions

| Decision | Rationale |
|----------|-----------|
| SVG served as raw base64 | No rasterization needed; browsers handle natively |
| Parse SVG dimensions from width/height/viewBox | Best-effort dimension extraction for capping |
| Default to 100x100 for unparseable SVG | Safe fallback when dimensions can't be determined |
