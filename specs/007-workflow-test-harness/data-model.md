# Data Model: Axis Manipulation Tools, LLM Guidance Hints & Workflow Test Harness

**Date**: 2025-12-26  
**Spec**: [spec.md](./spec.md)

## Entity Overview

This feature introduces 4 new entity types and extends 2 existing ones:

| Entity | Type | Location | Purpose |
|--------|------|----------|---------|
| AxisMapping | Value Object | params | Maps old axis names to new axis names |
| AxisToolParams | Pydantic Models | params | Per-tool parameter schemas |
| LLMHints | Pydantic Model | manifest + responses | Workflow guidance for LLMs |
| WorkflowTestCase | Pydantic Model | test harness | YAML-defined test definitions |
| ArtifactRef.metadata | Extension | artifacts/models.py | Extended with axes, shape, dtype fields |
| FunctionDef.hints | Extension | manifest.yaml | Per-function hint definitions |

---

## Entity Definitions

### 1. AxisMapping (Value Object)

Dictionary mapping source axis names to target axis names.

```python
# Type alias - not a separate class
AxisMapping = dict[str, str]

# Examples
{"Z": "T", "T": "Z"}  # Swap Z and T
{"Y": "Z", "Z": "Y"}  # Swap Y and Z
{"C": "T"}            # Relabel C as T
```

**Constraints**:
- Keys must exist in input image axes
- Mapping applied atomically (single-pass substitution)
- Result must not have duplicate axis names
- Case-sensitive (Z != z)

---

### 2. AxisToolParams (Pydantic Models)

Parameter schemas for each axis manipulation tool.

```python
from pydantic import BaseModel, Field
from typing import Literal

class RelabelAxesParams(BaseModel):
    """Parameters for base.relabel_axes"""
    axis_mapping: dict[str, str] = Field(
        ...,
        description="Mapping from old axis names to new names (e.g., {'Z': 'T', 'T': 'Z'})"
    )

class SqueezeParams(BaseModel):
    """Parameters for base.squeeze"""
    axis: int | str | None = Field(
        None,
        description="Axis to squeeze (int index or str name). If None, squeeze all singleton axes."
    )

class ExpandDimsParams(BaseModel):
    """Parameters for base.expand_dims"""
    axis: int = Field(
        ...,
        description="Position to insert new axis (0=first, -1=before last)"
    )
    new_axis_name: str = Field(
        ...,
        description="Name for the new axis (single uppercase letter: T, C, Z, etc.)"
    )

class MoveAxisParams(BaseModel):
    """Parameters for base.moveaxis"""
    source: int | str = Field(
        ...,
        description="Source axis (index or name)"
    )
    destination: int = Field(
        ...,
        description="Destination position (index)"
    )

class SwapAxesParams(BaseModel):
    """Parameters for base.swap_axes"""
    axis1: int | str = Field(
        ...,
        description="First axis to swap (index or name)"
    )
    axis2: int | str = Field(
        ...,
        description="Second axis to swap (index or name)"
    )
```

---

### 3. LLMHints (Pydantic Models)

Structured hints for LLM workflow guidance.

```python
from pydantic import BaseModel, Field
from typing import Optional

class InputRequirement(BaseModel):
    """Schema for a single input requirement"""
    type: str  # Artifact type: BioImageRef, LabelImageRef, etc.
    required: bool = True
    description: str
    expected_axes: list[str] | None = None  # e.g., ["T", "Y", "X"]
    preprocessing_hint: str | None = None
    supported_storage_types: list[str] | None = None  # e.g., ["zarr-temp", "file"]

class OutputDescription(BaseModel):
    """Schema for a single output description"""
    type: str  # Artifact type
    description: str

class NextStepHint(BaseModel):
    """Suggested next step in workflow"""
    fn_id: str
    reason: str
    required_inputs: list[str] | None = None

class SuggestedFix(BaseModel):
    """Suggested fix for an error"""
    fn_id: str
    params: dict
    explanation: str

class SuccessHints(BaseModel):
    """Hints returned on successful execution"""
    next_steps: list[NextStepHint] = Field(default_factory=list)
    common_issues: list[str] = Field(default_factory=list)

class ErrorHints(BaseModel):
    """Hints returned on error"""
    diagnosis: str | None = None
    suggested_fix: SuggestedFix | None = None
    related_metadata: dict | None = None  # detected_axes, shape, ome_hint

class FunctionHints(BaseModel):
    """Hints defined per-function in manifest.yaml"""
    inputs: dict[str, InputRequirement] = Field(default_factory=dict)
    outputs: dict[str, OutputDescription] = Field(default_factory=dict)
    success_hints: SuccessHints | None = None
    error_hints: dict[str, ErrorHints] = Field(default_factory=dict)  # keyed by error code
```

---

### 4. WorkflowTestCase (Pydantic Models)

Test case definitions loaded from YAML.

```python
from pydantic import BaseModel, Field
from typing import Any, Literal

class StepAssertion(BaseModel):
    """Single assertion for a test step"""
    type: Literal["artifact_exists", "output_type", "metadata_check"]
    key: str | None = None  # For metadata_check
    value: Any = None  # Expected value

class WorkflowStep(BaseModel):
    """Single step in a workflow test"""
    step_id: str
    fn_id: str
    inputs: dict[str, str | dict] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    assertions: list[StepAssertion] = Field(default_factory=list)

class WorkflowTestCase(BaseModel):
    """Complete workflow test case loaded from YAML"""
    test_name: str
    description: str
    steps: list[WorkflowStep]

# Context for step execution
class StepContext(BaseModel):
    """Runtime context tracking step outputs"""
    outputs: dict[str, dict] = Field(default_factory=dict)  # step_id -> artifact_ref
    
    def resolve_reference(self, ref: str) -> dict:
        """Resolve {step_id.output} reference to artifact ref"""
        if not ref.startswith("{") or not ref.endswith("}"):
            return {"uri": f"file://{ref}"}  # Literal file path
        
        inner = ref[1:-1]  # Remove braces
        step_id, output_name = inner.rsplit(".", 1)
        return self.outputs[step_id]
```

---

### 5. Extended ArtifactRef.metadata

Extending the existing metadata dict in `ArtifactRef` (additive, backward-compatible schema extension).

```python
# In artifacts/models.py - metadata dict gets these additional keys

class ArtifactMetadata:
    """Structure of metadata dict for BioImageRef artifacts"""
    
    # Required fields (FR-020)
    shape: list[int]       # e.g., [1, 1, 56, 512, 512]
    dtype: str             # e.g., "uint16", "float32"
    axes: str              # e.g., "TCZYX"
    
    # Optional fields
    axes_inferred: bool    # True if axes were guessed (FR-021)
    physical_pixel_sizes: dict   # {"X": 1.179, "Y": 1.179, "Z": None}
    
    # File metadata (FR-022)
    file_metadata: dict | None
    # Contains:
    #   ome_xml_summary: str  # Truncated if >1KB
    #   custom_attributes: dict  # Vendor-specific metadata

# Example metadata in artifact response
{
    "ref_id": "abc123",
    "type": "BioImageRef",
    "uri": "file:///tmp/bioimage-mcp/.../output.ome.tiff",
    "format": "OME-TIFF",
    "metadata": {
        "shape": [1, 1, 56, 512, 512],
        "dtype": "uint16",
        "axes": "TCZYX",
        "axes_inferred": false,
        "physical_pixel_sizes": {"X": 1.179, "Y": 1.179, "Z": None},
        "file_metadata": {
            "ome_xml_summary": "FLIM TCSPC data, 56 time bins",
            "custom_attributes": {"FirstAxis": "DC-TCSPC T"}
        }
    }
}
```

---

### 6. Extended FunctionDef.hints (manifest.yaml)

Adding `hints` field to function definitions in manifest.yaml.

```yaml
functions:
  - fn_id: base.phasor_from_flim
    tool_id: tools.base
    name: Phasor transform
    description: Convert FLIM dataset to phasor coordinates
    tags: [image, transform, flim, phasor]
    
    # Existing fields
    inputs:
      - name: dataset
        artifact_type: BioImageRef
        required: true
    outputs:
      - name: g_image
        artifact_type: BioImageRef
        format: OME-TIFF
        required: true
    params_schema:
      type: object
      properties:
        time_axis:
          type: [string, integer]
        harmonic:
          type: integer
          default: 1
    
    # NEW: hints field for LLM guidance
    hints:
      inputs:
        dataset:
          expected_axes: ["T", "Y", "X"]
          preprocessing_hint: "If T has only 1 sample, check if FLIM bins are in Z axis"
          supported_storage_types: ["file"]
      outputs:
        g_image:
          description: "Phasor G coordinates (real component)"
        s_image:
          description: "Phasor S coordinates (imaginary component)"
      success_hints:
        next_steps:
          - fn_id: base.phasor_calibrate
            reason: "Apply calibration using reference standard"
            required_inputs: ["reference dataset with known lifetime"]
        common_issues:
          - "Raw phasors are uncalibrated - use phasor_calibrate for quantitative analysis"
      error_hints:
        AXIS_SAMPLES_ERROR:
          diagnosis: "The T axis has only 1 sample. FLIM time bins may be stored in Z dimension."
          suggested_fix:
            fn_id: base.relabel_axes
            params:
              axis_mapping: {"Z": "T", "T": "Z"}
            explanation: "Relabel Z axis as T to treat Z slices as FLIM time bins"
```

---

## State Transitions

### Axis Tool Execution Flow

```
Input BioImageRef
    │
    ▼
┌─────────────────────┐
│ Validate parameters │
│ - Check axis exists │
│ - Check no dups     │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Load image data     │
│ - BioImage.read()   │
│ - Extract axes str  │
│ - Extract phys size │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Apply axis operation│
│ - relabel: string   │
│ - squeeze: np ops   │
│ - moveaxis: np ops  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Update metadata     │
│ - New axes string   │
│ - New phys sizes    │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Write output        │
│ - OmeTiffWriter     │
│ - With updated meta │
└─────────────────────┘
    │
    ▼
Output BioImageRef
```

### Workflow Test Execution Flow

```
Load YAML test case
    │
    ▼
┌─────────────────────┐
│ Initialize context  │
│ context = {}        │
└─────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ For each step in test:      │
│   1. Resolve {ref} inputs   │
│   2. Call MCPTestClient     │
│   3. Store output in context│
│   4. Check assertions       │
│   5. Fail-fast if error     │
└─────────────────────────────┘
    │
    ▼
Test result (pass/fail)
```

---

## Validation Rules

### AxisMapping Validation

| Rule | Condition | Error Message |
|------|-----------|---------------|
| Keys exist | All keys in input axes | "Axis {key} not found in image with axes {axes}" |
| No duplicates | len(set(new_axes)) == len(new_axes) | "Cannot relabel {old} to {new}: axis {new} already exists" |
| Valid names | All values are single uppercase letters | "Invalid axis name '{name}': must be single uppercase letter" |

### SqueezeParams Validation

| Rule | Condition | Error Message |
|------|-----------|---------------|
| Axis exists | axis in range or axis in axes | "Axis {axis} not found" |
| Is singleton | shape[axis] == 1 | "Cannot squeeze axis {name} (index {idx}) with size {size} > 1" |
| Has singletons | Any shape[i] == 1 (if axis=None) | "No singleton axes to squeeze" |

### ExpandDimsParams Validation

| Rule | Condition | Error Message |
|------|-----------|---------------|
| Valid position | -ndim-1 <= axis <= ndim | "Axis position {axis} out of bounds for {ndim}D array" |
| Name unique | new_axis_name not in current axes | "Axis name {name} already exists in axes {axes}" |
| Valid name | len(name)==1 and name.isupper() | "Invalid axis name '{name}'" |

---

## Relationships

```
┌──────────────────┐     uses      ┌──────────────────┐
│  MCPTestClient   │──────────────▶│  ExecutionService│
└──────────────────┘               └──────────────────┘
        │                                   │
        │ loads                             │ creates
        ▼                                   ▼
┌──────────────────┐               ┌──────────────────┐
│ WorkflowTestCase │               │   ArtifactRef    │
│   (from YAML)    │               │ (with metadata)  │
└──────────────────┘               └──────────────────┘
        │                                   ▲
        │ contains                          │
        ▼                                   │
┌──────────────────┐     produces  ┌──────────────────┐
│  WorkflowStep    │──────────────▶│  Axis Tool Fn    │
│  (fn_id, params) │               │ (relabel, etc.)  │
└──────────────────┘               └──────────────────┘
                                            │
                                            │ returns
                                            ▼
                                   ┌──────────────────┐
                                   │   LLMHints       │
                                   │ (next_steps,etc) │
                                   └──────────────────┘
```
