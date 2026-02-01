---
phase: quick-006-enable-image-previews-for-plotref-in-art
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/bioimage_mcp/artifacts/preview.py
  - src/bioimage_mcp/api/artifacts.py
  - tests/unit/api/test_artifacts.py
autonomous: true

must_haves:
  truths:
    - "artifact_info(include_image_preview=true) returns image_preview for PlotRef"
    - "PlotRef image_preview width/height are capped by image_preview_size"
    - "Preview generation failures do not fail artifact_info (image_preview omitted)"
  artifacts:
    - path: src/bioimage_mcp/artifacts/preview.py
      provides: "PlotRef preview generation (resize-to-max, base64)"
    - path: src/bioimage_mcp/api/artifacts.py
      provides: "artifact_info wiring for PlotRef -> image_preview"
    - path: tests/unit/api/test_artifacts.py
      provides: "Unit coverage for PlotRef image_preview"
  key_links:
    - from: src/bioimage_mcp/api/artifacts.py
      to: src/bioimage_mcp/artifacts/preview.py
      via: "generate_plot_preview(...) call"
      pattern: "generate_plot_preview"
---

<objective>
Enable image previews for PlotRef in artifact_info, using the same image_preview mechanism as BioImageRef/LabelImageRef, but with no projections and only a max-dimension cap via image_preview_size.

Purpose: Plot artifacts should be visually inspectable through artifact_info without requiring clients to fetch and render the full image.
Output: PlotRef responses include image_preview (base64 + format + width/height) when requested.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/bioimage_mcp/api/artifacts.py
@src/bioimage_mcp/artifacts/preview.py
@src/bioimage_mcp/artifacts/models.py
@tests/unit/api/test_artifacts.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add PlotRef preview generator (resize + base64)</name>
  <files>src/bioimage_mcp/artifacts/preview.py</files>
  <action>
Create a PlotRef-focused preview helper that does NOT use BioIO/projection and only enforces image_preview_size:

- Add `generate_plot_preview(path: Path, *, max_size: int = 256, width_px: int | None = None, height_px: int | None = None) -> dict | None`.
- For raster plots (PNG/JPG): open via Pillow, convert to RGBA or RGB as needed, downscale only when max(width,height) > max_size (preserve aspect), then encode preview as PNG base64.
- For SVG plots: do NOT rasterize; base64-encode the SVG bytes and set preview `format` to `svg`. Compute preview `width`/`height` from (a) width_px/height_px params if provided, else (b) parse root `<svg>` width/height/viewBox if trivial; then cap reported width/height to max_size while preserving aspect.
- Match existing preview behavior: return `None` on any exception (fail-silent).
- Keep return shape aligned with existing image_preview contract: include `base64`, `format`, `width`, `height`.
  </action>
  <verify>python -c "from bioimage_mcp.artifacts.preview import generate_plot_preview; import inspect; print('generate_plot_preview' in inspect.getsource(generate_plot_preview))"</verify>
  <done>
`generate_plot_preview` exists, returns preview dict for a valid PNG, and returns None when it cannot generate a preview.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire PlotRef -> image_preview in artifact_info</name>
  <files>src/bioimage_mcp/api/artifacts.py</files>
  <action>
Extend `ArtifactsService.artifact_info(...)` to support PlotRef previews:

- Import and call `generate_plot_preview` when `ref.type == "PlotRef"` and `include_image_preview` is true.
- Resolve local filesystem path from `ref.uri` similarly to existing image preview logic (handle `file://...`; for `mem://...` use `_simulated_path` if present).
- Pass `max_size=image_preview_size`.
- Pass plot dimensions from PlotRef metadata when available (e.g. `ref.metadata.width_px`, `ref.metadata.height_px`) to improve SVG width/height reporting.
- On success set `response["image_preview"] = preview`; on any failure omit the field (do not raise).
- Do NOT apply projection/slice/channel logic for PlotRef.
  </action>
  <verify>python -c "from bioimage_mcp.api.artifacts import ArtifactsService; import inspect; s=inspect.getsource(ArtifactsService.artifact_info); assert 'PlotRef' in s and 'image_preview' in s"</verify>
  <done>
Calling `artifact_info(..., include_image_preview=True)` on a PlotRef returns `image_preview` when the referenced file is readable.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add unit test covering PlotRef preview and size cap</name>
  <files>tests/unit/api/test_artifacts.py</files>
  <action>
Add a new unit test that validates PlotRef previews behave like other image previews:

- Create a temporary PNG using Pillow (e.g. 500x300) and import it as a PlotRef via `ArtifactStore.import_file(...)`.
- Provide PlotRef-required metadata via `metadata_override` (must include at least `width_px` and `height_px`; include `dpi` if needed).
- Call `ArtifactsService.artifact_info(ref.ref_id, include_image_preview=True, image_preview_size=128)`.
- Assert `image_preview` exists, decodes as a valid PNG, and `max(img.size) <= 128`.
- Keep the test independent from matplotlib and tool-pack execution (pure Pillow + ArtifactStore).
  </action>
  <verify>pytest tests/unit/api/test_artifacts.py -k "plot"</verify>
  <done>
Unit tests prove PlotRef preview generation works and respects `image_preview_size`.
  </done>
</task>

</tasks>

<verification>
- `pytest tests/unit/api/test_artifacts.py -k "plot"`
</verification>

<success_criteria>
- PlotRef artifacts returned by `artifact_info` include `image_preview` when requested and the underlying file is readable.
- Preview dimensions are capped by `image_preview_size` (reported width/height for SVG, actual resized pixels for raster).
- Preview failures are non-fatal and only omit the `image_preview` field.
</success_criteria>

<output>
After completion, create `.planning/quick/006-enable-image-previews-for-plotref-in-art/006-SUMMARY.md`
</output>
