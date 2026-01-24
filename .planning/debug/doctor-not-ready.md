---
status: diagnosed
trigger: "Diagnose why `bioimage-mcp doctor` reports \"not ready\" despite successful tool registration."
created: 2026-01-24T12:37:12+01:00
updated: 2026-01-24T14:16:31+01:00
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: readiness check fails because conda-lock dependency missing
test: confirm check_conda_lock is in run_all_checks
expecting: run_all_checks includes check_conda_lock so missing binary triggers NOT READY
next_action: record root cause and report diagnosis

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: "Doctor reports READY after successful tool installation"
actual: "Doctor reports NOT READY and lists missing conda-lock requirement"
errors: "NOT READY\nRegistry: 4 tools, 964 functions; 0 invalid manifests\n- conda_lock:\n  - Install conda-lock>=4.0.0 (used for reproducible env locks)"
reproduction: "Run `bioimage-mcp doctor` in Phase 05 integration environment"
started: "Reported during Phase 05 integration (exact start unknown)"

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-24T14:12:06+01:00
  checked: src/bioimage_mcp/bootstrap/checks.py
  found: check_conda_lock uses shutil.which("conda-lock") and returns ok=False with remediation if missing
  implication: readiness can fail solely due to missing conda-lock executable

- timestamp: 2026-01-24T14:12:06+01:00
  checked: tests/unit/bootstrap/test_checks.py
  found: test_check_conda_lock_missing_fails asserts ok=False when conda-lock missing
  implication: conda-lock absence is treated as a failing readiness check

- timestamp: 2026-01-24T14:14:18+01:00
  checked: src/bioimage_mcp/bootstrap/doctor.py
  found: doctor sets ready = all(r.ok for r in results) and prints remediation for each failing check
  implication: any failing check (including conda_lock) causes NOT READY output

- timestamp: 2026-01-24T14:16:31+01:00
  checked: src/bioimage_mcp/bootstrap/checks.py
  found: run_all_checks includes check_conda_lock in readiness checklist
  implication: conda-lock presence is a required readiness gate

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "Doctor readiness is computed as all checks ok; check_conda_lock fails when conda-lock executable missing."
fix: ""
verification: ""
files_changed: []
