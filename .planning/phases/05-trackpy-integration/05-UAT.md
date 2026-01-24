---
status: diagnosed
phase: 05-trackpy-integration
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md, 05-05-SUMMARY.md, 05-06-SUMMARY.md]
started: 2026-01-24T00:00:00Z
updated: 2026-01-24T00:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Install Trackpy
expected: Run `bioimage-mcp install trackpy`. Should complete successfully (or report "already installed") without errors.
result: pass

### 2. List Tools
expected: Run `bioimage-mcp list`. Should show 'trackpy' in the table with ~130 functions and status 'installed'.
result: pass

### 3. Doctor Check
expected: Run `bioimage-mcp doctor`. Should report 'trackpy' environment as 'ok' (all checks passed).
result: issue
reported: "Registry reports 4 tools and 964 functions.shows \"not ready\". A warning about conda-lock was noted, but no errors were reported for the trackpy environment itself."
severity: major

### 4. Describe Function
expected: Run `bioimage-mcp describe trackpy.locate`. Should return a JSON schema with parameters (image, diameter, etc.).
result: issue
reported: "JSON Response showed params_schema with empty properties, despite diameter being a known parameter. Inputs correctly showed image."
severity: major

### 5. Run Analysis (Locate)
expected: |
  Run `bioimage-mcp run trackpy.locate` with sample data:
  `bioimage-mcp run trackpy.locate --inputs '{"image": "datasets/trackpy-examples/bulk_water/frame000_green.ome.tiff", "diameter": 11}'`
  Should return a Table artifact (Ref) containing particle coordinates.
result: pass

## Summary

total: 5
passed: 3
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Run `bioimage-mcp doctor`. Should report 'trackpy' environment as 'ok' (all checks passed)."
  status: failed
  reason: "User reported: Registry reports 4 tools and 964 functions.shows \"not ready\". A warning about conda-lock was noted, but no errors were reported for the trackpy environment itself."
  severity: major
  test: 3
  root_cause: "Doctor readiness is computed as all checks ok; check_conda_lock returns ok=False when the conda-lock executable is missing, so the missing conda-lock alone yields NOT READY."
  artifacts:
    - path: "src/bioimage_mcp/bootstrap/checks.py"
      issue: "check_conda_lock uses shutil.which('conda-lock') and returns ok=False with remediation when missing; run_all_checks includes this check."
    - path: "src/bioimage_mcp/bootstrap/doctor.py"
      issue: "doctor sets ready = all(r.ok for r in results) and prints NOT READY plus remediation for each failing check."
  missing:
    - "Install conda-lock in the environment."
  debug_session: ".planning/debug/doctor-not-ready.md"

- truth: "Run `bioimage-mcp describe trackpy.locate`. Should return a JSON schema with parameters (image, diameter, etc.)."
  status: failed
  reason: "User reported: JSON Response showed params_schema with empty properties, despite diameter being a known parameter. Inputs correctly showed image."
  severity: major
  test: 4
  root_cause: "Trackpy's entrypoint only handles requests with command=execute; describe_function sends a legacy meta.describe request without a command field, so the entrypoint returns an Unknown command error and discovery falls back to the manifest schema (which has empty properties from meta.list)."
  artifacts:
    - path: "src/bioimage_mcp/api/discovery.py"
      issue: "meta.describe request is sent without a command field, so tools expecting command=execute treat it as unknown."
    - path: "tools/trackpy/bioimage_mcp_trackpy/entrypoint.py"
      issue: "Legacy requests without command are passed to _handle_request, which only accepts command=execute or shutdown and otherwise returns Unknown command."
  missing:
    - "Legacy request handling in trackpy entrypoint should accept meta.describe payloads without a command field."
  debug_session: ".planning/debug/trackpy-schema-empty.md"
