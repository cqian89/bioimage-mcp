---
phase: 06-infrastructure-n-d-foundation
plan: 3
subsystem: registry
tags: [scipy, ndimage, dynamic-adapter, memory-safety, metadata]

# Dependency graph
requires:
  - phase: 06-infrastructure-n-d-foundation
    provides: [scipy dynamic adapter discovery]
provides:
  - Memory-safe scipy.ndimage execution
  - Metadata pass-through for physical pixel sizes
  - Support for auxiliary array artifacts and safe callables
affects: [07-transforms-measurements]

# Tech tracking
tech-stack:
  added: []
  patterns: [Safe Callable Resolver, Context-Dependent Return Format]

key-files:
  created: 
    - src/bioimage_mcp/registry/dynamic/adapters/callable_registry.py
    - tests/unit/registry/dynamic/test_scipy_ndimage_execute.py
  modified: 
    - src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py

key-decisions:
  - "Implemented a curated allowlist for callable resolution to ensure security while supporting scipy measurements."
  - "Used 16MB threshold for uint16 to float32 casting to balance performance and memory safety."
  - "Adopted context-dependent return formats: OME-TIFF for arrays and JSON for scalar measurements."

patterns-established:
  - "Named Input Resolution: Prefer 'image' or 'input' keys for primary data, falling back to first artifact."
  - "Metadata Pass-through: Explicitly preserve physical pixel sizes and channel names across operations."

# Metrics
duration: 25min
completed: 2026-01-25
---

# Phase 6 Plan 3: Scipy N-D Infrastructure Summary

**Memory-safe scipy.ndimage execution with metadata preservation, auxiliary artifact support, and safe callable resolution.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-01-25T12:00:00Z
- **Completed:** 2026-01-25T12:25:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- **Safe Callable Resolver:** Created a secure mapping from string references to numpy/scipy callables, preventing arbitrary code execution while enabling powerful measurement tools.
- **Enhanced Scipy Adapter:** Updated the execution engine to handle named inputs correctly, automatically resolve auxiliary arrays like footprints, and ensure memory safety when processing large uint16 microscopy data.
- **Metadata Preservation:** Implemented pass-through logic for critical scientific metadata, including physical pixel sizes (microns/ms) and channel names, ensuring downstream tools have accurate spatial context.
- **Robust Output Handling:** Established a context-dependent return strategy where multi-dimensional results are stored as OME-TIFF artifacts and scalar measurements are returned as structured JSON.

## Task Commits

Each task was committed atomically:

1. **Task 1: Safe callable resolver** - `515e158` (feat)
2. **Task 2: Scipy adapter update** - `5f50322` (feat)
3. **Task 3: Unit tests** - `3268b0e` (test)

**Plan metadata:** `[TBD]` (docs: complete plan)

## Files Created/Modified
- `src/bioimage_mcp/registry/dynamic/adapters/callable_registry.py` - Safe string-to-callable resolution mapping.
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py` - Core execution logic for scipy functions.
- `tests/unit/registry/dynamic/test_scipy_ndimage_execute.py` - Comprehensive test suite for execution patterns.

## Decisions Made
- **Allowlist for Callables:** Only specific numpy functions (min, max, mean, etc.) are allowed to be passed as parameters to avoid security risks associated with arbitrary function execution.
- **TCZYX 5D Preservation:** The adapter now strictly avoids `np.squeeze` on inputs, trusting `bioio` to provide the native 5D structure required for consistent dimension handling in scipy.
- **JSON for Scalars:** Chose to return scalar results (like mean intensity or center of mass) as JSON artifacts rather than single-pixel images to improve readability and usability for AI agents.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Robust 1D array handling in OME-TIFF save**
- **Found during:** Task 3 (Unit tests)
- **Issue:** `tifffile` and `bioio` failed when saving 1D arrays (like those from measurement functions) because they expect at least 2 dimensions for TIFF format.
- **Fix:** Added logic to `_save_image` to automatically reshape 1D arrays to 2D (1, N) and set axes to "YX" for format compatibility.
- **Files modified:** `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py`
- **Verification:** `test_execute_callable_resolution` now passes with 1D/scalar results.
- **Committed in:** `5f50322` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for supporting scipy measurement APIs that return non-image data. No scope creep.

## Issues Encountered
- **Mocking importlib.import_module:** Initial tests failed because a global patch of `import_module` broke `bioio`'s internal imports. Resolved by using a `side_effect` that only mocks the target `scipy.ndimage` namespace.

## Next Phase Readiness
- Infrastructure for N-D image processing is now robust and ready for Phase 7 (Transforms & Measurements).
- Coordinate-aware operations can now rely on preserved physical pixel sizes.

---
*Phase: 06-infrastructure-n-d-foundation*
*Completed: 2026-01-25*
