---
phase: quick
plan: 008
type: execute
wave: 1
depends_on: []
files_modified:
  - src/bioimage_mcp/bootstrap/list.py
  - tests/unit/bootstrap/test_list_output.py
autonomous: true

must_haves:
  truths:
    - "Running `bioimage-mcp list` never expands to per-function rows; the tree only shows tool rows and package rows."
    - "Functions whose IDs do not include a '.' are grouped under a single fallback package (not treated as separate packages)."
  artifacts:
    - path: "src/bioimage_mcp/bootstrap/list.py"
      provides: "CLI list grouping logic that computes tool package rows"
    - path: "tests/unit/bootstrap/test_list_output.py"
      provides: "Regression coverage for package grouping behavior"
  key_links:
    - from: "src/bioimage_mcp/bootstrap/list.py"
      to: "packages output in list_tools() payload"
      via: "pkg_counts grouping"
      pattern: "pkg_counts"
---

<objective>
Ensure `bioimage-mcp list` output is stable and only lists packages (never per-function rows), even when function IDs are not dot-namespaced.

Purpose: Prevent noisy/incorrect CLI output that varies by environment or tool-pack naming conventions.
Output: Updated package-grouping logic + regression test.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/bioimage_mcp/bootstrap/list.py
@tests/unit/bootstrap/test_list_output.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add regression test for non-namespaced function IDs</name>
  <files>tests/unit/bootstrap/test_list_output.py</files>
  <action>
Add a unit test that constructs a manifest with multiple functions whose `id` values have no '.' (e.g. `"alpha"`, `"beta"`).

Test expectations:
- JSON output (`list_tools(json_output=True)`) has exactly 1 package entry for those functions (a single fallback package ID), with `function_count == 2`.
- Table output (`list_tools(json_output=False)`) renders only one package row for the fallback package (not one row per function).

Keep the test self-contained using the existing tmp manifest patterns in this file.
  </action>
  <verify>pytest tests/unit/bootstrap/test_list_output.py -q</verify>
  <done>
New test fails on current behavior when function IDs without '.' would otherwise appear as separate package rows.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix package inference so list output never degrades to function-level</name>
  <files>src/bioimage_mcp/bootstrap/list.py</files>
  <action>
Update the package grouping logic in `list_tools()` to compute package IDs defensively:
- Prefer the first segment after stripping the tool prefix (`{tool_id}.`) when present.
- If the remaining function identifier has no '.', assign it to a single stable fallback package ID (e.g. `"misc"` or `"root"`).
- Ensure this fallback is used consistently for both the table output and the JSON payload (since both derive from the same `packages` list).

Do not change JSON schema shape; only change how `packages[].id` is derived.
  </action>
  <verify>pytest tests/unit/bootstrap/test_list_output.py -q</verify>
  <done>
All list-related unit tests pass, and the new regression test confirms non-namespaced function IDs are grouped under one fallback package.
  </done>
</task>

</tasks>

<verification>
- Unit: `pytest tests/unit/bootstrap/test_list_output.py -q`
- Smoke (optional): `python -m bioimage_mcp.cli list --json | python -m json.tool` shows `packages` per tool and no per-function rows.
</verification>

<success_criteria>
- `bioimage-mcp list` output is consistent across environments and never lists individual functions as package rows.
</success_criteria>

<output>
After completion, create `.planning/quick/008-the-cli-command-bioimage-mcp-list-shows-/008-SUMMARY.md`
</output>
