# Data Model: Cellpose Object-Oriented API

## Entities

### ObjectRef
**Description**: Reference to a serialized Python object (e.g., a loaded Cellpose model).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ref_id | string | Yes | Unique identifier for the object |
| type | string | Yes | Always "ObjectRef" |
| uri | string | Yes | URI of the object (e.g., `obj://session/env/id`) |
| format | string | Yes | Serialization format (e.g., "pickle") |
| python_class | string | Yes | Fully qualified class name (e.g., `cellpose.models.CellposeModel`) |
| storage_type | string | Yes | "memory" or "file" |
| metadata | dict | No | Optional metadata (device, weights path, etc.) |

**Validation Rules**:
- `uri` must follow `obj://<session_id>/<env_id>/<object_id>` if `storage_type` is "memory".
- `format` should typically be "pickle" for version 0.1.

### DynamicSource (Extended)
**Description**: Enhanced configuration for discovering class-based APIs.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| adapter | string | Yes | Adapter ID (e.g., "cellpose") |
| prefix | string | Yes | Function ID prefix |
| modules | list[str] | Yes | Modules to scan |
| target_class | string | No | Optional class to discover (instantiation + methods) |
| class_methods | list[str] | No | Methods to expose if `target_class` is set |

**Validation Rules**:
- If `target_class` is provided, the registry will treat `__init__` as a "constructor" function and the specified `class_methods` as functions that take an `ObjectRef` of this class as input.

## State Transitions

- **Instantiation**: `(Init Params)` → `ObjectRef` (Model loaded in memory)
- **Method Execution**: `ObjectRef` + `(Method Params)` → `LabelImageRef` (Inference)
- **Eviction**: `ObjectRef` → `None` (Object cleared from memory/cache)
