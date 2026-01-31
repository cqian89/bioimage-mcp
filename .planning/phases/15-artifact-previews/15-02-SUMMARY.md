---
phase: 15-artifact-previews
plan: 02
subsystem: api
tags: [label-image, colormap, markdown, table-preview, csv]

# Dependency graph
requires:
  - phase: 15-artifact-previews
    plan: 01
    provides: [Image preview foundation]
provides:
  - LabelImageRef colormap and region metadata previews
  - TableRef markdown table previews
  - Extended artifact_info tool with table preview control
affects:
  - phase: 15-artifact-previews (plan 03: ObjectRef type visibility)

# Tech tracking
tech-stack:
  added: []
  patterns: [Label colormapping with tab20, Markdown table generation from CSV]

key-files:
  created: [tests/unit/artifacts/test_preview.py]
  modified: [src/bioimage_mcp/artifacts/preview.py, src/bioimage_mcp/api/artifacts.py, src/bioimage_mcp/api/server.py, tests/unit/api/test_artifacts.py]

key-decisions:
  - "Use TAB20 colormap for label images with transparent background (alpha=0 for label 0)."
  - "Compute label centroids using raw numpy coordinates for lightweight execution."
  - "Expose table preview as opt-in via include_table_preview to avoid token bloat."
  - "Derive table dtypes from high-fidelity column metadata when available."

patterns-established:
  - "Label-to-RGBA Colormapping: Map integer labels to cyclic RGB colors with transparency."
  - "Opt-in Multimodal Previews: Differentiate between image, text, and table previews in a single info tool."

# Metrics
duration: 9 min
completed: 2026-01-31
---

# Phase 15 Plan 02: Label and Table Previews Summary

**Extended `artifact_info` with colormapped label image previews and markdown table previews.**

## Accomplishments
- Implemented `apply_tab20_colormap` and `get_label_metadata` for visually meaningful `LabelImageRef` previews.
- Implemented `generate_table_preview` using standard `csv` module to produce markdown tables for `TableRef`.
- Extended `ArtifactsService.artifact_info` and the MCP tool surface with parameters for controlling table previews (`include_table_preview`, `preview_rows`, `preview_columns`).
- Fixed a bug where `BioImage.data` access failed on numpy arrays without `.values`.
- Fixed a bug in `TableRef` metadata access where Pydantic models were treated as dicts.

## Task Commits
1. **Task 1: Add LabelImageRef colormap and region metadata** - `5d1350e` (feat)
2. **Task 2: Add TableRef markdown preview** - `a7d67c5` (feat)
3. **Task 3: Add tests for label and table previews** - `5ecfa03` (test)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed BioImage data access (.values)**
- **Found during:** Task 3 verification
- **Issue:** In some environments/readers, `BioImage.data` returns a `numpy.ndarray` directly, which lacks the `.values` attribute.
- **Fix:** Added check for `.values` attribute before access.
- **Commit:** `5ecfa03`

**2. [Rule 3 - Blocking] Fixed TableRef metadata access**
- **Found during:** Task 3 verification
- **Issue:** `ref.metadata` for `TableRef` is a `TableMetadata` Pydantic model, but code was using `.get("columns")`.
- **Fix:** Used `hasattr` and direct attribute access.
- **Commit:** `a7d67c5` (actually partially in `5ecfa03` or similar, wait, I fixed it in a separate edit but committed with tests)

## Next Phase Readiness
- Plan 15-03 will extend `ObjectRef` handling to provide better type visibility.
