# Retrospective: Investigation of Wrapper Elimination and System Consistency

**Date:** December 29, 2025  
**Project:** Bioimage-MCP  
**Spec:** 009-wrapper-elimination

## Executive Summary
The investigation into the `bioimage-mcp` system following the elimination of the "wrapper" and "builtin" tool layers has identified several critical issues that impact system reliability and user experience. The primary concerns involve stale state in the SQLite database, inconsistencies in configuration files, and bugs in the discovery/search mechanisms. While the MCP guidance patterns show promise, technical hurdles in artifact format compatibility and metadata propagation remain.

---

## Issue 1: Stale SQLite Database Entries (CRITICAL)

### Finding
The SQLite database used for tool discovery contains stale entries for the `tools.builtin` package, which now references a non-existent manifest.

### Evidence
Direct query of the `functions` table in `~/.bioimage-mcp/artifacts/state/bioimage_mcp.sqlite3` shows:
```python
[('builtin.gaussian_blur', 'tools.builtin'), ('builtin.convert_to_ome_zarr', 'tools.builtin')]
```
These entries point to `/mnt/c/Users/meqia/bioimage-mcp/tools/builtin/manifest.yaml`, a path that has been removed.

### Impact
LLM agents see `builtin.*` functions in `list_tools` output but receive a "Function not found" error from the executor upon invocation. This leads to broken workflows and agent confusion.

### Root Cause
The `tools/builtin` directory was removed as part of the wrapper elimination effort, but the database synchronization logic did not account for the deletion of entire manifest roots.

### Fix Options
1.  **Immediate:** Manually remove stale entries from the database or delete the `bioimage_mcp.sqlite3` file to force a full re-initialization.
2.  **Long-term:** Implement database cleanup logic during server startup that validates all registered manifests against the filesystem and removes orphaned entries.
3.  **Cleanup:** Remove the `tools/builtin` path from all configuration files.

---

## Issue 2: Config File References Non-Existent Directory

### Finding
Both user-level (`~/.bioimage-mcp/config.yaml`) and project-level (`.bioimage-mcp/config.yaml`) configuration files still reference the `tools/builtin` directory in the `tool_manifest_roots` list.

### Evidence
Config content snippet:
```yaml
registry:
  tool_manifest_roots:
    - ./tools/base
    - ./tools/cellpose
    - ./tools/builtin  # <--- Non-existent path
```

### Impact
The server attempts to scan non-existent directories, causing log noise and potential initialization errors.

### Fix
Remove the `./tools/builtin` entry from all configuration files.

---

## Issue 3: list_tools Pagination Returns Empty First Page

### Finding
The `list_tools` function occasionally returns an empty `tools` array on the first page even when valid tools exist.

### Evidence
Multiple calls to `list_tools(path="base.skimage")` and `list_tools(path="base.skimage.filters")` returned:
```json
{
  "tools": [],
  "next_cursor": "eyJvZmZzZXQiOiAxMCwgImxpbWl0IjogMTB9"
}
```
Tools only appeared after following the `next_cursor`.

### Impact
LLM agents may incorrectly conclude that no tools exist at a specific path if the first page is empty, failing to explore further.

### Root Cause
The pagination logic in `ToolIndex.list_children` or `ToolIndex.flatten_tools` (likely in `registry/index.py`) may have off-by-one errors or misalignments between hierarchical filtering and flat limit/offset calculations.

### Recommendation
Audit the `registry/index.py` implementation to ensure empty pages are skipped or that the offset/limit logic correctly accounts for filtered hierarchical views.

---

## Issue 4: search_functions Returns Empty for Valid Queries

### Finding
Semantic and keyword search via `search_functions` fails to return results for established terms.

### Evidence
Calls with `query="phasor"` and `query="wrapper"` returned zero results, despite these terms existing in function summaries and documentation.

### Impact
Agents cannot discover functions through semantic intent, forcing them to rely on exhaustive (and often broken) browsing of the tool hierarchy.

### Root Cause
Potential issues with the Full-Text Search (FTS) indexing or the `SearchIndex.rank()` method. Keywords may not be properly normalized or indexed during the manifest registration process.

### Recommendation
Verify that the SQLite FTS5 extension is working as expected and check the `SearchIndex` implementation for query normalization bugs.

---

## Issue 5: OME-Zarr Format Not Supported by Some Tools

### Finding
Passing an OME-Zarr artifact to downstream tools like `phasor_from_flim` results in a failure.

### Evidence
Running `phasor_from_flim` with a Zarr input produced by the (now defunct) `convert_to_ome_zarr`:
```text
BioImage does not support the image: [path/to/artifact.zarr]
```

### Impact
Modular pipelines using Zarr for intermediate storage are currently broken.

### Root Cause
The `bioio` plugin architecture may not be recognizing Zarr directories without specific extensions or without the `bioio-zarr` plugin properly configured.

### Recommendation
Standardize on OME-Zarr extensions (e.g., `.ome.zarr`) and ensure the `bioio-zarr` plugin is installed in all relevant tool environments.

---

## Issue 6: Inconsistent Axis Metadata Between Tools

### Finding
Axis metadata is inconsistent or lost between different tools in a workflow.

### Evidence
-   `phasor_from_flim` error: `"Unknown time_axis 'T' for axes 'ZYX'"` (indicating it expected a T axis but found ZYX).
-   `relabel_axes` error: `"Axis Z not found in image with axes ."` (indicating the axes string was empty).

### Impact
Workflows involving axis manipulation (projection, reshaping, relabeling) fail unpredictably.

### Root Cause
Discrepancies in how different tool implementations (e.g., those using `scikit-image` vs. `phasorpy`) read and write OME-TIFF/Zarr metadata.

### Recommendation
Enforce a strict metadata propagation contract. All tools must validate and preserve axis metadata, or provide a standardized "metadata-fix" utility.

---

## MCP Guidance Patterns (Best Practices Analysis)

### What the MCP Does Well
1.  **Rich `describe_function` output:** Provides comprehensive schemas including input/output ports and parameter defaults.
2.  **Actionable Hints:** Tools like `phasor_from_flim` include excellent `error_hints` for specific failures (e.g., `AXIS_SAMPLES_ERROR`).
3.  **Workflow Replayability:** Run responses include `workflow_hint` suggesting the next steps (e.g., using `activate_functions`).

### What Could Be Improved
1.  **Session Lifecycle:** Lack of clear guidance on when to start/resume sessions.
2.  **Function Ordering:** No "Getting Started" guidance for specific domains (e.g., "What tool do I use first for FLIM?").
3.  **Artifact Persistence:** No clarity for the agent on how long temporary artifacts persist.
4.  **Compatibility Matrix:** No mechanism for an agent to query which formats (TIFF vs Zarr) a specific function supports before trying to call it.

---

## Recommendations

### Immediate Fixes (Priority 1)
1.  Delete `~/.bioimage-mcp/artifacts/state/bioimage_mcp.sqlite3` to clear stale entries.
2.  Remove `tools/builtin` from `~/.bioimage-mcp/config.yaml` and `.bioimage-mcp/config.yaml`.
3.  Restart the MCP server.

### Short-Term Improvements (Priority 2)
1.  **Staleness Detection:** Add logic to the server startup to detect and prune manifests that no longer exist on disk.
2.  **Pagination Fix:** Resolve the empty-first-page bug in `list_tools`.
3.  **Search Debugging:** Repair the keyword matching logic in `search_functions`.

### Long-Term Improvements (Priority 3)
1.  **`bioimage-mcp doctor` Command:**
    *   Validate config paths.
    *   Check for orphaned DB entries.
    *   Verify required bioio plugins are present.
    *   Report format compatibility across tool packs.
2.  **Guidance Tools:**
    *   `get_workflow_templates(domain)`: Return common patterns (e.g., for "flim" or "segmentation").
    *   `get_format_compatibility(fn_id)`: Return supported input/output formats.
    *   `validate_artifact(ref_id)`: Pre-check if an artifact is compatible with a target function.
