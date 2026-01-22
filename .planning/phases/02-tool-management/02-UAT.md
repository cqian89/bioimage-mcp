---
status: diagnosed
phase: 02-tool-management
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-01-22T14:00:00Z
updated: 2026-01-22T14:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. List Installed Tools
expected: Running `bioimage-mcp list` shows a table of tool packs with name, status, and function count columns.
result: issue
reported: "Shows 'No tools registered' but doctor shows '3 tools, 820 functions'"
severity: major

### 2. List in JSON Format
expected: Running `bioimage-mcp list --json` outputs valid JSON with tool information.
result: issue
reported: "Returns {\"tools\": []} empty array when doctor shows 3 tools exist"
severity: major

### 3. Install Help Shows Options
expected: Running `bioimage-mcp install --help` shows profile options (cpu/gpu/minimal), positional tool arguments, and --force flag.
result: pass

### 4. Install Skips Already-Installed
expected: Running `bioimage-mcp install` on an already-installed environment shows it was skipped (unless --force is used).
result: pass

### 5. Remove Help Shows Options
expected: Running `bioimage-mcp remove --help` shows tool argument and --yes flag for skipping confirmation.
result: pass

### 6. Remove Blocks Base Environment
expected: Running `bioimage-mcp remove base` shows an error that base environment cannot be removed.
result: pass

### 7. Remove Non-Existent Tool
expected: Running `bioimage-mcp remove nonexistent` shows an appropriate error that the tool/environment doesn't exist.
result: pass

## Summary

total: 7
passed: 5
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "List command shows installed tool packs with status and function counts"
  status: failed
  reason: "User reported: Shows 'No tools registered' but doctor shows '3 tools, 820 functions'"
  severity: major
  test: 1
  root_cause: "list.py reads from SQLite database (registry.db) that only populates when server starts, while doctor.py reads manifests directly from disk via load_manifests()"
  artifacts:
    - path: "src/bioimage_mcp/bootstrap/list.py"
      issue: "Lines 39-50 rely exclusively on SQLite database; no fallback to filesystem discovery"
  missing:
    - "Add fallback to load_manifests() when database doesn't exist or is empty"
  debug_session: "ses_41a524066ffeeEPIO5cHO775ma"

- truth: "List --json outputs tool information"
  status: failed
  reason: "User reported: Returns empty array when doctor shows 3 tools exist"
  severity: major
  test: 2
  root_cause: "Same root cause as Test 1 - list.py uses SQLite instead of filesystem"
  artifacts:
    - path: "src/bioimage_mcp/bootstrap/list.py"
      issue: "Both table and JSON output share same data source issue"
  missing:
    - "Fix shared with Test 1"
  debug_session: "ses_41a524066ffeeEPIO5cHO775ma"
