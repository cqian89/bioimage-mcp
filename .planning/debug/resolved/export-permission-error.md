---
status: resolved
trigger: "base.io.bioimage.export fails with PermissionError when trying to save to /mnt/c/.../04-outputs/mean.ome.tiff"
created: 2026-01-23T00:00:00Z
updated: 2026-01-23T00:05:00Z
---

## Current Focus

hypothesis: CONFIRMED - export() in ops/io.py doesn't create parent directory before writing
test: Compared with store.py export which DOES call mkdir; ops/io.py export does NOT
expecting: N/A - root cause confirmed
next_action: Apply fix and verify

## Symptoms

expected: Export image to OME-TIFF at the specified path
actual: PermissionError: [Errno 13] - Access denied
errors: PermissionError: [Errno 13]
reproduction: Call base.io.bioimage.export with params {"path": "/mnt/c/.../04-outputs/mean.ome.tiff"}
started: Worked before, now fails

## Eliminated

## Evidence

- timestamp: 2026-01-23T00:02:00Z
  checked: _export_png, _export_ome_tiff, _export_ome_zarr in ops/io.py
  found: None of these functions create parent directories before writing
  implication: If output dir doesn't exist, write fails with PermissionError or similar

- timestamp: 2026-01-23T00:02:01Z
  checked: artifacts/store.py export function (line 573)
  found: store.py DOES call dest_path.parent.mkdir(parents=True, exist_ok=True) before copy
  implication: Two different code paths - store.py works, ops/io.py doesn't

- timestamp: 2026-01-23T00:02:02Z  
  checked: matplotlib_ops.py (line 881)
  found: Also properly creates parent dir with user_dest_path.parent.mkdir(parents=True, exist_ok=True)
  implication: This is an oversight in ops/io.py export, not a design decision

- timestamp: 2026-01-23T00:02:03Z
  checked: Existing tests for export to nonexistent directory
  found: No tests cover this edge case
  implication: Missing test coverage for this scenario

## Resolution

root_cause: The export() function in ops/io.py does not create the parent directory before writing. When user specifies a path like "/mnt/c/.../04-outputs/mean.ome.tiff" and the "04-outputs" directory doesn't exist, the underlying writers (OmeTiffWriter, imageio, etc.) fail with PermissionError [Errno 13] because they cannot write to a nonexistent directory.
fix: Added dest_path.parent.mkdir(parents=True, exist_ok=True) before calling _export_* functions in export() and table_export() functions in ops/io.py
verification: |
  1. Tested export() to nested nonexistent directory - PASSED
  2. Tested table_export() to nested nonexistent directory - PASSED
  3. All 43 unit tests in test_table_export.py and test_io_functions.py - PASSED
  4. All 5 integration tests in test_io_workflow.py - PASSED (4 passed, 1 skipped)
files_changed: [tools/base/bioimage_mcp_base/ops/io.py]
