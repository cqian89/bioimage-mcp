---
status: diagnosed
phase: 05-trackpy-integration
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md]
started: 2026-01-23T19:22:48Z
updated: 2026-01-23T20:12:02Z
---

## Current Test

[testing complete]

## Tests

### 1. Trackpy Environment Installation
expected: Run `bioimage-mcp install trackpy` and environment installs successfully without errors
result: issue
reported: "The command also installs base env, even though base env is already installed. The base env install also errors out (numpy build error), but the trackpy env is installed successfully. Afterwards running bioimage-mcp shows command not found, until pip install -e . is run again."
severity: major

### 2. Doctor Reports Trackpy Healthy
expected: Run `bioimage-mcp doctor` and see trackpy environment listed as "ok" or "installed"
result: issue
reported: "bioimage-mcp doctor failed: meta.list failed for tools.cellpose (Unknown fn_id: meta.list), output says NOT READY."
severity: major

### 3. List Shows Trackpy Functions
expected: MCP `list` command with path "trackpy" shows available trackpy functions (locate, link, batch, etc.)
result: pass

### 4. Describe Returns Function Schema
expected: MCP `describe` for a trackpy function (e.g., trackpy.locate) returns parameter names, types, and docstring
result: pass

### 5. Trackpy Locate Executes
expected: Running trackpy.locate via MCP on an image returns a table artifact with detected particle positions (x, y, mass columns)
result: issue
reported: "locate worked on a single frame but failed on multi-frame images due to dimension/worker errors."
severity: major

### 6. Trackpy Link Executes
expected: Running trackpy.link on feature table returns trajectory data with particle IDs tracked across frames
result: issue
reported: "1. Trackpy Batch Execution Failure: trackpy.batch failed with JSON decoding error (worker crash). 2. Persistent Ordinal Mismatch: Subsequent calls failed with 'Ordinal mismatch' (expected 6, got 5). Worker stability issues with multi-dimensional images."
severity: blocker

## Summary

total: 6
passed: 2
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "Run bioimage-mcp install trackpy and environment installs successfully without errors"
  status: failed
  reason: "User reported: The command also installs base env even though already installed. Base env install errors out (numpy build error). After install, bioimage-mcp command not found until pip install -e . is run again."
  severity: major
  test: 1
  root_cause: "`_env_exists` in `install.py` fails to parse `mamba/conda env list --json` output when it contains non-JSON text (warnings). It returns False (mistakenly), triggering a destructive `env update --prune` on base environment which removes the CLI."
  artifacts:
    - path: "src/bioimage_mcp/bootstrap/install.py"
      issue: "`json.loads(proc.stdout)` is called on raw stdout without cleaning; crashes on mixed text/JSON output."
  missing:
    - "Robust JSON extraction in `_env_exists` (find first `{`)."
  debug_session: ".planning/debug/install-regression.md"

- truth: "Run bioimage-mcp doctor and see trackpy environment listed as ok"
  status: failed
  reason: "User reported: bioimage-mcp doctor failed: meta.list failed for tools.cellpose (Unknown fn_id: meta.list), output says NOT READY."
  severity: major
  test: 2
  root_cause: "`tools.cellpose` manifest specifies `dynamic_sources`, triggering fallback to `meta.list` out-of-process discovery, but its worker entrypoint does not implement `meta.list`."
  artifacts:
    - path: "tools/cellpose/bioimage_mcp_cellpose/entrypoint.py"
      issue: "Missing `meta.list` handler in `FUNCTION_HANDLERS` and `process_execute_request`."
  missing:
    - "Implement `handle_meta_list` function in `tools/cellpose/bioimage_mcp_cellpose/entrypoint.py`"
    - "Add `meta.list` to `FUNCTION_HANDLERS` mapping"
  debug_session: ".planning/debug/doctor-failure.md"

- truth: "Running trackpy.locate via MCP on an image returns a table artifact with detected particle positions"
  status: failed
  reason: "User reported: locate worked on a single frame but failed on multi-frame images due to dimension/worker errors."
  severity: major
  test: 5
  root_cause: "Known issue: Worker stdout pollution corrupts NDJSON stream (see Ordinal Mismatch). Trackpy printing to stdout during processing."
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Running trackpy.link on feature table returns trajectory data with particle IDs tracked across frames"
  status: failed
  reason: "User reported: trackpy.batch crashed (JSON error), causing persistent Ordinal Mismatch for subsequent calls (link). Worker state desync requires manual kill."
  severity: blocker
  test: 6
  root_cause: "Worker functions printing to stdout (like trackpy) corrupt the NDJSON IPC stream. The client caught JSONDecodeError but kept the worker alive, causing the next request to read the buffered response from the previous failed request (Ordinal mismatch)."
  artifacts:
    - path: "src/bioimage_mcp/runtimes/persistent.py"
      issue: "Caught exceptions during IPC read/decode but failed to terminate the corrupted worker process"
  missing:
    - "Strict worker termination on any protocol violation (JSON error, ordinal mismatch)"
  debug_session: ".planning/debug/ordinal-mismatch.md"
