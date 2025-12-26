# Code Review: 006-phasor-usability-fixes

**Date**: Fri Dec 26 17:46:38 CET 2025
**Reviewer**: Orchestrator

## Summary

| Category | Status | Details |
|----------|--------|---------|
| Tasks | **FAIL** | US4 (IO Compatibility) is implemented as dead code; dependencies missing. |
| Tests | **PASS** | All 23 tests pass, but US4 tests verify isolated code not used in production. |
| Coverage | **HIGH** | New functions are tested, but integration is missing for IO fallback. |
| Architecture | **FAIL** | Logic split between `io.py` and `utils.py` resulted in incomplete integration. |
| Constitution | **PASS** | Changes align with principles, but implementation is incomplete. |

## Findings

### 1. [CRITICAL] IO Fallback Logic Not Integrated (US4)
The new function `load_image_fallback` was implemented in `tools/base/bioimage_mcp_base/io.py`, but it is **never used**.
- **File**: `tools/base/bioimage_mcp_base/utils.py`
- **Details**: The `load_image` function in `utils.py` (used by all transforms) still contains the old, hardcoded loading logic. It does not import or call `load_image_fallback`.
- **Impact**: The bioio-bioformats fallback feature is effectively non-functional for all tools.

### 2. [CRITICAL] Missing Environment Dependencies (US4)
The `bioio-bioformats` reader requires Java and specific python packages which are missing from the environment definition.
- **File**: `envs/bioimage-mcp-base.yaml`
- **Details**: Missing `openjdk`, `scyjava`, and `bioio-bioformats`.
- **Impact**: Even if the code were integrated, the fallback to bioformats would crash with `ImportError` or runtime errors.

### 3. [MEDIUM] Misleading Integration Tests (US4)
The integration tests verify the `load_image_fallback` function in isolation, ignoring the actual entry point used by the application.
- **File**: `tests/integration/test_io_fallback_chain.py`
- **Details**: Tests import directly from `bioimage_mcp_base.io`, bypassing `bioimage_mcp_base.utils.load_image`. This masked the integration failure.

### 4. [LOW] Duplicate Code Block (US3)
- **File**: `tools/base/bioimage_mcp_base/transforms.py`
- **Details**: Lines 594-604 contain a duplicate `return` block for `phasor_calibrate`, making it unreachable code.

## Remediation

1.  **Integrate IO Fallback**:
    - Modify `tools/base/bioimage_mcp_base/utils.py` to import `load_image_fallback` from `.io` and delegate `load_image` calls to it.
    - OR move `load_image` entirely to `io.py` and update imports in `transforms.py`.

2.  **Update Environment**:
    - Add `openjdk`, `scyjava`, and `bioio-bioformats` to `envs/bioimage-mcp-base.yaml`.
    - Run `conda-lock` to update the lockfile.

3.  **Fix Tests**:
    - Update `tests/integration/test_io_fallback_chain.py` to test `bioimage_mcp_base.utils.load_image` instead of the internal function.

4.  **Cleanup**:
    - Remove the duplicate return block in `phasor_calibrate`.

## Fix Report
**Date**: Fri Dec 26 2025
**Status**: All Critical and Medium issues resolved.

1.  **US4 (IO Compatibility)**:
    -   Moved `load_image_fallback` and helper functions from `io.py` to `utils.py` to allow universal access.
    -   Updated `utils.load_image_with_warnings` to use the robust fallback chain (ome-tiff -> bioformats -> tifffile).
    -   Updated `io.export_ome_tiff` to use the shared fallback logic, removing duplicated code.
    -   Added `bioio-bioformats`, `openjdk`, and `scyjava` to `envs/bioimage-mcp-base.yaml`.

2.  **US3 (Code Cleanup)**:
    -   Removed unreachable duplicate return block in `transforms.py` (`phasor_calibrate`).

3.  **Tests**:
    -   Updated `tests/integration/test_io_fallback_chain.py` to test the logic now residing in `utils.py`.
    -   Verified all tests pass with `pytest`.
