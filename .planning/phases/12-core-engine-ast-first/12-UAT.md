---
status: complete
phase: 12-core-engine-ast-first
source: [12-01-SUMMARY.md, 12-02-SUMMARY.md, 12-03-SUMMARY.md, 12-04-SUMMARY.md, 12-05-SUMMARY.md, 12-06-SUMMARY.md, 12-07-SUMMARY.md, 12-08-SUMMARY.md, 12-09-SUMMARY.md]
started: 2026-01-27T16:33:44Z
updated: 2026-01-27T18:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Describe Meta Block
expected: Run `bioimage-mcp describe scipy.ndimage.gaussian_filter`. The response includes a `meta` block with at least `tool_version` and `introspection_source`, and `params_schema` does NOT include metadata keys like `tool_version`, `introspection_source`, `callable_fingerprint`, or `module`.
result: pass

### 2. Artifact Ports Omitted from params_schema
expected: In the same describe response, `inputs` includes `image` (artifact), but `params_schema.properties` does NOT include `image` or other artifact ports.
result: pass

### 3. Docstring Parameter Descriptions
expected: In the describe response, `params_schema.properties.sigma.description` (or another known parameter like `order`) contains a non-empty, meaningful description (not blank or generic).
result: pass

### 4. Required/Properties Consistency
expected: Describe `scipy.ndimage.center_of_mass` (or another function with only artifact inputs). The resulting `params_schema` has no `required` entries for artifact ports; if no non-artifact required params remain, the `required` key is omitted entirely.
result: pass

### 5. List/Describe Metadata Alignment
expected: After describing `scipy.ndimage.gaussian_filter`, the MCP `tools/list` response for `path="scipy.ndimage.gaussian_filter"` shows `introspection_source` matching the describe `meta.introspection_source` (synchronized list/describe metadata).
result: pass

### 6. Doctor Tool Environment Check
expected: Running `bioimage-mcp doctor --json` includes a check for tool environments (e.g., `tool_environments`) with `ok: true` if all envs exist, or a remediation command if any are missing.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
