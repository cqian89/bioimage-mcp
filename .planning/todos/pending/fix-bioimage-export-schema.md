# Fix: base.io.bioimage.export Schema Overpromises ObjectRef Support

## Summary
The `base.io.bioimage.export` manifest schema claims support for `ObjectRef` inputs, but the implementation only handles image-like objects (xarray DataArrays, numpy arrays). When an ObjectRef containing a table (DataFrame) is passed, it fails with "Cannot export object of type DataFrame".

## Root Cause
- **Manifest** (`tools/base/manifest.yaml` lines 232-236): Accepts `[BioImageRef, LabelImageRef, ObjectRef]`
- **Implementation** (`tools/base/bioimage_mcp_base/ops/io.py` line 1179): Only handles objects with `.values` attribute (xarray) or numpy arrays

## Recommended Fix
**Option A (Recommended)**: Restrict schema to match implementation
```yaml
inputs:
  - name: image
    artifact_type: [BioImageRef, LabelImageRef]  # Remove ObjectRef
    required: true
    description: Image or label artifact to export (use base.io.table.export for tables)
```

**Option B**: Extend implementation to detect and route table exports
- This adds complexity and duplicates `base.io.table.export` functionality
- Not recommended

## Files to Modify
- `tools/base/manifest.yaml` (lines 232-236)

## Related
- `base.io.table.export` already handles table exports correctly
- Users should be directed to use the appropriate export function

## Priority
Medium - Schema mismatch causes confusing errors but workaround exists

## Created
2026-01-31
