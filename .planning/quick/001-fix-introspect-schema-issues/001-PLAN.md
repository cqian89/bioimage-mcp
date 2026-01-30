---
phase: quick-001-fix-introspect-schema-issues
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/bioimage_mcp/runtimes/introspect.py
  - tests/unit/runtimes/test_introspect.py
autonomous: true

must_haves:
  truths:
    - "When meta.describe falls back to name-pattern type inference, any parameter containing 'axis' is emitted as JSON Schema type 'integer' (not 'string')."
    - "Parameters named 'label_image' and 'intensity_image' are treated as artifact ports and are omitted from params_schema properties/required to prevent runtime argument binding errors."
  artifacts:
    - path: src/bioimage_mcp/runtimes/introspect.py
      provides: "Pattern-based JSON Schema inference + artifact-port omission"
      contains:
        - "PARAM_TYPE_PATTERNS['axis'] = 'integer'"
        - "ARTIFACT_PORTS includes 'label_image' and 'intensity_image'"
    - path: tests/unit/runtimes/test_introspect.py
      provides: "Regression tests for axis inference + regionprops artifact ports"
      contains:
        - "fallback infers axis as integer"
        - "label_image/intensity_image omitted from schema"
  key_links:
    - from: src/bioimage_mcp/runtimes/introspect.py
      to: schema_from_descriptions
      via: "PARAM_TYPE_PATTERNS mapping"
      pattern: "PARAM_TYPE_PATTERNS.*axis.*integer"
    - from: src/bioimage_mcp/runtimes/introspect.py
      to: is_artifact_param
      via: "ARTIFACT_PORTS membership check"
      pattern: "name\\.lower\\(\\) in ARTIFACT_PORTS"
---

<objective>
Fix dynamic introspection schema bugs causing contract/runtime failures: emit integer axis indices (ndarray-friendly) and omit regionprops artifact inputs from params_schema.

Purpose: Keep meta.describe schemas executable and consistent with numpy-backed runtime images.
Output: Updated introspection rules + regression tests covering the two reported failures.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/bioimage_mcp/runtimes/introspect.py
@tests/unit/runtimes/test_introspect.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix axis inference + expand artifact port omit list</name>
  <files>src/bioimage_mcp/runtimes/introspect.py</files>
  <action>
  - Update PARAM_TYPE_PATTERNS so the "axis" pattern maps to JSON Schema type "integer".
  - Update the inline comment to reflect reality: runtime image arrays are numpy ndarrays (integer axis indices only); string axis labels (e.g. "Z") are DataArray/xarray-specific and not supported here.
  - Add "label_image" and "intensity_image" to ARTIFACT_PORTS so is_artifact_param omits them from params_schema and required.
  - Keep behavior deterministic; do not change unrelated patterns or omission heuristics.
  </action>
  <verify>python -m compileall src/bioimage_mcp/runtimes/introspect.py</verify>
  <done>
  - PARAM_TYPE_PATTERNS["axis"] is "integer".
  - ARTIFACT_PORTS contains "label_image" and "intensity_image".
  </done>
</task>

<task type="auto">
  <name>Task 2: Add regression tests for axis inference + regionprops ports</name>
  <files>tests/unit/runtimes/test_introspect.py</files>
  <action>
  - Add a unit test that exercises the schema_from_descriptions fallback path (via introspect_python_api returning no properties) and asserts that a described parameter named "axis" emits JSON Schema type "integer".
    - Construct a function where all real signature params are omitted as artifacts (e.g. only "image") so fallback is used.
  - Add a unit test asserting that parameters named "label_image" and "intensity_image" are omitted from properties and from required when introspecting a signature.
    - Include at least one non-artifact parameter to confirm schema still emits normal properties.
  </action>
  <verify>pytest tests/unit/runtimes/test_introspect.py</verify>
  <done>
  - Both new tests pass and would fail on the pre-fix behavior.
  </done>
</task>

</tasks>

<verification>
- Unit regression: `pytest tests/unit/runtimes/test_introspect.py`
</verification>

<success_criteria>
- Axis-inferred params_schema emits integer axis indices.
- Regionprops-style inputs `label_image`/`intensity_image` do not appear in params_schema required/properties, preventing "multiple values for argument" binding errors.
</success_criteria>

<output>
After completion, create `.planning/quick/001-fix-introspect-schema-issues/001-SUMMARY.md`
</output>
