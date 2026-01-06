# Research: Cellpose Object-Oriented API & Stateful Execution

## Research Questions

### Q1: ObjectRef Serialization Strategy
**Decision**: Use `pickle` for in-process caching (same session), file-backed for cross-session/cross-env if needed.
**Rationale**: Cellpose models are large PyTorch models; pickle is the standard and most efficient way to preserve full Python object state including GPU tensor references and internal model metadata.
**Alternatives Considered**:
- `torch.save()`: Too specific to PyTorch; would require special handling for non-PyTorch objects in the future.
- `dill`: Increases dependencies and may be overkill for standard Cellpose models.
- JSON: Not feasible for binary data (tensors/weights).

### Q2: Class-based Discovery Pattern
**Decision**: Extend `DynamicSource` with optional `target_class` and `class_methods` fields.
**Rationale**: Minimal schema change that remains backward compatible. Allows the registry to specifically target class constructors and methods for introspection.
**Alternatives Considered**:
- Separate `ClassSource` type: Adds complexity to the manifest parser and registry logic.
- Manual manifest entries: Loses the benefit of dynamic discovery and introspection as the Cellpose API evolves.

### Q3: Init/Method Parameter Separation
**Decision**: Add `class_context` to `ExecuteRequest` with `init_params` dict.
**Rationale**: Clean separation in the IPC protocol. The worker can use `init_params` to instantiate the class (or retrieve from cache) and then call the target method with the primary `params`.
**Alternatives Considered**:
- Convention-based prefixes (e.g., `init_model_type`): Fragile and clutters the flat parameter namespace.
- Nested params: Complicates Pydantic validation and client-side form generation.

### Q4: ObjectRef URI Scheme
**Decision**: `obj://session_id/env_id/object_id`
**Rationale**: Consistent with the existing `mem://` pattern for transient artifacts. Clearly identifies the artifact as a Python object rather than a raw buffer or image.
**Alternatives Considered**:
- Extend `mem://`: Confuses images/buffers with complex Python objects.
- New `model://`: Too specific; we want a general way to pass any Python object between steps.

### Q5: Eviction API
**Decision**: Extend existing `evict` command to support `ObjectRef`.
**Rationale**: Provides a unified interface for memory management across all transient artifact types.
**Alternatives Considered**:
- Separate `clear_model_cache` tool: Bloats the MCP tool surface and requires users to know which type of memory they are clearing.
