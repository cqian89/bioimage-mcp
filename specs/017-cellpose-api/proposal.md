# Feature Specification: Cellpose Class-Based API & ObjectRef

**Feature Branch**: `017-cellpose-api`  
**Created**: 2026-01-06  
**Status**: Draft  
**Input**: Revise original Cellpose API proposal to use `ObjectRef`, correct module paths, and prioritize introspectable class-method APIs.

## Executive Summary

Bioimage analysis workflows increasingly rely on deep learning models (e.g., Cellpose, StarDist) that require expensive initialization (loading weights, GPU allocation). The current Bioimage-MCP architecture excels at static function execution but lacks a first-class mechanism for model persistence across multiple calls within a session.

This specification introduces:
1. **`ObjectRef`**: A generic artifact type for in-memory Python objects (models, networks) that can be serialized/pickled and reused across function calls.
2. **Class-Based Execution**: Support for calling methods on instantiated objects (e.g., `CellposeModel.eval`) rather than just module-level functions.
3. **Corrected Cellpose Integration**: A prioritized set of introspectable Cellpose APIs using their actual Python module paths, enabling robust discovery and execution.

## Current State Analysis

Currently, all tools are executed as isolated subprocesses. While this provides excellent fault isolation, it imposes a "cold start" penalty for ML tools:
- A `cellpose.segment` call must load the model weights from disk every time.
- There is no way to pass an "already-trained" or "already-loaded" model between steps.
- The `dynamic_sources` registry only looks for functions, not class methods.
- Artifact types are limited to data (BioImage, Table, etc.), not computation state (Models).

## Gap Analysis

1. **State Persistence**: No mechanism to return a `Model` or `Net` from one tool and use it in another.
2. **Path Accuracy**: Previous proposals used incorrect paths (e.g., `cellpose.cellpose.CellposeModel.eval` instead of `cellpose.models.CellposeModel.eval`).
3. **Introspectability**: Some common Cellpose APIs (like `Cellpose.eval`) use `**kwargs`, making it impossible for the MCP registry to automatically generate a valid JSON Schema for parameters.
4. **Training Support**: `cellpose.train.train_seg` requires a network object as an argument, which cannot be represented by current artifact types.
5. **Checkpoint-to-Disk Pattern**: `cellpose.train.train_seg` follows a "checkpoint-to-disk" pattern. Unlike most methods that return in-memory objects, training saves state to a `.pth` file. This ensures that large models aren't held in memory unnecessarily after training and provides a clear path for model versioning.

| API Component | Coverage | Notes |
|---------------|----------|-------|
| `cellpose.models.CellposeModel.eval` | Target | Explicit signature |
| `cellpose.models.Cellpose.eval` | Excluded | Uses **kwargs |
| `cellpose.denoise.DenoiseModel.eval` | Target | Explicit signature |
| `cellpose.denoise.CellposeDenoiseModel.eval` | Excluded | Uses **kwargs |
| `cellpose.train.train_seg` | Target | Requires ObjectRef for `net` |
| `cellpose.metrics.*` | Target | Pure functions |

## Proposed Architecture

### 1. `ObjectRef` Artifact Type
We introduce a new artifact type `ObjectRef` to represent serialized Python objects.
- **MIME Type**: `application/x-python-pickle` (or tool-specific serialization).
- **Metadata**: Includes `python_class` (e.g., `cellpose.models.CellposeModel`) and `device` (cpu/cuda).
- **Storage**: Objects are persisted as files in the artifact store. This ensures compatibility with the existing subprocess model while allowing reuse across calls.
- **URI Format**: `obj://session_id/env_id/instance_id` for session-scoped references.

### 2. Class-Based Execution Architecture
One major challenge in exposing class methods as MCP tools is the split between constructor parameters (`__init__`) and method parameters (e.g., `eval`). 

#### Init vs Method Parameters
We solve this by introducing a `class_config` in the manifest overlays that explicitly lists `init_params`. Parameters not in this list are passed to the method itself.

#### Execution Flow Pseudocode
```python
def execute_class_method(fn_id, all_params, session_id):
    # 1. Parse fn_id -> (module, class_name, method_name)
    # 2. Get class_config for this class
    init_param_names = class_config.get("init_params", [])
    
    # 3. Split all_params into init_args and method_args
    init_args = {k: v for k, v in all_params.items() if k in init_param_names}
    method_args = {k: v for k, v in all_params.items() if k not in init_param_names}
    
    # 4. Check for existing instance in cache
    cache_key = hash(class_name + str(init_args))
    instance = session_cache.get(cache_key)
    
    # 5. Instantiate if not cached
    if not instance:
        cls = import_class(module, class_name)
        instance = cls(**init_args)
        if class_config.cache_instances:
            session_cache.put(cache_key, instance)
            
    # 6. Execute method
    result = getattr(instance, method_name)(**method_args)
    return result
```

### 3. Instance Persistence & Caching
Problem: Loading the same model (e.g., `cyto2`) multiple times in a workflow causes excessive latency and VRAM usage.
Solution: Implicit caching within the session.

#### Cache Lifecycle
- **Duration**: Instances are cached for the duration of an MCP session.
- **Keying**: Cache is keyed by `(class_name, init_params_hash)`.
- **ObjectRefs**: If a method returns an `ObjectRef`, that instance is also added to the cache with its `artifact_id` as the key.
- **Memory Management**: The cache uses a Least Recently Used (LRU) eviction policy when VRAM/RAM limits are reached.

### 4. Class-Based Registry & Runtime
The `registry` and `runtimes` modules will be updated to support the "Instantiate-then-Call" pattern:
- **Registry**: Can discover methods of a class. The `fn_id` will follow the pattern `module.ClassName.method_name`.
- **Runtime**: When executing a class method:
  1. If an `ObjectRef` is provided as an input (e.g., `self`), use the serialized instance.
  2. Otherwise, instantiate the class using its constructor (if parameters provided) then call the method.

### 5. Prioritized Cellpose APIs
We focus on APIs with explicit signatures as listed in the Gap Analysis table.

## User Scenarios & Testing

### User Story 1: Reusing a Loaded Model (Priority: P1)
**Given** a user has a session, **When** they call a tool to load/instantiate `CellposeModel` (returning an `ObjectRef`), **And** they call `eval` using that `ObjectRef` as the `self` input, **Then** the model is not re-loaded from disk, significantly reducing execution time.

### User Story 2: Training and Segmenting (Priority: P2)
**Given** a set of training images and labels, **When** the user instantiates a network (via `CellposeModel.__init__`) to get an `ObjectRef`, **And** they call `cellpose.train.train_seg(net=ObjectRef, ...)`, **Then** it returns a `NativeOutputRef` (path to `.pth` weights) and a `TableRef` (training losses). **When** the user then instantiates a `CellposeModel` using that weights path as the `pretrained_model` parameter, **Then** they get a new `ObjectRef` that can be used for segmentation.

## Generalization to Other ML Libraries
The `ObjectRef` and Class-Based Execution patterns are designed to be library-agnostic:
- **StarDist**: `StarDist2D` (init) -> `predict_instances` (method)
- **DeepCell**: `Mesmer` (init) -> `predict` (method)
- **SAM**: `SamPredictor` (init with model) -> `predict` (method)

## Edge Cases
- **Eviction**: If an `ObjectRef` is evicted mid-workflow, the system should attempt to re-instantiate if `init_params` are available in the workflow record.
- **File Deletion**: If the underlying pickle file for a persisted `ObjectRef` is deleted, the tool call must fail gracefully with an informative error.
- **GPU/CPU Mismatch**: If an `ObjectRef` was created on `cuda` but requested on a `cpu`-only worker, the runtime should attempt a `map_location='cpu'` load.
- **Serialization Failures**: Objects with unpicklable state (e.g., open file handles, CUDA context pointers) must use specialized `__getstate__`/`__setstate__` or be excluded from persistence.

## Requirements

### Constitution Constraints
- **Isolation**: Tool processes remain subprocesses. `ObjectRef` serialization/deserialization happens across the subprocess boundary.
- **Artifacts**: `ObjectRef` is a first-class `ArtifactRef`.
- **Discovery**: Registry MUST filter out methods using `**kwargs` unless an explicit overlay is provided.

### Functional Requirements
- **FR-001**: Registry MUST support `dynamic_sources` targeting specific classes within a module.
- **FR-002**: Runtime MUST handle `ObjectRef` by deserializing the object before calling the method.
- **FR-003**: `describe` tool MUST correctly show `ObjectRef` as a valid input/output type.
- **FR-004**: System MUST support `ObjectRef` in workflow export/replay.
- **FR-005**: Discovery MUST support class-based sources, extracting both `__init__` and method signatures.
- **FR-006**: Runtime MUST correctly split parameters into `init_params` and method parameters based on `class_config`.
- **FR-007**: ObjectRef instances MUST be persisted across steps in the same session via a local cache.
- **FR-008**: System MUST provide an eviction policy and allow manual cache management via a standard tool-pack function callable through existing MCP `run` (e.g., `cellpose.cache.clear`), explicitly noting this is not a new MCP tool.
- **FR-009**: Errors involving invalid or expired `ObjectRef` MUST return constitution-aligned structured errors (`code`, `message`, `details[]` entries with `path` + `hint`).
- **FR-010**: Workflow export/records MUST include enough metadata (class name, `init_params`, optional device) to allow reconstruction in a new session.

### Non-Functional Requirements
- **NFR-001**: `ObjectRef` serialization (pickling) must complete in <10s for typical models (e.g., Cellpose, StarDist).
- **NFR-002**: Cache lookup must be O(1).
- **NFR-003**: Memory usage monitoring MUST be active for cached instances, with warnings if VRAM exceeds 90%.

## Schema Changes Required

### `src/bioimage_mcp/registry/manifest_schema.py`
```python
class ClassConfig(BaseModel):
    init_params: list[str] = Field(default_factory=list)
    cache_instances: bool = True

class FunctionOverlay(BaseModel):
    # Existing fields...
    class_config: ClassConfig | None = None
```

## Implementation Plan

### Phase 1: Artifact & Registry (0.17.1)
1. Add `ObjectRef` to `bioimage_mcp.artifacts.types`.
2. Update `bioimage_mcp.registry.discovery` to walk classes and methods.
3. Update `manifest.yaml` schema to allow `classes` under `dynamic_sources` and `class_config` in `function_overlays`.

### Phase 2: Runtime Support (0.17.2)
1. Update `bioimage_mcp.runtimes` to handle calling methods on objects.
2. Implement object serialization/deserialization helpers in `bioimage_mcp_base`.

### Phase 3: Cellpose Tool Pack Update (0.17.3)
1. Update `tools/cellpose/manifest.yaml` with correct module paths.
2. Add function overlays for any Cellpose methods that require parameter renaming or simplification.

## File Changes

### 1. `src/bioimage_mcp/artifacts/types.py`
- Add `ObjectRef` class inheriting from `ArtifactRef`.

### 2. `tools/cellpose/manifest.yaml`
```yaml
tool_pack:
  id: bioimage-mcp-cellpose
  version: "0.2.0"

dynamic_sources:
  - module: cellpose.models
    classes: [CellposeModel]
    methods: [__init__, eval]
  - module: cellpose.denoise
    classes: [DenoiseModel]
    methods: [eval]
  - module: cellpose.train
    functions: [train_seg]
  - module: cellpose.metrics
    functions: [average_precision]

function_overlays:
  "cellpose.models.CellposeModel.__init__":
    hints:
      outputs:
        self: { artifact_type: ObjectRef }
  "cellpose.models.CellposeModel.eval":
    class_config:
      init_params: [gpu, model_type, net_avg, device, residual_on, style_on, concatenation]
    io_pattern: IMAGE_TO_LABELS
    hints:
      inputs:
        self: { artifact_type: ObjectRef }
        x: { artifact_type: BioImageRef }
      outputs:
        masks: { artifact_type: LabelImageRef }
  "cellpose.train.train_seg":
    hints:
      inputs:
        net: { artifact_type: ObjectRef }
      outputs:
        model_path: { artifact_type: NativeOutputRef, format: "pytorch-weights" }
        losses: { artifact_type: TableRef, format: "json" }
```

### 3. `src/bioimage_mcp/registry/discovery.py`
- Modify `_discover_functions` to also inspect requested classes and their methods.

## Success Criteria

- **SC-001**: `list` and `describe` correctly show `cellpose.models.CellposeModel.eval`.
- **SC-002**: `CellposeModel.eval` correctly identifies `ObjectRef` for the `self` (or equivalent) parameter.
- **SC-003**: Executing `eval` with a pre-instantiated `ObjectRef` is at least 2x faster than cold-start for subsequent calls (for standard models).
- **SC-004**: `train_seg` successfully returns a `NativeOutputRef` for weights and a `TableRef` for losses.

## Migration Notes
- All previous usages of `ModelRef` or `NetRef` in experimental branches must be migrated to `ObjectRef`.
- Function IDs for Cellpose are now class-qualified (e.g., `cellpose.models.CellposeModel.eval`).

## Key Entities

### ObjectRef
```json
{
  "ref_id": "obj_12345",
  "type": "ObjectRef",
  "uri": "file:///path/to/model.pkl",
  "metadata": {
    "python_class": "cellpose.models.CellposeModel",
    "device": "cuda",
    "sha256": "..."
  }
}
```
