# Research: Axis Manipulation Tools, LLM Guidance Hints & Workflow Test Harness

**Date**: 2025-12-26  
**Spec**: [spec.md](./spec.md)

## Research Questions & Findings

### 1. Atomic Axis Relabeling Implementation

**Question**: How to implement atomic axis relabeling when mapping keys/values overlap (e.g., `{"Z":"T","T":"Z"}`)?

**Decision**: Apply mapping to axis string via single-pass character substitution.

**Rationale**:
- BioIO canonicalizes image dimensions to a 5D string (e.g., `"TCZYX"`)
- `OmeTiffWriter.save` accepts numpy array + `dim_order` string (not xarray)
- String substitution in one pass is inherently atomic - handles swaps without collision
- No data transposition needed - only metadata changes

**Implementation Pattern**:
```python
def relabel_axes(inputs: dict, params: dict, work_dir: Path) -> dict:
    image_ref = inputs.get("image")
    uri = image_ref.get("uri")
    mapping = params.get("axis_mapping")  # e.g., {"Z": "T", "T": "Z"}
    
    path = uri_to_path(str(uri))
    img = BioImage(str(path))
    data = img.get_image_data()
    original_axes = img.dims.order  # e.g., "TCZYX"
    
    # Atomic relabeling: map each character from original string
    # Handles simultaneous swaps correctly
    new_axes = "".join(mapping.get(axis, axis) for axis in original_axes)
    
    out_path = work_dir / "relabeled.ome.tiff"
    OmeTiffWriter.save(data, str(out_path), dim_order=new_axes)
    
    return {
        "outputs": {
            "output": {
                "type": "BioImageRef",
                "format": "OME-TIFF",
                "path": str(out_path),
                "metadata": {"axes": new_axes}
            }
        }
    }
```

**Alternatives Considered**:
- xarray.rename() - Rejected: OmeTiffWriter doesn't accept xarray objects
- Temporary intermediate names - Rejected: Unnecessary complexity

---

### 2. OME-TIFF Physical Size Metadata Preservation

**Question**: How to preserve physical_pixel_sizes across axis operations?

**Decision**: Explicitly reconstruct and pass `PhysicalPixelSizes` during write.

**Rationale**:
- bioio/tifffile treat data arrays and metadata separately during writes
- Transforming numpy array does not auto-update PhysicalPixelSizes
- OME-XML links physical sizes to logical axes (X=last, Y=second-to-last, Z=third-to-last)
- Must manually calculate new sizes based on transformation

**Key APIs**:
- **Read**: `bioio.BioImage.physical_pixel_sizes` -> `PhysicalPixelSizes` with `.X`, `.Y`, `.Z`
- **Construct**: `bioio_base.types.PhysicalPixelSizes(X=..., Y=..., Z=...)`
- **Write**: `OmeTiffWriter.save(..., physical_pixel_sizes=new_pps)`

**Implementation Pattern**:
```python
from bioio import BioImage
from bioio.writers import OmeTiffWriter
from bioio_base.types import PhysicalPixelSizes

# Read
img = BioImage("input.ome.tif")
data = img.get_image_data()
pps = img.physical_pixel_sizes

# For axis swap (e.g., X <-> Y)
new_data = data.swapaxes(-1, -2)
new_pps = PhysicalPixelSizes(X=pps.Y, Y=pps.X, Z=pps.Z)

# For squeeze (removing Z)
new_pps = PhysicalPixelSizes(X=pps.X, Y=pps.Y, Z=None)

# For expand_dims (adding new axis)
# New axis gets None (unknown physical size per spec)
new_pps = PhysicalPixelSizes(X=pps.X, Y=pps.Y, Z=None)

# Write
OmeTiffWriter.save(new_data, "output.ome.tif", physical_pixel_sizes=new_pps)
```

**Alternatives Considered**:
- Implicit metadata propagation - Rejected: Not supported by writers
- Storing metadata in sidecar files - Rejected: Adds complexity, breaks OME standard

---

### 3. Mock Executor Design for Test Harness

**Question**: Where to inject mocks in the test harness?

**Decision**: Mock at `execute_step` function level in `bioimage_mcp.api.execution`.

**Rationale**:
1. **Clean Boundary**: `execute_step` sits between orchestration and subprocess execution
2. **Identity-based Mocking**: Function receives `fn_id`, `params`, `inputs` - easy per-tool mocks
3. **Artifact Flow Integration**: Mocks write fake files to `work_dir`, allowing ExecutionService to test artifact importing, metadata extraction, provenance recording
4. **Environment Independence**: Bypasses micromamba/conda and tool entrypoints
5. **Proven Pattern**: Already used successfully in `tests/integration/test_mcp_llm_simulation.py`

**Implementation Pattern**:
```python
def _create_mock_executor(mock_registry: dict):
    def _mock_execute_step(*, fn_id, work_dir, inputs, params, **kwargs):
        if fn_id in mock_registry:
            return mock_registry[fn_id](work_dir=work_dir, inputs=inputs, params=params)
        # Default: successful no-op
        return {"ok": True, "outputs": {}}, "Mock execution successful", 0
    return _mock_execute_step

# Usage in tests
def test_workflow(tmp_path, monkeypatch):
    def relabel_mock(work_dir, **kwargs):
        out_path = work_dir / "relabeled.ome.tiff"
        out_path.write_bytes(b"MOCK_TIFF_DATA")
        return {
            "ok": True,
            "outputs": {"image": {"type": "BioImageRef", "path": str(out_path)}}
        }, "Log: relabeled axes", 0

    mock_registry = {"base.relabel_axes": relabel_mock}
    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        _create_mock_executor(mock_registry)
    )
    # Run workflow through real ExecutionService
```

**Configurability**:
- Per-test: Use `monkeypatch` for isolation
- Per-tool: MCPTestClient maintains internal `mock_registry` dict
- Validation: Run `ExecutionService.validate_workflow` even in mock mode

**Alternatives Considered**:
- Mock subprocess calls - Rejected: Too low-level, misses orchestration bugs
- Mock runtime dispatcher - Rejected: Less clean boundary, harder to configure per-tool
- Persistent worker processes with IPC - Rejected: Overkill for testing

---

### 4. YAML Test Case Schema

**Question**: What schema for data-driven workflow test cases?

**Decision**: Step-based YAML with explicit `step_id` references for artifact passing.

**Rationale**:
1. **Declarative Orchestration**: Test harness executes steps one at a time, managing state
2. **Explicit Data Flow**: `{step_id.output}` syntax makes dependencies clear (inspired by GitHub Actions)
3. **Integrated Assertions**: Per-step assertions enable fail-fast behavior
4. **Pytest Compatibility**: Easy to load via `pytest_generate_tests` hook

**Schema Structure**:
```yaml
test_name: string  # Unique test identifier
description: string  # Human-readable description
steps:
  - step_id: string  # Unique within test, used for references
    fn_id: string  # Tool function ID (e.g., "base.relabel_axes")
    inputs:
      <input_name>: string | object  # File path or {step_id.output} reference
    params:
      <param_name>: any  # Tool parameters
    assertions:
      - type: string  # "artifact_exists" | "output_type" | "metadata_check"
        key: string?  # For metadata_check
        value: any?  # Expected value
```

**Example Test Case** (`tests/integration/workflow_cases/flim_phasor.yaml`):
```yaml
test_name: "flim_phasor_golden_path"
description: "End-to-end FLIM phasor workflow with axis relabeling"

steps:
  - step_id: "fix_axes"
    fn_id: "base.relabel_axes"
    inputs:
      image: "datasets/FLUTE_FLIM_data_tif/Embryo.tif"
    params:
      axis_mapping:
        Z: "T"
        T: "Z"
    assertions:
      - type: "output_type"
        value: "BioImageRef"
      - type: "metadata_check"
        key: "axes"
        value: "TCZYX"

  - step_id: "compute_phasor"
    fn_id: "base.phasor_from_flim"
    inputs:
      dataset: "{fix_axes.output}"  # Reference previous step output
    params:
      harmonic: 1
    assertions:
      - type: "artifact_exists"
      - type: "output_type"
        value: "BioImageRef"
```

**Implementation Strategy**:
1. Loader in `conftest.py` reads YAML files via glob
2. Runner iterates through steps, executing via MCPTestClient
3. Context dict stores results: `context['fix_axes.output'] = artifact_ref`
4. Substitution: Scan inputs/params for `{...}` strings, replace from context

**Alternatives Considered**:
- Implicit "last output" passing - Rejected: Unclear for complex workflows
- JSON Schema validation - Deferred: Add later if needed for strictness
- DSL for assertions - Rejected: Keep simple with type-based assertion handlers

---

## Summary of Decisions

| Unknown | Decision | Key API/Pattern |
|---------|----------|-----------------|
| Atomic axis relabeling | Single-pass string substitution | `"".join(mapping.get(axis, axis) for axis in original_axes)` |
| Physical size preservation | Explicit PhysicalPixelSizes reconstruction | `PhysicalPixelSizes(X=..., Y=..., Z=...)` |
| Mock executor level | Mock `execute_step` function | `monkeypatch.setattr("...execution.execute_step", ...)` |
| YAML test schema | Step-based with `{step_id.output}` references | `inputs: {previous.output}` syntax |

All NEEDS CLARIFICATION items have been resolved.
