# Quickstart: Wrapper Elimination Validation

**Date**: 2025-12-29  
**Purpose**: Validate implementation of wrapper elimination and overlay system

## Prerequisites

```bash
# Ensure bioimage-mcp-base environment is installed
python -m bioimage_mcp doctor

# Run tests to verify baseline
pytest tests/contract/ -v
```

## Validation Steps

### 1. Verify Overlay Schema

```bash
# Unit test: overlay model and merge logic
pytest tests/unit/registry/test_overlay_merge.py -v

# Contract test: overlay validation
pytest tests/contract/test_overlay_schema.py -v
```

**Expected**: All tests pass; FunctionOverlay model validates correctly.

### 2. Verify Dynamic Discovery

```bash
# List dynamically discovered functions
python -c "
from bioimage_mcp.registry import RegistryIndex
import asyncio

async def main():
    registry = RegistryIndex()
    await registry.load()
    
    # List skimage functions
    result = await registry.list_tools(path='base.skimage')
    print(f'Skimage functions: {len(result.functions)}')
    
    # Verify gaussian is dynamically discovered
    gaussian = await registry.describe_function('base.skimage.filters.gaussian')
    print(f'Gaussian fn_id: {gaussian.fn_id}')
    print(f'Has hints: {gaussian.hints is not None}')

asyncio.run(main())
"
```

**Expected**: 
- 50+ skimage functions discovered
- `base.skimage.filters.gaussian` exists with merged overlay hints

### 3. Verify Overlay Merging

```bash
# Test overlay merge behavior
python -c "
from bioimage_mcp.registry import RegistryIndex
import asyncio

async def main():
    registry = RegistryIndex()
    await registry.load()
    
    # Describe function with overlay
    fn = await registry.describe_function('base.skimage.filters.gaussian')
    
    # Check overlay fields were applied
    assert 'preprocessing' in fn.tags, 'Tags not merged from overlay'
    assert fn.hints is not None, 'Hints not merged from overlay'
    print('Overlay merge: PASSED')

asyncio.run(main())
"
```

**Expected**: Overlay fields (tags, hints) are present in describe_function response.

### 4. Verify Essential Wrappers Renamed

```bash
# Verify new wrapper namespace
python -c "
from bioimage_mcp.registry import RegistryIndex
import asyncio

EXPECTED_WRAPPERS = [
    'base.wrapper.io.convert_to_ome_zarr',
    'base.wrapper.io.export_ome_tiff',
    'base.wrapper.axis.relabel_axes',
    'base.wrapper.axis.squeeze',
    'base.wrapper.axis.expand_dims',
    'base.wrapper.axis.moveaxis',
    'base.wrapper.axis.swap_axes',
    'base.wrapper.phasor.phasor_from_flim',
    'base.wrapper.phasor.phasor_calibrate',
    'base.wrapper.denoise.denoise_image',
]

async def main():
    registry = RegistryIndex()
    await registry.load()
    
    for fn_id in EXPECTED_WRAPPERS:
        fn = await registry.describe_function(fn_id)
        assert fn is not None, f'Missing wrapper: {fn_id}'
        print(f'✓ {fn_id}')
    
    print('All essential wrappers present')

asyncio.run(main())
"
```

**Expected**: All 10 essential wrappers exist under `base.wrapper.*` namespace.

### 5. Verify Thin Wrappers Removed

```bash
# Verify thin wrappers no longer in static manifest
python -c "
from bioimage_mcp.registry import RegistryIndex
import asyncio

REMOVED_WRAPPERS = [
    'base.bioimage_mcp_base.preprocess.gaussian',
    'base.bioimage_mcp_base.preprocess.median',
    'base.bioimage_mcp_base.transforms.resize',
    'base.bioimage_mcp_base.transforms.rotate',
]

async def main():
    registry = RegistryIndex()
    await registry.load()
    
    for fn_id in REMOVED_WRAPPERS:
        try:
            fn = await registry.describe_function(fn_id)
            if fn is not None:
                print(f'✗ {fn_id} still exists (should be removed)')
        except:
            print(f'✓ {fn_id} correctly removed')

asyncio.run(main())
"
```

**Expected**: Old thin wrapper fn_ids no longer exist (use dynamic equivalents).

### 6. Verify Legacy Redirects

```bash
# Test legacy redirect behavior
pytest tests/integration/test_legacy_redirects.py -v

# Manual validation
python -c "
# This would be run via MCP, but we can test entrypoint logic
import sys
sys.path.insert(0, 'tools/base')
from bioimage_mcp_base.entrypoint import LEGACY_REDIRECTS

print('Legacy redirects configured:')
for old, new in LEGACY_REDIRECTS.items():
    print(f'  {old} → {new}')
"
```

**Expected**: Legacy fn_ids redirect to new fn_ids with deprecation warning.

### 7. Execute Dynamic Function End-to-End

```bash
# Integration test: run dynamically discovered function
pytest tests/integration/test_dynamic_execution.py::test_skimage_gaussian -v
```

**Expected**: `base.skimage.filters.gaussian` executes successfully on test image.

## Success Criteria

| Criterion | Validation | Status |
|-----------|------------|--------|
| SC-001: Static manifest ≤12 essential wrappers | Step 4 | ☐ |
| SC-002: 50+ dynamic skimage functions | Step 2 | ☐ |
| SC-003: Overlay merge works | Step 3 | ☐ |
| SC-004: All tests pass | Full test suite | ☐ |
| SC-005: Consistent naming | Steps 4, 5 | ☐ |
| SC-006: Legacy redirects work | Step 6 | ☐ |

## Troubleshooting

### Dynamic discovery returns 0 functions
- Check `manifest.yaml` has `dynamic_sources` configured
- Verify scikit-image is installed in bioimage-mcp-base env

### Overlay not applied
- Verify fn_id in overlay matches exactly the discovered fn_id
- Check manifest loader logs for overlay merge errors

### Legacy redirect not working
- Verify LEGACY_REDIRECTS dict in entrypoint.py
- Check entrypoint dispatch logic routes through redirects
