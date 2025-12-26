# Quickstart: Phasor Workflow Usability Fixes

## Overview

This feature fixes critical usability issues in the phasor-FLIM workflow. After implementation:

1. ✅ Discovery endpoints (`list_tools`, `search_functions`) work without errors
2. ✅ `describe_function` returns complete parameter schemas
3. ✅ Phasor calibration is available for quantitative FLIM analysis
4. ✅ OME-TIFF files with complex metadata load reliably

## Prerequisites

```bash
# Ensure you're on the feature branch
git checkout 006-phasor-usability-fixes

# Install development dependencies
pip install -e ".[dev]"

# Install the base tool environment
micromamba create -f envs/bioimage-mcp-base.yaml
micromamba activate bioimage-mcp-base
```

## Running Tests

### TDD Workflow

Follow red-green-refactor for each fix:

```bash
# 1. Run tests (expect failures for new tests)
pytest tests/unit/api/test_server_session.py -v

# 2. Implement the fix
# 3. Run tests again (expect passes)
pytest tests/unit/api/test_server_session.py -v

# 4. Run all related tests
pytest tests/contract/test_discovery_contract.py -v
pytest tests/contract/test_phasor_calibrate.py -v
pytest tests/integration/test_io_fallback.py -v
```

### Full Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bioimage_mcp --cov-report=html
```

## Implementation Tasks

### Task 1: Fix ServerSession.id Error

**File**: `src/bioimage_mcp/api/server.py`

```python
# Before
def get_session(ctx: Context) -> Any:
    return session_manager.ensure_session(ctx.session.id)  # FAILS

# After
def get_session_identifier(ctx: Context) -> str:
    """Get stable session identifier from MCP context."""
    # Try SSE transport session_id first
    if hasattr(ctx, 'request_context') and ctx.request_context:
        req = getattr(ctx.request_context, 'request', None)
        if req and hasattr(req, 'query_params'):
            sid = req.query_params.get('session_id')
            if sid:
                return sid
    # Fallback to memory-based identifier
    return f"session_{id(ctx.session)}"

def get_session(ctx: Context) -> Any:
    return session_manager.ensure_session(get_session_identifier(ctx))
```

### Task 2: Fix Empty Schema from describe_function

**File**: `tools/base/bioimage_mcp_base/entrypoint.py`

Verify that `meta.describe` correctly extracts schemas from:
1. Static function definitions in manifest.yaml
2. Dynamic functions discovered via adapters (phasorpy, skimage)

### Task 3: Add Phasor Calibration

**File**: `tools/base/bioimage_mcp_base/transforms.py`

```python
def phasor_calibrate(*, inputs: dict, params: dict, work_dir: Path) -> dict[str, Any]:
    """Calibrate phasor coordinates using a reference standard.
    
    Inputs:
        sample_phasors (BioImageRef): 2-channel phasor image (G=ch0, S=ch1)
        reference_phasors (BioImageRef): 2-channel reference phasor image
    
    Params:
        lifetime (float): Known lifetime of reference in nanoseconds
        frequency (float): Laser repetition frequency in Hz
        harmonic (int): Harmonic number (default: 1)
    
    Outputs:
        calibrated_phasors (BioImageRef): 2-channel calibrated phasor image
    """
    # Implementation wraps phasorpy.lifetime.phasor_calibrate
    pass
```

**File**: `tools/base/manifest.yaml`

```yaml
- fn_id: base.phasor_calibrate
  tool_id: tools.base
  name: Phasor calibration
  description: Calibrate raw phasor coordinates using a reference standard with known lifetime.
  tags: [image, transform, flim, phasor, calibration]
  inputs:
    - name: sample_phasors
      artifact_type: BioImageRef
      required: true
    - name: reference_phasors
      artifact_type: BioImageRef
      required: true
  outputs:
    - name: calibrated_phasors
      artifact_type: BioImageRef
      format: OME-TIFF
      required: true
  params_schema:
    type: object
    properties:
      lifetime:
        type: number
        description: Known lifetime of reference standard in nanoseconds
      frequency:
        type: number
        description: Laser repetition frequency in Hz
      harmonic:
        type: integer
        default: 1
        description: Harmonic number
    required: [lifetime, frequency]
```

### Task 4: Add bioio-bioformats

**File**: `envs/bioimage-mcp-base.yaml`

```yaml
dependencies:
  - python=3.13
  - pip
  - bioio
  - bioio-ome-zarr
  - bioio-ome-tiff
  - openjdk>=11        # NEW
  - scyjava            # NEW
  - numpy
  - scipy
  - scikit-image
  - phasorpy
  - numpydoc
  - pydantic>=2.0
  - pip:
    - -e .
    - bioio-bioformats  # NEW
```

**File**: `tools/base/bioimage_mcp_base/io.py`

```python
def load_image_fallback(path: Path) -> tuple[np.ndarray, list[dict], str]:
    """Load image with fallback chain.
    
    Returns:
        tuple: (data, warnings, reader_used)
    """
    warnings = []
    
    # 1. Try bioio-ome-tiff
    try:
        from bioio_ome_tiff import Reader as OmeTiffReader
        from bioio import BioImage
        img = BioImage(str(path), reader=OmeTiffReader)
        return img.get_image_data(), warnings, "bioio-ome-tiff"
    except Exception as e:
        warnings.append({"code": "OME_TIFF_FALLBACK", "message": str(e)})
    
    # 2. Try bioio-bioformats
    try:
        from bioio_bioformats import Reader as BioformatsReader
        from bioio import BioImage
        img = BioImage(str(path), reader=BioformatsReader)
        return img.get_image_data(), warnings, "bioio-bioformats"
    except Exception as e:
        warnings.append({"code": "BIOFORMATS_FALLBACK", "message": str(e)})
    
    # 3. Final fallback to tifffile
    import tifffile
    data = tifffile.imread(str(path))
    warnings.append({
        "code": "TIFFFILE_FALLBACK",
        "message": "Using tifffile - metadata may be incomplete"
    })
    return data, warnings, "tifffile"
```

## Validation

After implementation, verify the complete phasor workflow:

```python
# Example workflow test
from bioimage_mcp.api.discovery import DiscoveryService

# 1. Discovery works
discovery = DiscoveryService(conn)
tools = discovery.list_tools(limit=10, cursor=None)
assert "tools" in tools

# 2. Search works
results = discovery.search_functions(query="phasor", limit=10, cursor=None)
assert any(f["fn_id"] == "base.phasor_from_flim" for f in results["functions"])

# 3. Schema is complete
schema = discovery.describe_function("base.phasor_from_flim")
assert "params_schema" in schema or "schema" in schema
assert schema.get("schema", {}).get("properties", {}) != {}

# 4. Calibration is available
calibrate = discovery.describe_function("base.phasor_calibrate")
assert calibrate is not None
```

## Related Files

- **Spec**: `specs/006-phasor-usability-fixes/spec.md`
- **Research**: `specs/006-phasor-usability-fixes/research.md`
- **Data Model**: `specs/006-phasor-usability-fixes/data-model.md`
- **API Contract**: `specs/006-phasor-usability-fixes/contracts/api.yaml`

## Next Steps

After completing this quickstart:
1. Run `/speckit.tasks` to generate detailed task breakdown
2. Create PR with constitution check for code review
3. Update documentation in `docs/tutorials/flim_phasor.md`
