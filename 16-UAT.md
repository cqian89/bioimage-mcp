# Phase 16: StarDist Tool Environment UAT

| Test | Expected Behavior | Status | Severity | Notes |
|------|-------------------|--------|----------|-------|
| 1. Install StarDist Environment | `bioimage-mcp install stardist` completes with "Installed: 1" and no errors. | Pass | High | Verifies env definition and lockfile. |
| 2. List StarDist Tool | `bioimage-mcp list --tool stardist` shows `stardist` in the output with status `ready` or similar (not `missing`). | Pass | High | Verifies tool registration and manifest. |
| 3. Verify End-to-End Workflow | `pytest tests/integration/test_stardist_adapter_e2e.py` passes. | Fail | Critical | Missing deps (griffe, mcp), Python version mismatch (3.11 vs 3.13). |

## Issues Found

### Issue 1: StarDist entrypoint imports core server code requiring unavailable dependencies
**Severity:** Critical  
**Description:** `tools/stardist/bioimage_mcp_stardist/entrypoint.py` imports from the core server (`bioimage_mcp.registry.dynamic.cache`, `bioimage_mcp.registry.dynamic.discovery`, `bioimage_mcp.registry.manifest_schema`, `bioimage_mcp.registry.engine`). These require dependencies like `griffe` and `mcp` which are not installed in the `bioimage-mcp-stardist` conda environment.

**Root Cause:** The entrypoint tries to add `REPO_ROOT/src` to `sys.path` (lines 29-31), but this only works when:
1. The repo structure is present at runtime
2. All core server dependencies are available

When running `conda run -n bioimage-mcp-stardist pytest ...`, the core server's dependencies (`griffe`, `mcp`) are not in the stardist env, causing import failures.

### Issue 2: Python version incompatibility prevents installing core server in tool env
**Severity:** Critical  
**Description:** The core server requires Python >= 3.13 (`pyproject.toml`), but the StarDist environment is pinned to Python 3.11 (required for TensorFlow/StarDist compatibility). This makes it impossible to `pip install -e .` the core server into the tool environment.

### Issue 3: Test design requires running inside tool environment but needs core server
**Severity:** High  
**Description:** The test docstring says to run with `conda run -n bioimage-mcp-stardist pytest ...`, but the test imports from `bioimage_mcp_stardist.entrypoint`, which in turn imports core server code. This is a circular dependency that cannot be resolved without architectural changes.

## Diagnosed Root Cause

The StarDist tool pack was designed to reuse the core server's introspection utilities (`IntrospectionCache`, `discover_functions`, `DiscoveryEngine`, `Introspector`), but this creates a dependency on the core server from within the isolated tool environment. Unlike Cellpose (which has a `CellposeAdapter` in the core server itself), StarDist's adapter lives entirely in the tool pack.

## Recommended Fixes

1. **Option A (Minimal):** Move StarDist introspection utilities to be self-contained within the tool pack, eliminating core server imports for the entrypoint's critical paths.

2. **Option B (Refactor):** Create a `stardist` adapter in the core server (`src/bioimage_mcp/registry/dynamic/adapters/stardist.py`) like Cellpose, and have the tool pack entrypoint only handle execution, not discovery.

3. **Option C (Test Fix):** Rewrite the integration test to run from the core server environment (Python 3.13), invoking StarDist tools via the MCP subprocess execution path rather than direct imports.
