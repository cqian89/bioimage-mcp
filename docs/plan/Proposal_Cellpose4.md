# Feature Specification: Spec 017: Cellpose 4 (Cellpose-SAM) Integration

**Feature Branch**: `017-cellpose4`  
**Created**: 2026-01-06  
**Status**: Draft  
**Spec**: `specs/017-cellpose4/proposal.md`

## Clarifications

**Q: Should we maintain backward compatibility with CP3?**  
A: Yes, but via separate tool packs. `bioimage-mcp-cellpose` (CP3) and `bioimage-mcp-cellpose4` (CP4) will coexist as independent environments. This avoids dependency hell (CP4 requires newer PyTorch/Torchvision).

**Q: How to handle the deprecated `styles` output in CP4?**  
A: CP4's universal model does not produce the same style vector as CP3. The adapter will return an empty/zero array for the style artifact to maintain schema consistency with existing downstream tools, but will mark it as deprecated in metadata.

**Q: Should we auto-detect GPU availability?**  
A: Yes. The adapter will introspect the environment at runtime to determine if CUDA or MPS (Metal) is available and set the default `use_gpu` value accordingly.

**Q: Is the `channels` parameter still relevant?**  
A: CP4 marks it as deprecated for the universal `cpsam` model (which is often grayscale/RGB-agnostic), but it is still used internally for preprocessing. We will keep it but make it optional with smart defaults.

## 1. Overview

### Problem Statement
Cellpose 4.0 (Cellpose-SAM / CP4) introduces a universal transformer-based model (`cpsam`) that replaces the specialized models from Cellpose 3 (CP3). The CP4 API has significant breaking changes:
1.  **Class Hierarchy**: Removal of the `Cellpose` class in favor of `CellposeModel`.
2.  **Parameter Changes**: Deprecation of `channels` for universal models, addition of `use_bfloat16` for memory optimization, and new normalization strategies.
3.  **Dependency Conflict**: CP4 requires `torch>=2.0`, which conflicts with some legacy environments.

The current `bioimage-mcp` implementation is hardcoded for CP3-style models and parameter sets, making it incompatible with the latest version.

### Goal
Integrate Cellpose 4 into the `bioimage-mcp` ecosystem while maintaining isolated execution environments. This involves creating a new tool pack environment, updating the dynamic adapter to handle CP4's signature, and providing a seamless migration path for users through version-aware introspection.

## 2. User Scenarios & Testing

### User Story 1 - Universal Segmentation (Priority: P1)
As a biologist, I want to segment a diverse set of images (cells, nuclei, organelles) using a single "foundation model" without having to tune model types or channel settings manually.

**Why this priority**: This is the primary value proposition of Cellpose 4. It simplifies the user experience by providing a "one size fits all" starting point.

**Independent Test**: Can be tested by running `cellpose.eval` on a multi-channel TIFF using the `cpsam` model and verifying that masks are produced for both cytoplasm and nuclei without specifying `model_type`.

**Acceptance Scenarios**:
1.  **Given** a user has a 2-channel fluorescence image, **When** they call `cellpose.eval` in the CP4 environment without a `model_type`, **Then** the system defaults to `cpsam` and produces a valid `LabelImageRef`.
2.  **Given** a user provides `channels: [2, 3]` to CP4, **When** the inference runs, **Then** the system logs a deprecation warning but correctly uses the channels for pre-processing.

---

### User Story 2 - Memory-Efficient Large Image Processing (Priority: P1)
As a power user, I want to process large 3D volumes or high-resolution slides on consumer-grade GPUs by leveraging CP4's memory optimization features.

**Why this priority**: Memory exhaustion is the #1 failure mode for deep learning tools in bioimaging. `bfloat16` support is a critical fix for this.

**Independent Test**: Monitor GPU VRAM usage during two identical runs, one with `use_bfloat16: true` and one with `false`.

**Acceptance Scenarios**:
1.  **Given** a GPU with 8GB VRAM and a 2048x2048x50 Z-stack, **When** `use_bfloat16: true` is set, **Then** the segmentation completes without OOM (Out of Memory) errors.
2.  **Given** `use_bfloat16: true` is requested on a hardware platform that doesn't support it (e.g., older NVIDIA cards), **When** the adapter initializes, **Then** it gracefully falls back to float32 and logs a warning.

---

### User Story 3 - Legacy Parameter Handling (Priority: P2)
As a user migrating from CP3, I want my existing scripts or workflows to work with the CP4 tool pack without immediate failure.

**Why this priority**: Prevents breaking existing user workflows and provides a smooth transition period.

**Independent Test**: Call CP4 `cellpose.eval` with `model_type: "cyto3"`.

**Acceptance Scenarios**:
1.  **Given** a workflow expects `model_type: "cyto3"`, **When** executed against the CP4 tool pack, **Then** the adapter maps "cyto3" to "cpsam", issues a logged warning, and continues execution.
2.  **Given** a user provides a parameter that was removed in CP4 (e.g., `styles`), **When** the tool is described, **Then** the parameter is marked as `deprecated: true` in the JSON Schema.

---

### Edge Cases
- **No GPU detected**: System must fall back to CPU and set `use_gpu: false` automatically.
- **Incompatible PyTorch version**: If the user manually pollutes the environment, `meta.describe` should report a health-check failure.
- **Corrupt Model Download**: CP4 downloads models on first run; if this fails (no internet), the tool should return a structured error with a hint to check connectivity.
- **Empty Image**: Passing a blank image should return an empty LabelImageRef rather than crashing.

## 3. Requirements

### 3.1 Constitution Constraints
- **Isolation**: CP4 MUST run in a dedicated `bioimage-mcp-cellpose4` conda environment.
- **Reproducibility**: Environment pinned via `envs/bioimage-mcp-cellpose4.lock.yml`. Artifacts MUST include model version and inference params in provenance metadata.
- **Discovery**: The adapter MUST use dynamic introspection (`inspect` module) to discover parameters, as CP4.x is evolving rapidly.

### 3.2 Functional Requirements

#### Environment & Integration
- **FR-001**: Create a new tool pack environment definition for Cellpose 4 (Python 3.12+, Torch 2.x).
- **FR-002**: Implement a version-aware `CellposeAdapter` that forks logic for CP < 4.0 and CP >= 4.0.
- **FR-015**: Support parallel tool pack installation (both `cellpose` and `cellpose4` can be active simultaneously).

#### Discovery & Metadata
- **FR-003**: Dynamic parameter discovery for `CellposeModel.eval`. Filter out legacy parameters like `diam_mean` if using universal models.
- **FR-007**: Implement runtime introspection via `meta.describe` to fetch live parameter schemas from the CP4 environment.
- **FR-008**: Log deprecation warnings when CP3-style parameters (e.g., `model_type="cyto2"`) are used with CP4.
- **FR-014**: Output artifact metadata MUST include model version, inference parameters, and hardware used (GPU/CPU) in the provenance record.

#### Processing Features
- **FR-004**: Explicitly expose CP4-specific parameters: `use_bfloat16`, `invert`, and `tile`.
- **FR-009**: Support the `normalize` parameter (dictionary or boolean) for advanced intensity scaling.
- **FR-010**: Support `do_3D` parameter for Z-stack segmentation, ensuring the adapter handles 3D artifacts correctly.
- **FR-013**: Handle errors for unsupported operations (e.g., if a specific CP4 model doesn't support 3D).

#### Quality & Validation
- **FR-011**: Contract tests for CP4 adapter validating that the generated JSON Schema matches CP4 signatures.
- **FR-012**: Integration tests using real CP4 inference on a sample dataset (e.g., `datasets/FLUTE_FLIM_data_tif/`).

## 4. Configuration Examples

### 4.1 Manifest Example (`tools/cellpose4/manifest.yaml`)
```yaml
tool_pack:
  id: bioimage-mcp-cellpose4
  version: "0.4.0"
  environment:
    name: bioimage-mcp-cellpose4
    lockfile: envs/bioimage-mcp-cellpose4.lock.yml

functions:
  - id: cellpose.eval
    summary: Universal cell segmentation using Cellpose 4 (Cellpose-SAM)
    adapter: cellpose
    config:
      module_name: "cellpose.models.CellposeModel"
      default_model: "cpsam"
    inputs:
      - name: image
        type: BioImageRef
    outputs:
      - name: mask
        type: LabelImageRef
      - name: styles
        type: BioImageRef
        deprecated: true
```

### 4.2 Environment Definition (`envs/bioimage-mcp-cellpose4.yml`)
```yaml
name: bioimage-mcp-cellpose4
channels:
  - pytorch
  - nvidia
  - conda-forge
dependencies:
  - python=3.12
  - pytorch>=2.4
  - torchvision
  - pytorch-cuda=12.1 # for GPU support
  - cellpose>=4.0.0
  - bioio
  - bioio-ome-tiff
  - pydantic>=2.0
```

### 4.3 Version-Aware Adapter Logic (Conceptual)
```python
def _introspect_cp4(self, cls_obj):
    import inspect
    from cellpose import version_str
    
    sig = inspect.signature(cls_obj.eval)
    params = {}
    
    for name, param in sig.parameters.items():
        if name in ["x", "self"]: continue
        
        # Mapping CP4 types to JSON Schema
        p_type = "string"
        if param.annotation == bool: p_type = "boolean"
        elif param.annotation in [int, float]: p_type = "number"
        
        params[name] = {
            "type": p_type,
            "default": param.default if param.default is not inspect._empty else None
        }
    
    # Force injection of CP4 specific flags if not found
    if "use_bfloat16" not in params:
        params["use_bfloat16"] = {"type": "boolean", "default": False}
        
    return params
```

## 5. Key Entities & Abstractions

### 5.1 Parameter Filtering Strategies
Since CP4's `eval` method contains many internal/debugging parameters, the adapter applies filtering:
- **Exclude**: `batch_size` (managed by server), `interp` (internal), `logger` (internal).
- **Include**: `diameter`, `flow_threshold`, `cellprob_threshold`, `normalize`, `use_bfloat16`.

### 5.2 Schema Transformation Rules
- **Boolean mapping**: Parameters ending in `_gpu`, `_3d`, `_bfloat16` are strictly typed as `boolean`.
- **Model Aliasing**: The `model_type` parameter is transformed into an Enum containing both new CP4 models (`cpsam`, `cyto3`) and legacy aliases.

### 5.3 Version Detection Logic
The adapter executes `cellpose.__version__` inside the tool's environment during the registration phase. This version is cached in the `Registry` to avoid repeated subprocess calls.

## 6. Success Criteria

- **SC-001**: `list` tool shows `cellpose.eval` from the `bioimage-mcp-cellpose4` pack.
- **SC-002**: Successful segmentation of a test image using the `cpsam` model with default parameters.
- **SC-003**: GPU VRAM usage is at least 30% lower when `use_bfloat16: true` is enabled (for supported hardware).
- **SC-004**: Contract tests verify that `model_type` is no longer a required parameter in CP4.
- **SC-005**: 3D segmentation of a 5D OME-TIFF artifact produces a 3D LabelImageRef.
- **SC-006**: All dynamically discovered parameters have non-empty `description` fields (inferred from docstrings if possible).
- **SC-007**: No regression in CP3 tool pack functionality (verified by running legacy integration tests).
- **SC-008**: Startup time increase for dynamic discovery is `< 1s` compared to CP3.

## 7. Implementation Plan

### Phase 1: Environment & Tool Pack
1.  Generate `envs/bioimage-mcp-cellpose4.lock.yml`.
2.  Setup `tools/cellpose4/` with the new manifest.

### Phase 2: Adapter Evolution
1.  Refactor `CellposeAdapter` to support multi-version introspection.
2.  Implement the CP4 `CellposeModel` runner.
3.  Add the `bfloat16` hardware check logic.

### Phase 3: Testing & Provenance
1.  Add CP4-specific integration tests.
2.  Update `RunRecord` logic to include CP version and model hashes.

## 8. Assumptions & Risks
- **Risk**: CP4 models are large (>500MB); the first execution will be slow due to download.
- **Mitigation**: Add a "model warming" step in the `doctor` command to pre-download models.
- **Assumption**: Users have updated GPU drivers compatible with Torch 2.4+.
