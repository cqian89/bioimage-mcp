# Phase 7 Plan 1: Add IO patterns for JSON + multi-output labeling Summary

Enables analytical extraction from images by implementing IO patterns for measurements and multi-output labeling in the scipy adapter.

## Accomplishments
- Added new `IOPattern` variants: `IMAGE_TO_JSON`, `IMAGE_AND_LABELS_TO_JSON`, and `IMAGE_TO_LABELS_AND_JSON`.
- Implemented port mapping for these patterns in `loader.py`, ensuring they advertise appropriate artifact types (e.g., `ScalarRef` for JSON outputs).
- Updated `ScipyNdimageAdapter` to classify functions as measurements or transforms based on their name.
- Enhanced `ScipyNdimageAdapter.execute` to handle multiple outputs, specifically for `scipy.ndimage.label` which returns both a labeled image and an object count.
- Updated `ScipyNdimageAdapter._save_scalar` to recursively handle numpy scalars, tuples, lists, and slices, ensuring complex measurement outputs are JSON-serializable.
- Verified with contract tests for discovery and execution, and unit tests for port mapping.

## Key Files
- `src/bioimage_mcp/registry/dynamic/models.py`: Added IO pattern enums.
- `src/bioimage_mcp/registry/loader.py`: Added port mappings for new patterns.
- `src/bioimage_mcp/registry/dynamic/adapters/scipy_ndimage.py`: Implemented classification and multi-output execution.
- `tests/contract/test_scipy_adapter.py`: Added discovery and execution tests.
- `tests/unit/registry/test_loader_io_patterns.py`: Added unit tests for port mapping.

## Deviations from Plan
None - plan executed exactly as written.

## Decisions Made
- **Output Naming**: Explicitly set `output_name` in metadata for `label` outputs (`labels` and `output`) to ensure the server correctly maps them to the advertised ports.
- **Recursive JSON serialization**: Implemented `_to_native` helper in `_save_scalar` to ensure all components of a measurement tuple/list (like `extrema` or `center_of_mass`) are correctly converted to native Python types.

## Next Phase Readiness
- Ready for Phase 7 Plan 2: Implement zoom metadata updates and transform pass-through.

## Metrics
- **Duration**: 29490402 min
- **Started**: 
- **Completed**: 2026-01-26T10:42:17Z
- **Tasks completed**: 4/4
- **Files modified**: 5
