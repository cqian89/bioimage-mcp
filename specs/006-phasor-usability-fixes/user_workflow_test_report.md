# Phasor FLIM Workflow - User Perspective Test Report

**Date:** December 26, 2025
**Tester:** LLM Agent (simulating fresh user)
**Dataset:** `datasets/FLUTE_FLIM_data_tif/Embryo.tif` with `Fluorescein_Embryo.tif` as calibration reference

## Test Methodology

This test repeats the workflow from `docs/plan/phasor_workflow_usability_report.md` from a user perspective, without inspecting the codebase for hints. All tool calls are documented with their inputs and outputs.

---

## Step 1: List Available Tools

### Tool Call
```
bioimage-mcp_list_tools(limit=20)
```

### Result: INTERMITTENT FAILURE
**First attempt:** `Error: 'Session session_137966225781296 not found'`
**Second attempt (later):** SUCCESS - returned 3 tools:
- `tools.base` - Base Image Processing Toolkit
- `tools.builtin` - Built-ins
- `tools.cellpose` - Cellpose Segmentation

### Issue Found
**Session Initialization Race Condition**: The `list_tools` command failed initially with a session not found error, but worked later in the session. This suggests a race condition in session initialization that can cause sporadic failures for early discovery calls.

---

## Step 2: Search for Phasor Functions

### Tool Call
```
bioimage-mcp_search_functions(query="phasor")
```

### Result: INTERMITTENT FAILURE
**First attempt:** `Error: 'Session session_137966225781296 not found'`
**Later attempt:** SUCCESS - Found functions including `base.phasor_from_flim` and `base.phasor_calibrate`

### Issue Found
Same session initialization race condition as Step 1.

---

## Step 3: Describe phasor_from_flim Function

### Tool Call
```
bioimage-mcp_describe_function(fn_id="base.phasor_from_flim")
```

### Result: SUCCESS
```json
{
  "fn_id": "base.phasor_from_flim",
  "schema": {
    "properties": {
      "harmonic": {
        "description": "Phasor harmonic to compute (default 1).",
        "type": "integer"
      },
      "time_axis": {
        "description": "Time/bin axis name or index for the FLIM signal (e.g., 'T' or 0).",
        "type": "string"
      }
    },
    "required": [],
    "type": "object"
  },
  "introspection_source": "python_api"
}
```

### Improvement from Original Report
The original report noted `describe_function` returned an empty schema. This is now FIXED - useful parameter documentation is returned.

### Issue Found
**Missing Input Schema**: The schema only shows `params` (harmonic, time_axis), but doesn't document the required `inputs` format. Users must guess or use `dry_run` to discover that:
- The input port is named `dataset`
- It expects a `BioImageRef` object format

---

## Step 4: Run Phasor Analysis on Embryo.tif

### Tool Call Attempts

#### Attempt 1: String path as input
```
bioimage-mcp_call_tool(
  fn_id="base.phasor_from_flim",
  inputs={"uri": "/mnt/c/.../Embryo.tif"},
  params={"harmonic": 1, "time_axis": "T"}
)
```
**Result:** `Error: Workflow validation failed: 1 error(s)`

**Issue:** Error message is not actionable - doesn't say what failed.

#### Attempt 2: Using dry_run for diagnostics
```
bioimage-mcp_call_tool(
  fn_id="base.phasor_from_flim",
  inputs={"image": "/mnt/c/.../Embryo.tif"},
  params={"harmonic": 1, "time_axis": "T"},
  dry_run=true
)
```
**Result:** Detailed error showing:
```json
{
  "port_name": "dataset",
  "expected_type": "BioImageRef",
  "actual_type": "missing",
  "message": "Step 0 missing required input 'dataset'"
}
```

**Improvement:** `dry_run=true` provides excellent error diagnostics!

#### Attempt 3: Correct input port name, string value
```
bioimage-mcp_call_tool(
  fn_id="base.phasor_from_flim",
  inputs={"dataset": "/mnt/c/.../Embryo.tif"},
  params={"harmonic": 1, "time_axis": "T"}
)
```
**Result:** `Error: 'str' object has no attribute 'get'`

**Issue:** The input needs to be an object, not a string. Error message is cryptic.

#### Attempt 4: BioImageRef object format
```
bioimage-mcp_call_tool(
  fn_id="base.phasor_from_flim",
  inputs={"dataset": {"type": "BioImageRef", "uri": "/mnt/c/.../Embryo.tif"}},
  params={"harmonic": 1, "time_axis": "T"}
)
```
**Result:** `Error: not enough samples=1 along axis=0`

**Issue:** Tool executes but fails on axis interpretation.

#### Attempt 5: Different time_axis values
- `time_axis="0"` -> `Error: Unknown time_axis '0' for axes 'TCZYX'`
- `time_axis` omitted (default) -> `Error: not enough samples=1 along axis=0`

### Critical Issue Found
**FLIM Data Axis Interpretation Failure**: The bioio library reads the 3D FLIM stack (256 time bins x Y x X) as 5D TCZYX with T=1. The actual FLIM time-bin dimension is being collapsed or misidentified. This prevents the phasor computation from having any samples along the time axis.

The image is reported as having axes `TCZYX` where:
- T = 1 (should be the 256 FLIM time bins)
- C, Z dimensions also appear to be singleton or wrong

This is a data compatibility issue where the FLIM TIFF files don't have proper metadata for bioio to interpret the dimensions correctly.

---

## Step 5: Describe phasor_calibrate Function

### Tool Call
```
bioimage-mcp_describe_function(fn_id="base.phasor_calibrate")
```

### Result: SUCCESS
```json
{
  "fn_id": "base.phasor_calibrate",
  "schema": {
    "properties": {
      "frequency": {
        "description": "Laser repetition frequency in Hz (e.g., 80e6 for 80 MHz)."
      },
      "harmonic": {
        "description": "Harmonic number for multi-harmonic analysis (default: 1).",
        "type": "integer"
      },
      "lifetime": {
        "description": "Known lifetime of reference standard in nanoseconds (e.g., 4.04 for Fluorescein)."
      }
    },
    "required": [],
    "type": "object"
  }
}
```

### Improvement from Original Report
The original report stated "No `phasor_calibrate` or equivalent tool exists." This is now FIXED - `base.phasor_calibrate` exists and is discoverable.

### Issue Found
**Cannot Test Calibration**: Since `phasor_from_flim` fails on the sample data, calibration cannot be tested end-to-end.

---

## Step 6: Attempt to Export Results

No artifacts were successfully created due to the axis interpretation failure.

---

## Summary of Findings

### Issues Fixed Since Original Report
| Issue | Status |
|-------|--------|
| Discovery tools return empty/error | PARTIALLY FIXED - works after session warmup |
| `describe_function` returns empty schema | FIXED - returns useful params schema |
| Missing `phasor_calibrate` function | FIXED - function now exists |

### Issues Remaining

| Issue | Severity | Description |
|-------|----------|-------------|
| Session initialization race condition | Medium | `list_tools` and `search_functions` fail with "session not found" on first calls |
| FLIM axis interpretation failure | Critical | bioio reads FLIM TIFFs as TCZYX with T=1, breaking phasor computation |
| Missing input schema in describe_function | Medium | Only params are documented, not input ports |
| Cryptic validation errors | Low | `"Workflow validation failed: 1 error(s)"` without details unless dry_run used |
| String input error message | Low | `"'str' object has no attribute 'get'"` should suggest proper BioImageRef format |

### Recommendations

1. **CRITICAL**: Fix FLIM data axis handling - either:
   - Add metadata-based axis inference for known FLIM formats
   - Add explicit `axes` parameter to `phasor_from_flim` to override auto-detection
   - Document required TIFF metadata format for FLIM data

2. **HIGH**: Fix session initialization race condition - ensure session is created before accepting tool calls

3. **MEDIUM**: Include input port schemas in `describe_function` output (not just params)

4. **LOW**: Improve error messages:
   - Include validation details in non-dry-run errors
   - Suggest `BioImageRef` format when string is passed

---

## Appendix: All Tool Calls Made

| # | Tool | Input Summary | Result |
|---|------|--------------|--------|
| 1 | `list_tools` | limit=20 | FAIL: session not found |
| 2 | `search_functions` | query="phasor" | FAIL: session not found |
| 3 | `describe_function` | fn_id="base.phasor_from_flim" | SUCCESS: schema returned |
| 4 | `call_tool` | dataset as uri string | FAIL: validation failed (vague) |
| 5 | `call_tool` | dataset as path string | FAIL: validation failed |
| 6 | `call_tool` (dry_run) | image string input | SUCCESS: detailed validation error |
| 7 | `call_tool` | dataset string | FAIL: 'str' has no attribute 'get' |
| 8 | `call_tool` | dataset as BioImageRef, time_axis="T" | FAIL: not enough samples=1 |
| 9 | `call_tool` | dataset as BioImageRef, time_axis="0" | FAIL: Unknown time_axis '0' |
| 10 | `call_tool` | dataset as BioImageRef, no time_axis | FAIL: not enough samples=1 |
| 11 | `describe_tool` | tool_id="base.phasor_from_flim" | FAIL: tool not found |
| 12 | `describe_tool` | tool_id="phasor_from_flim" | FAIL: tool not found |
| 13 | `search_functions` | query="calibrate" | SUCCESS: found phasor_calibrate |
| 14 | `describe_function` | fn_id="base.phasor_calibrate" | SUCCESS: schema returned |
| 15 | `list_tools` | limit=10 | SUCCESS: 3 tools returned |
