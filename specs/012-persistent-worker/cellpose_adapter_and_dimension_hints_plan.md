# Cellpose Adapter and Dimension Hints Plan

**Date**: 2026-01-02  
**Status**: Draft  
**Related Issues**: Validation report from `datasets/FLUTE_FLIM_data_tif/outputs/20260101_2253_test_validation_workflow.md`

---

## Executive Summary

This plan addresses two related issues:
1. **Cellpose adapter**: Enable dynamic dispatch for cellpose functions (currently fails with "No adapter found")
2. **Dimension hints**: Guide agents to preprocess 5D images before calling functions that expect 2D/3D input

Both solutions leverage the existing hints infrastructure in `FunctionHints` and `InputRequirement`.

---

## Part 1: Cellpose Adapter for Dynamic Dispatch

### Current State

**Problem**: Calling `cellpose.segment` fails with:
```
Error: "No adapter found for prefix: 'cellpose'"
```

**Root Cause**: 
- The `ADAPTER_REGISTRY` only contains: `phasorpy`, `scipy`, `skimage`, `xarray`
- Cellpose is defined as a static function in `tools/cellpose/manifest.yaml`
- When routing fails (e.g., env not installed), calls fall through to dynamic dispatch which has no cellpose adapter

### Design Goals

1. Enable dynamic discovery of cellpose functions via adapter pattern
2. Support multiple cellpose models (`cyto3`, `nuclei`, `cyto2`, etc.)
3. Introspect `CellposeModel.eval()` parameters for schema generation
4. Handle 5D TCZYX input normalization consistently

### Proposed Architecture

#### 1.1 CellposeAdapter Class

```python
# src/bioimage_mcp/registry/dynamic/adapters/cellpose.py

class CellposeAdapter(BaseAdapter):
    """Adapter for cellpose library functions."""
    
    # Functions to expose dynamically
    DISCOVERABLE_FUNCTIONS = {
        "cellpose.models": ["segment", "train"],
        "cellpose.denoise": ["denoise"],
    }
    
    # Model types for segment function
    MODEL_TYPES = ["cyto3", "cyto2", "cyto", "nuclei", "tissuenet", "livecell"]
    
    def __init__(self):
        self.introspector = Introspector()
    
    def discover(self, module_config: dict[str, Any]) -> list[FunctionMetadata]:
        """Discover cellpose functions from configured modules."""
        # Similar pattern to PhasorPyAdapter
        ...
    
    def resolve_io_pattern(self, func_name: str, signature: Any) -> IOPattern:
        """Resolve I/O pattern based on function name."""
        patterns = {
            "segment": IOPattern.IMAGE_TO_LABELS,
            "train": IOPattern.GENERIC,
            "denoise": IOPattern.IMAGE_TO_IMAGE,
        }
        return patterns.get(func_name, IOPattern.GENERIC)
    
    def execute(
        self,
        fn_id: str,
        inputs: list[Artifact],
        params: dict[str, Any],
        work_dir: Path | None = None,
    ) -> list[Artifact]:
        """Execute a cellpose function."""
        # 1. Load image with bioio (5D TCZYX)
        # 2. Squeeze/normalize for cellpose (2D/3D)
        # 3. Execute CellposeModel.eval() or other function
        # 4. Save outputs as OME-TIFF artifacts
        ...
```

#### 1.2 Adapter Registration

```python
# src/bioimage_mcp/registry/dynamic/adapters/__init__.py

def _populate_default_adapters() -> None:
    # ... existing adapters ...
    
    # Import cellpose adapter (optional - may not be installed)
    try:
        from bioimage_mcp.registry.dynamic.adapters.cellpose import CellposeAdapter
        ADAPTER_REGISTRY["cellpose"] = CellposeAdapter()
    except ImportError:
        pass  # cellpose not installed, skip adapter
```

#### 1.3 Manifest Update

```yaml
# tools/cellpose/manifest.yaml

dynamic_sources:
  - adapter: cellpose
    prefix: cellpose
    modules:
      - cellpose.models
      - cellpose.denoise
    include_patterns:
      - "segment"
      - "denoise"
    exclude_patterns:
      - "_*"
      - "test_*"

# Keep existing static function for backward compatibility
functions:
  - fn_id: cellpose.segment
    # ... existing definition ...
```

### Implementation Tasks

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| T101: Create `CellposeAdapter` class | P0 | 4h | None |
| T102: Register adapter in `__init__.py` | P0 | 0.5h | T101 |
| T103: Update cellpose manifest with `dynamic_sources` | P1 | 1h | T101 |
| T104: Add introspection for `CellposeModel.eval()` | P1 | 2h | T101 |
| T105: Write contract tests for adapter | P0 | 2h | T101 |
| T106: Write integration test with real cellpose | P1 | 2h | T101-T105 |

---

## Part 2: Dimension Hints for Agent Guidance

### Current State

**Problem**: Agents call skimage functions with 5D input, causing rank mismatch errors:
```
base.skimage.segmentation.felzenszwalb: Rank mismatch error on 5D input
```

**Existing Infrastructure**:
The schema already has `InputRequirement` with dimension-related fields:
```python
class InputRequirement(BaseModel):
    expected_axes: list[AxisName] | None = None  # e.g., ["Y", "X"]
    preprocessing_hint: str | None = None        # e.g., "Squeeze singleton dimensions"
```

These fields are NOT being populated or used effectively.

### Design Goals

1. Populate `expected_axes` and `preprocessing_hint` in function hints
2. Return hints in `describe_function` response
3. Provide actionable preprocessing instructions for agents
4. Support both static (manifest) and dynamic (adapter-generated) hints

### Proposed Schema Extensions

#### 2.1 Extended InputRequirement

```python
# src/bioimage_mcp/api/schemas.py

class DimensionRequirement(BaseModel):
    """Detailed dimension requirements for an input."""
    
    min_ndim: int | None = None        # Minimum dimensionality (e.g., 2)
    max_ndim: int | None = None        # Maximum dimensionality (e.g., 3)
    expected_axes: list[str] | None = None  # e.g., ["Y", "X"] or ["Z", "Y", "X"]
    spatial_axes: list[str] = ["Y", "X"]    # Which axes are spatial
    
    # Preprocessing hints for agent
    squeeze_singleton: bool = True     # Remove singleton dims automatically
    slice_strategy: str | None = None  # "first" | "middle" | "max_intensity" | None
    
    # Human-readable instructions for agent
    preprocessing_instructions: list[str] | None = None


class InputRequirement(BaseModel):
    """Schema for a single input requirement."""
    
    type: ArtifactType
    required: bool
    description: str
    expected_axes: list[AxisName] | None = None
    preprocessing_hint: str | None = None
    supported_storage_types: list[StorageType] | None = None
    
    # NEW: Detailed dimension requirements
    dimension_requirements: DimensionRequirement | None = None
```

#### 2.2 Adapter-Generated Hints

Each adapter can populate dimension hints during discovery:

```python
# In SkimageAdapter.discover()

def _generate_dimension_hints(self, module_name: str, func_name: str) -> dict:
    """Generate dimension hints based on function requirements."""
    
    # Functions known to require 2D input
    require_2d = {
        "threshold_otsu", "threshold_li", "threshold_triangle",
        "felzenszwalb", "slic", "quickshift",
    }
    
    # Functions known to require 2D or 3D input  
    require_2d_or_3d = {
        "gaussian", "sobel", "canny", "erosion", "dilation",
    }
    
    if func_name in require_2d:
        return {
            "dimension_requirements": {
                "min_ndim": 2,
                "max_ndim": 2,
                "expected_axes": ["Y", "X"],
                "squeeze_singleton": True,
                "preprocessing_instructions": [
                    "Squeeze singleton T, C, Z dimensions",
                    "If multiple channels, select one channel",
                    "If 3D, select a single Z slice",
                ]
            }
        }
    
    if func_name in require_2d_or_3d:
        return {
            "dimension_requirements": {
                "min_ndim": 2,
                "max_ndim": 3,
                "expected_axes": ["Y", "X"],  # or ["Z", "Y", "X"]
                "squeeze_singleton": True,
                "preprocessing_instructions": [
                    "Squeeze singleton T and C dimensions",
                    "Function supports 2D (YX) or 3D (ZYX) input",
                ]
            }
        }
    
    return {}
```

#### 2.3 Manifest-Based Hints (Static)

```yaml
# tools/base/manifest.yaml

function_overlays:
  base.skimage.segmentation.felzenszwalb:
    hints:
      inputs:
        image:
          type: BioImageRef
          required: true
          description: Input image for superpixel segmentation
          dimension_requirements:
            min_ndim: 2
            max_ndim: 3
            expected_axes: ["Y", "X"]
            squeeze_singleton: true
            preprocessing_instructions:
              - "Squeeze singleton T and C dimensions first"
              - "If 5D TCZYX, use base.xarray.squeeze or base.xarray.isel"
              - "For multichannel, convert to grayscale or select single channel"
      error_hints:
        RANK_MISMATCH:
          diagnosis: "Input has too many dimensions for this function"
          suggested_fix:
            fn_id: "base.xarray.squeeze"
            params: {}
            explanation: "Remove singleton dimensions before calling this function"
```

#### 2.4 describe_function Response Enhancement

The `describe_function` response will include dimension hints:

```json
{
  "fn_id": "base.skimage.segmentation.felzenszwalb",
  "schema": {
    "type": "object",
    "properties": {
      "scale": {"type": "number", "default": 1.0},
      "sigma": {"type": "number", "default": 0.8},
      "min_size": {"type": "integer", "default": 20}
    }
  },
  "inputs": {
    "image": {
      "type": "BioImageRef",
      "required": true,
      "description": "Input image for superpixel segmentation",
      "dimension_requirements": {
        "min_ndim": 2,
        "max_ndim": 3,
        "expected_axes": ["Y", "X"],
        "squeeze_singleton": true,
        "preprocessing_instructions": [
          "Squeeze singleton T and C dimensions first",
          "If 5D TCZYX, use base.xarray.squeeze or base.xarray.isel",
          "For multichannel, convert to grayscale or select single channel"
        ]
      }
    }
  },
  "hints": {
    "error_hints": {
      "RANK_MISMATCH": {
        "diagnosis": "Input has too many dimensions for this function",
        "suggested_fix": {
          "fn_id": "base.xarray.squeeze",
          "params": {},
          "explanation": "Remove singleton dimensions before calling this function"
        }
      }
    }
  }
}
```

### Agent Usage Pattern

When an agent receives dimension hints, it should:

1. **Before calling a function**: Check `dimension_requirements` in `describe_function` response
2. **If input has wrong dimensions**: Follow `preprocessing_instructions`
3. **Build preprocessing workflow**:

```python
# Agent decision logic (pseudocode)
fn_info = describe_function("base.skimage.segmentation.felzenszwalb")
dim_req = fn_info["inputs"]["image"]["dimension_requirements"]

if dim_req["max_ndim"] < input_artifact.ndim:
    # Need preprocessing
    if dim_req["squeeze_singleton"]:
        # First try squeeze
        result = run_function("base.xarray.squeeze", inputs={"image": input_ref})
        
    if result.ndim > dim_req["max_ndim"]:
        # Still too many dims - need to select slice
        instructions = dim_req["preprocessing_instructions"]
        # Agent can use instructions to decide which slice
        result = run_function("base.xarray.isel", inputs={"image": input_ref}, 
                             params={"T": 0, "C": 0})  # or agent's choice
```

### Implementation Tasks

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| T201: Add `DimensionRequirement` model | P0 | 1h | None |
| T202: Update `InputRequirement` schema | P0 | 0.5h | T201 |
| T203: Add dimension hint generation in SkimageAdapter | P0 | 3h | T201 |
| T204: Update manifest overlays for key functions | P1 | 2h | T202 |
| T205: Ensure describe_function returns dimension hints | P0 | 1h | T202 |
| T206: Write contract tests for dimension hints | P0 | 2h | T201-T205 |
| T207: Update docs with agent guidance patterns | P2 | 1h | T205 |

---

## Part 3: Combined Implementation Approach

### Phase 1: Dimension Hints (Week 1)

1. Extend `InputRequirement` with `DimensionRequirement`
2. Add dimension hint generation to existing adapters (skimage, phasorpy)
3. Update key function overlays in `tools/base/manifest.yaml`
4. Ensure `describe_function` returns hints
5. Write contract tests

### Phase 2: Cellpose Adapter (Week 2)

1. Create `CellposeAdapter` class
2. Register in adapter registry
3. Update cellpose manifest with `dynamic_sources`
4. Add dimension hints for cellpose functions
5. Write integration tests

### Test Strategy

```python
# tests/contract/test_dimension_hints.py

def test_describe_function_includes_dimension_hints():
    """describe_function returns dimension_requirements for skimage functions."""
    response = describe_function("base.skimage.segmentation.felzenszwalb")
    
    assert "inputs" in response
    assert "image" in response["inputs"]
    dim_req = response["inputs"]["image"].get("dimension_requirements")
    
    assert dim_req is not None
    assert dim_req["max_ndim"] <= 3
    assert "preprocessing_instructions" in dim_req


def test_cellpose_adapter_registered():
    """Cellpose adapter is registered when cellpose is installed."""
    from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY
    
    # Only if cellpose is installed
    try:
        import cellpose
        assert "cellpose" in ADAPTER_REGISTRY
    except ImportError:
        pytest.skip("cellpose not installed")


def test_cellpose_segment_via_dynamic_dispatch():
    """cellpose.segment can be called via dynamic dispatch."""
    # ...
```

---

## Summary

| Component | Solution | Files to Modify |
|-----------|----------|-----------------|
| Cellpose adapter | New `CellposeAdapter` class | `adapters/cellpose.py`, `adapters/__init__.py`, `tools/cellpose/manifest.yaml` |
| Dimension hints | Extend `InputRequirement`, populate in adapters | `api/schemas.py`, `adapters/skimage.py`, `tools/base/manifest.yaml`, `api/discovery.py` |

**Benefits**:
1. Agents can introspect dimension requirements before calling functions
2. Clear preprocessing instructions guide correct workflow construction
3. Error recovery via `error_hints` with suggested fixes
4. Cellpose works via dynamic dispatch even when env issues occur
