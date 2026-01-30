---
phase: quick-003-fix-tool-schema-validation-issues
plan: 003
type: execute
wave: 1
depends_on: []
files_modified:
  - src/bioimage_mcp/registry/dynamic/models.py
  - src/bioimage_mcp/registry/engine.py
  - src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py
  - src/bioimage_mcp/registry/dynamic/adapters/skimage.py
  - tools/base/manifest.yaml
  - tools/base/bioimage_mcp_base/io.py
  - tests/contract/test_skimage_adapter.py
  - tests/integration/test_flim_calibration.py
  - tests/unit/api/test_io_functions.py
autonomous: true

must_haves:
  truths:
    - "Describing and running base.phasorpy.lifetime.phasor_to_apparent_lifetime agree on the output port names and count"
    - "Describing base.skimage.measure.regionprops and base.skimage.measure.regionprops_table does not require label_image in params_schema"
    - "base.io.bioimage.export accepts dest_path (not path) and the output artifact path matches the chosen destination"
  artifacts:
    - path: "src/bioimage_mcp/registry/engine.py"
      provides: "IOPattern -> (inputs, outputs) port mapping used by describe"
    - path: "src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py"
      provides: "phasorpy execute() output naming for multi-output functions"
    - path: "src/bioimage_mcp/registry/dynamic/adapters/skimage.py"
      provides: "skimage dynamic introspection filtering of artifact-only parameters"
    - path: "tools/base/manifest.yaml"
      provides: "base.io.bioimage.export params_schema contract"
    - path: "tools/base/bioimage_mcp_base/io.py"
      provides: "base.io.bioimage.export runtime implementation"
  key_links:
    - from: "src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py"
      to: "src/bioimage_mcp/registry/engine.py"
      via: "IOPattern selection -> describe ports must match execute output_name values"
      pattern: "PHASOR_TO_SCALAR|phasor_to_apparent_lifetime"
    - from: "src/bioimage_mcp/registry/dynamic/adapters/skimage.py"
      to: "src/bioimage_mcp/registry/dynamic/introspection.py"
      via: "dynamic introspection -> params_schema emission"
      pattern: "label_image|intensity_image"
    - from: "tools/base/manifest.yaml"
      to: "tools/base/bioimage_mcp_base/io.py"
      via: "manifest params_schema property name must match params read by implementation"
      pattern: "base\.io\.bioimage\.export.*dest_path"
---

<objective>
Fix three schema-validation regressions by aligning tool describe schemas with runtime behavior:
1) PhasorPy apparent lifetime outputs, 2) skimage regionprops artifact params omission, 3) export param standardization to dest_path.

Purpose: Keep unified introspection deterministic and schema-valid across list/describe/run.
Output: Updated adapters + engine port mapping + base manifest/runtime + targeted regression tests.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

@src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py
@src/bioimage_mcp/registry/dynamic/adapters/skimage.py
@src/bioimage_mcp/registry/engine.py
@tools/base/manifest.yaml
@tools/base/bioimage_mcp_base/io.py

@tests/integration/test_flim_calibration.py
@tests/contract/test_skimage_adapter.py
@tests/unit/api/test_io_functions.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Make phasor_to_apparent_lifetime schema and runtime outputs match</name>
  <files>
src/bioimage_mcp/registry/dynamic/models.py
src/bioimage_mcp/registry/engine.py
src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py
tests/integration/test_flim_calibration.py
  </files>
  <action>
1) Stop treating phasor_to_apparent_lifetime as a generic "phasor -> scalar" single-output tool.

2) Add a dedicated I/O pattern for this function (keep it explicit to avoid impacting other PHASOR_TO_SCALAR functions):
   - Add a new enum member in `src/bioimage_mcp/registry/dynamic/models.py` (e.g. `PHASOR_TO_LIFETIMES`).
   - In `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py`, return this new pattern ONLY when `func_name == "phasor_to_apparent_lifetime"`.
   - In `src/bioimage_mcp/registry/engine.py`, map the new pattern to:
     inputs: `real`, `imag` (BioImageRef)
     outputs: `phase_lifetime`, `modulation_lifetime` (BioImageRef)

3) Align runtime output naming in `src/bioimage_mcp/registry/dynamic/adapters/phasorpy.py`:
   - When executing `phasor_to_apparent_lifetime` and `result` is a 2-tuple of ndarrays, save them with output_name EXACTLY matching the describe ports: `phase_lifetime` and `modulation_lifetime`.
   - Ensure the generic heuristic `elif "phasor" in func_name and len(result) == 2` does NOT rename these to `real`/`imag`.
   - Keep existing behavior for `phasor_from_signal` (mean/real/imag) unchanged.

4) Add/adjust a regression assertion in `tests/integration/test_flim_calibration.py` (or the most local existing phasor integration test) that:
   - describe for `base.phasorpy.lifetime.phasor_to_apparent_lifetime` exposes two outputs with the chosen names
   - run returns two outputs whose metadata/output_name match those names (no `real`/`imag` naming for this function)

Avoid broad changes to PHASOR_TO_SCALAR; keep blast radius limited to this one function.
  </action>
  <verify>
pytest -q tests/integration/test_flim_calibration.py
  </verify>
  <done>
- The tool schema (describe) declares two outputs for apparent lifetime.
- The runtime (run) returns two outputs whose output_name values match the schema.
  </done>
</task>

<task type="auto">
  <name>Task 2: Ensure regionprops artifact inputs never appear as params_schema properties or required</name>
  <files>
src/bioimage_mcp/registry/dynamic/adapters/skimage.py
tests/contract/test_skimage_adapter.py
  </files>
  <action>
1) Reproduce the failure in-process (no live server required): discover `regionprops_table` and the redirected `regionprops` via `SkimageAdapter().discover(...)`.

2) Fix the adapter/introspection pipeline so that `label_image` and `intensity_image` are:
   - NOT present in the emitted `params_schema.properties`
   - NOT present in `params_schema.required`

Implementation guidance:
   - The adapter already filters `meta.parameters` by `ARTIFACT_INPUT_PARAMS`. If the tool schema still shows `label_image` as required, the required list is being derived from an unfiltered source.
   - Adjust the skimage adapter so filtering happens at the correct stage for schema generation (e.g., ensure the introspected metadata used to generate JSON schema cannot retain required-ness for omitted keys).
   - Keep `execute()` multi-input behavior intact (regionprops_table still accepts labels + intensity_image as artifact inputs).

3) Add a contract test in `tests/contract/test_skimage_adapter.py` that asserts BOTH:
   - `discover()` metadata for `regionprops_table` does not include these names in `metadata.parameters`
   - the redirected `regionprops` metadata also omits them

This is a schema-contract fix: do not reintroduce these values as ordinary params.
  </action>
  <verify>
pytest -q tests/contract/test_skimage_adapter.py
  </verify>
  <done>
- label_image/intensity_image are omitted from params_schema properties and required for regionprops/regionprops_table.
- regionprops_table execution continues to accept those values as artifact inputs.
  </done>
</task>

<task type="auto">
  <name>Task 3: Standardize base.io.bioimage.export to dest_path and make runtime respect it</name>
  <files>
tools/base/manifest.yaml
tools/base/bioimage_mcp_base/io.py
tests/unit/api/test_io_functions.py
  </files>
  <action>
1) Update `tools/base/manifest.yaml` so `base.io.bioimage.export` uses `dest_path` (not `path`) in `params_schema.properties`.
   - Keep it optional (do NOT add it to required).
   - Update the property description to specify absolute path (file for OME-TIFF/PNG/NPY; directory for OME-Zarr).

2) Update `tools/base/bioimage_mcp_base/io.py` to actually honor the destination parameter:
   - Read `dest_path = params.get("dest_path")`.
   - Backward compatibility: if `dest_path` is missing, fall back to the legacy key `params.get("path")`.
   - If a destination is provided, write the export to that path instead of always using `work_dir/export.*`.
   - Ensure the returned artifact `path` matches the actual output location.

3) Add/adjust a unit test in `tests/unit/api/test_io_functions.py` asserting:
   - Passing `dest_path` changes the output artifact path.
   - Legacy `path` still works (optional), but schema now advertises only `dest_path`.

Keep the rest of the export behavior (format selection, OME-Zarr directory creation) unchanged.
  </action>
  <verify>
pytest -q tests/unit/api/test_io_functions.py -k "export"
  </verify>
  <done>
- base.io.bioimage.export schema uses dest_path.
- Export writes to the requested destination and returns an artifact pointing at it.
  </done>
</task>

</tasks>

<verification>
- ruff check .
- ruff format --check .
- pytest -q tests/contract/test_skimage_adapter.py tests/unit/api/test_io_functions.py tests/integration/test_flim_calibration.py
</verification>

<success_criteria>
- No schema validation errors for the three reported issues (describe/run alignment and params_schema correctness).
- All targeted tests and lint/format checks pass.
</success_criteria>

<output>
After completion, create `.planning/quick/003-fix-tool-schema-validation-issues/003-SUMMARY.md`
</output>
