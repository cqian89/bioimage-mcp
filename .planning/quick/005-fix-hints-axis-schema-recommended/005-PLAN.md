---
phase: quick-005-fix-hints-axis-schema-recommended
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/bioimage_mcp/api/schemas.py
  - src/bioimage_mcp/api/discovery.py
  - tests/contract/test_hints_schema.py
autonomous: true

must_haves:
  truths:
    - "Manifest-defined dimension hints can express OME-Zarr-style axis names (multi-character and/or lowercase, e.g. 'bins', 'y', 'x') without schema rejection."
    - "describe() returns input hint payloads that omit empty/default hint objects (no empty 'hints: {}' blocks)."
    - "Contract tests encode the new 'recommended axis name' schema used by hints."
  artifacts:
    - path: src/bioimage_mcp/api/schemas.py
      provides: "Axis-name type(s) used by FunctionHints/InputRequirement schema"
      contains:
        - "AxisNameRecommended"
        - "InputRequirement.expected_axes uses AxisNameRecommended"
    - path: src/bioimage_mcp/api/discovery.py
      provides: "describe() response shaping for per-input hints"
      contains:
        - "omit empty per-input hints"
    - path: tests/contract/test_hints_schema.py
      provides: "contract coverage for hints schema (expected_axes pattern + examples)"
  key_links:
    - from: src/bioimage_mcp/api/schemas.py
      to: "InputRequirement.model_json_schema()"
      via: "AxisNameRecommended pattern"
      pattern: "AxisNameRecommended"
    - from: src/bioimage_mcp/api/discovery.py
      to: "describe_function() inputs[*].hints"
      via: "post-processing / omission logic"
      pattern: "info\.pop\(\"hints\""
---

<objective>
Make hints axis naming consistent with OME-Zarr (multi-character/lowercase dims) while keeping responses compact by omitting empty hint objects.

Purpose: Prevent manifest hint validation failures and reduce token bloat in describe() outputs.
Output: Updated hints axis schema + tightened describe() hint emission + contract tests.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/bioimage_mcp/api/schemas.py
@src/bioimage_mcp/api/discovery.py
@tests/contract/test_hints_schema.py
@specs/014-native-artifact-types/contracts/artifact-metadata-schema.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Widen hints axis-name schema to the recommended axis identifier pattern</name>
  <files>src/bioimage_mcp/api/schemas.py</files>
  <action>
Update the hints-facing axis-name schema so FunctionHints can represent OME-Zarr-style dimension labels:

- Introduce a new axis name type alias (recommended axis identifier), aligned with the artifact metadata schema dims pattern:
  - Pattern: ^[a-zA-Z][a-zA-Z0-9]*$
- Switch InputRequirement.expected_axes to use this new type instead of the strict single-uppercase AxisName.

Constraints:
- Keep the existing strict single-uppercase AxisName available (do not delete it), since other schema/contracts may still reference it.
- Do not change the artifact metadata schema file in specs/; this task only makes hints consistent with that existing contract.
  </action>
  <verify>pytest -q tests/contract/test_hints_schema.py::test_input_requirement_schema</verify>
  <done>
InputRequirement.model_json_schema() encodes expected_axes items with the recommended axis identifier pattern (not single-uppercase-only).
  </done>
</task>

<task type="auto">
  <name>Task 2: Omit empty/meaningless hints blocks from describe() responses</name>
  <files>src/bioimage_mcp/api/discovery.py</files>
  <action>
Tighten describe() output shaping so hint payloads are only included when they carry meaningful information:

- Per-input hints:
  - If the computed hints payload is None OR an empty dict, do not include the 'hints' key for that input.
  - When post-processing existing input dicts, treat both None and {} as "absent" and remove the key.

- Top-level function hints (success/error):
  - Only include success_hints if it contains at least one non-empty field (e.g., non-empty next_steps or common_issues).
  - Only include error_hints if the dict is non-empty.
  - If both are empty after filtering, omit the top-level 'hints' key entirely.

Constraints:
- Preserve existing behavior for non-empty hints; this is only about omission of empty/meaningless blocks.
- Keep all changes local to src/bioimage_mcp/api/discovery.py.
  </action>
  <verify>pytest -q tests/contract/test_describe.py::test_describe_function_sanitizes_text_and_hints</verify>
  <done>
describe() never returns 'hints: {}' (top-level or per-input); 'hints' is present only when it contains meaningful content.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update and extend contract tests for the new hints axis schema</name>
  <files>tests/contract/test_hints_schema.py</files>
  <action>
Update contract expectations and add a focused regression for multi-character axis names:

- Update test_input_requirement_schema() to assert the new expected_axes item pattern (recommended axis identifier).
- Add a new small test that validates InputRequirement accepts a manifest-like expected_axes list with multi-character and lowercase entries (e.g., ['bins', 'y', 'x']).

Constraints:
- Keep the contract tests narrowly scoped to schema/validation behavior; do not require tool env installs.
  </action>
  <verify>pytest -q tests/contract/test_hints_schema.py</verify>
  <done>
Contract tests pass and explicitly cover multi-character/lowercase expected_axes values.
  </done>
</task>

</tasks>

<verification>
- Contract: `pytest -q tests/contract/test_hints_schema.py` passes.
- Contract: `pytest -q tests/contract/test_describe.py::test_describe_function_sanitizes_text_and_hints` passes.
</verification>

<success_criteria>
- Tool manifests can declare hint expected_axes like ['bins','y','x'] without failing schema validation.
- describe() payloads do not contain empty hint objects (no empty 'hints' blocks).
</success_criteria>

<output>
After completion, create `.planning/quick/005-fix-hints-axis-schema-recommended/005-SUMMARY.md`
</output>
