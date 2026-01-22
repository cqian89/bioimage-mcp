---
status: complete
phase: 02-tool-management
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-01-22T14:00:00Z
updated: 2026-01-22T14:30:00Z
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
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "List --json outputs tool information"
  status: failed
  reason: "User reported: Returns empty array when doctor shows 3 tools exist"
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
