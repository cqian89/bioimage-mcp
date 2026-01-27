---
status: complete
phase: 12-core-engine-ast-first
source: [12-01-SUMMARY.md, 12-02-SUMMARY.md, 12-03-SUMMARY.md, 12-04-SUMMARY.md, 12-05-SUMMARY.md, 12-06-SUMMARY.md, 12-07-SUMMARY.md, 12-08-SUMMARY.md, 12-09-SUMMARY.md]
started: 2026-01-27T16:33:44Z
updated: 2026-01-27T16:49:35Z
---

## Current Test

[testing complete]

## Tests

### 1. Describe Meta Block
expected: Run `bioimage-mcp describe scipy.ndimage.gaussian_filter`. The response includes a `meta` block with at least `tool_version` and `introspection_source`, and `params_schema` does NOT include metadata keys like `tool_version`, `introspection_source`, `callable_fingerprint`, or `module`.
result: issue
reported: "*   Result: FAILED (Incomplete)
*   Issue: The function scipy.ndimage.gaussian_filter was not found in the catalog (ID not found). 
*   Observations: bioimage-mcp doctor reports AST inspection failed for module scipy.ndimage because the module scipy is missing from the tool environment."
severity: major

### 2. Artifact Ports Omitted from params_schema
expected: In the same describe response, `inputs` includes `image` (artifact), but `params_schema.properties` does NOT include `image` or other artifact ports.
result: issue
reported: "*   Result: FAILED (Incomplete)
*   Issue: Dependent on Test 1. Could not retrieve schema for scipy.ndimage.gaussian_filter."
severity: major

### 3. Docstring Parameter Descriptions
expected: In the describe response, `params_schema.properties.sigma.description` (or another known parameter like `order`) contains a non-empty, meaningful description (not blank or generic).
result: issue
reported: "*   Result: FAILED (Incomplete)
*   Issue: Dependent on Test 1. Could not retrieve parameter descriptions."
severity: major

### 4. Required/Properties Consistency
expected: Describe `scipy.ndimage.center_of_mass` (or another function with only artifact inputs). The resulting `params_schema` has no `required` entries for artifact ports; if no non-artifact required params remain, the `required` key is omitted entirely.
result: issue
reported: "*   Result: FAILED (Incomplete)
*   Issue: The function scipy.ndimage.center_of_mass was not found in the catalog (ID not found)."
severity: major

### 5. List/Describe Metadata Alignment
expected: After describing `scipy.ndimage.gaussian_filter`, the MCP `tools/list` response for `path="scipy.ndimage.gaussian_filter"` shows `introspection_source` matching the describe `meta.introspection_source` (synchronized list/describe metadata).
result: issue
reported: "5. List/Describe Metadata Alignment
*   Result: FAILED (Incomplete)
*   Issue: Dependent on Test 1. Function not available for alignment check. "
severity: major

### 6. Doctor Tool Environment Check
expected: Running `bioimage-mcp doctor --json` includes a check for tool environments (e.g., `tool_environments`) with `ok: true` if all envs exist, or a remediation command if any are missing.
result: issue
reported: "*   Running bioimage-mcp doctor --json did include a tool_environments check with ok: true and a count of 4.
    *   However, the environment integrity is compromised: many modules (scipy, skimage, phasorpy) failed AST inspection due to ModuleNotFoundError.
    *   The tool_consolidation check failed with ok: false and invalid_base_manifest.
    *   A validation error was reported for tools/base/scipy_ndimage_blacklist.yaml. "
severity: major

## Summary

total: 6
passed: 0
issues: 6
pending: 0
skipped: 0

## Gaps

- truth: "Describe returns meta block for scipy.ndimage.gaussian_filter and keeps metadata out of params_schema"
  status: failed
  reason: "User reported: *   Result: FAILED (Incomplete)\n*   Issue: The function scipy.ndimage.gaussian_filter was not found in the catalog (ID not found). \n*   Observations: bioimage-mcp doctor reports AST inspection failed for module scipy.ndimage because the module scipy is missing from the tool environment."
  severity: major
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Describe omits artifact ports like image from params_schema"
  status: failed
  reason: "User reported: *   Result: FAILED (Incomplete)\n*   Issue: Dependent on Test 1. Could not retrieve schema for scipy.ndimage.gaussian_filter."
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Describe includes meaningful docstring parameter descriptions"
  status: failed
  reason: "User reported: *   Result: FAILED (Incomplete)\n*   Issue: Dependent on Test 1. Could not retrieve parameter descriptions."
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Describe ensures required list matches emitted properties (artifact omission consistency)"
  status: failed
  reason: "User reported: *   Result: FAILED (Incomplete)\n*   Issue: The function scipy.ndimage.center_of_mass was not found in the catalog (ID not found)."
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Metadata enriched during describe is synchronized back to the function registry and visible in list"
  status: failed
  reason: "User reported: 5. List/Describe Metadata Alignment\n*   Result: FAILED (Incomplete)\n*   Issue: Dependent on Test 1. Function not available for alignment check. "
  severity: major
  test: 5
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Doctor includes tool environment availability checks with remediation"
  status: failed
  reason: "User reported: Environment integrity is compromised (ModuleNotFoundError for scipy/skimage/phasorpy in AST inspection); tool_consolidation failed; validation error for blacklist YAML."
  severity: major
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
