# Quickstart: Wrapper Consolidation

## Overview
This spec eliminates 16 manual `base.wrapper.*` tools by implementing:
1. **xarray Adapter**: Unified tool for axis/transform operations via xarray methods
2. **Decentralized Handoff**: Automatic cross-env format negotiation and materialization
3. **input_mode: xarray**: Manifest field for dimension-aware data handling
4. **Persistent Workers & mem://**: Reuse environment state and hold intermediate data in memory

## Before vs After

### Before (Manual Wrappers)
```python
# 3 separate tool calls
zarr = run_function('base.wrapper.io.convert_to_ome_zarr', {'image': ref})
relabeled = run_function('base.wrapper.axis.relabel_axes', 
                         {'image': zarr}, 
                         {'axis_mapping': {'Z': 'T'}})
squeezed = run_function('base.wrapper.axis.squeeze', {'image': relabeled})
```

### After (xarray Adapter & Persistent Workers)
```python
# Single unified interface producing memory-backed artifacts
relabeled = run_function('base.xarray.rename',
                         {'image': ref},
                         {'mapping': {'Z': 'T'}})
squeezed = run_function('base.xarray.squeeze',
                         {'image': relabeled})

# Explicitly save to disk (defaults to OME-TIFF; OME-Zarr support is TBD)
exported = run_function('base.bioio.export', 
                        {'image': squeezed, 'path': 'output.ome.tiff'})
```

## Key Implementation Steps

### 1. Extend Manifest Schema
Add `input_mode`, `apply_ufunc`, and `io_requirements` fields to FunctionDef model.

### 2. Implement xarray Adapter Tools
Register individual tools under `base.xarray.*` (rename, squeeze, expand_dims, transpose, isel, pad, sum, max, mean). These tools will default to `mem://` outputs.

### 3. Persistent Worker Support
Update `ExecutionBridge` and `PersistentWorkerManager` to maintain environments across calls.

### 4. Implement Decentralized Handoff & Export
Add cross-env negotiation, source-env materialization logic, and the `base.bioio.export` tool.

### 4. Delete Wrappers
Remove 16 wrapper tools from manifest and implementation files.

### 5. Update Tests
Add contract and integration tests for new functionality.

## Wrapper Tools to Delete (16)

| Category | Tools |
|----------|-------|
| I/O | convert_to_ome_zarr, export_ome_tiff |
| Axis | relabel_axes, squeeze, expand_dims, moveaxis, swap_axes |
| Transform | crop, project_sum, project_max, flip, pad, normalize_intensity |
| Phasor | phasor_from_flim, phasor_calibrate (convert to direct phasorpy calls) |
| Denoise | denoise_image (replace with apply_ufunc) |

## Verification

```bash
# Run tests
pytest tests/contract/test_xarray_adapter_schema.py
pytest tests/integration/test_xarray_adapter.py

# Verify wrappers removed
grep -r "base.wrapper" tools/base/manifest.yaml
```
