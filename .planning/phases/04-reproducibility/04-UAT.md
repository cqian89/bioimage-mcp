---
status: testing
phase: 04-reproducibility
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md]
started: 2026-01-22T19:30:00Z
updated: 2026-01-22T19:30:00Z
---

## Current Test

number: 2
name: Version Mismatch Warning
expected: |
  When replaying a session where tool versions have changed (different lock_hash),
  the response includes version mismatch warnings while still allowing replay to proceed.
awaiting: user response

## Tests

### 1. Override Validation
expected: When replaying a session with invalid parameter overrides, the API returns validation_failed status with error details before execution starts.
result: issue
reported: "Got ENVIRONMENT_MISSING error instead of override validation error. System checked environment first (base not installed) and never reached parameter validation for the invalid 'format: INVALID_FORMAT' override."
severity: major

### 2. Version Mismatch Warning
expected: When replaying a session where tool versions have changed (different lock_hash), the response includes version mismatch warnings while still allowing replay to proceed.
result: [pending]

### 3. Missing Environment Detection
expected: When attempting replay without the required Conda environment installed, response shows environment_missing status and includes install_offers with the command to install (e.g., "bioimage-mcp install <env>").
result: [pending]

### 4. Step Progress Reporting
expected: Replay response includes step_progress list showing each step's status (pending/running/completed/failed), timing (started_at/ended_at), and descriptive messages.
result: [pending]

### 5. Dry-run Mode
expected: Calling session_replay with dry_run=true validates overrides and inputs, returns status=ready with pending step_progress entries, but does NOT execute any tools.
result: [pending]

### 6. Resume from Failure
expected: When a previous replay failed mid-workflow, providing resume_session_id allows continuing from the last successful step, skipping already-completed steps.
result: [pending]

### 7. Missing Input Hints
expected: When required external inputs are missing during replay, the error includes structured hints with JSON Pointers (e.g., "/inputs/image") identifying what's missing.
result: [pending]

### 8. Human-readable Error Summary
expected: Failed replays include a human_summary field with a formatted, actionable description of what went wrong and how to fix it.
result: [pending]

## Summary

total: 8
passed: 0
issues: 1
pending: 7
skipped: 0

## Gaps

- truth: "When replaying with invalid parameter overrides, API returns validation_failed with override-specific error messages before execution"
  status: failed
  reason: "User reported: Got ENVIRONMENT_MISSING error instead of override validation error. System checked environment first (base not installed) and never reached parameter validation for the invalid 'format: INVALID_FORMAT' override."
  severity: major
  test: 1
  artifacts: []
  missing: []
