# Research: Dynamic Function Registry

## Unknowns & Clarifications

### Resolved Clarifications
*From Feature Spec*
- **Cache Invalidation**: Triggered by environment lockfile hash changes.
- **Unsupported Types**: Required params with unsupported types causes function exclusion. Optional params are omitted.
- **Missing Docstrings**: Fallback to signature-based schema.
- **Name Collisions**: Use fully qualified IDs (e.g., `skimage.filters.gaussian`).
- **Introspection Failure**: Log warning and skip.

### New Findings
- **Introspection Tools**: `numpydoc` is required for parsing NumPy-style docstrings (FR-006) but is not currently in `bioimage-mcp-base`. It must be added.
- **Environment Isolation**: Introspection must run *inside* the tool environment to avoid polluting the core server and to ensure correct type resolution.
- **Library Availability**: `scikit-image`, `scipy`, and `phasorpy` are present in `bioimage-mcp-base`.

## Technical Decisions

### 1. Introspection Strategy
**Decision**: Implement a standalone script (`src/bioimage_mcp/runtimes/introspect_module.py`) that is executed within the target environment via `conda run` (or `runtimes.executor` mechanism).
**Rationale**: Adheres to Constitution II (Isolation). The core server cannot import tool libraries directly.
**Mechanism**:
1. Core server calls `runtimes.executor.run_script(env, script, args=[module_name])`.
2. Script imports `module_name`.
3. Script walks module attributes, filtering by `include_patterns`/`exclude_patterns`.
4. Script uses `inspect.signature` + `numpydoc` to build JSON Schema.
5. Script outputs JSON to stdout/file for core server to consume.

### 2. Adapter Architecture
**Decision**: Define a `DynamicAdapter` interface in `src/bioimage_mcp/registry/adapters.py`.
**Rationale**: Allows extensibility (FR-002, User Story 3).
**Structure**:
- `discover(module_config) -> List[ToolMetadata]`
- `execute(fn_id, inputs, params) -> List[Artifact]`
- `resolve_io_pattern(func_name, signature) -> IOPattern`

### 3. I/O Pattern Inference
**Decision**: Use a rule-based system in adapters to map function signatures to Artifact types.
**Rationale**: Most bioimage functions follow predictable patterns (Image -> Image, Image -> Label).
**Rules (skimage example)**:
- `skimage.filters.*` -> `BioImageRef` -> `BioImageRef`
- `skimage.segmentation.*` -> `BioImageRef` -> `LabelImageRef`
- `skimage.measure.*` -> `LabelImageRef` -> `TableRef`
- Overrides allowed for specific functions (e.g., `threshold_*` returns scalar/value).

### 4. Dependency Updates
**Decision**: Add `numpydoc` to `envs/bioimage-mcp-base.yaml`.
**Rationale**: Essential for FR-006 (docstring parsing).

### 5. PhasorPy Integration
**Decision**: Map `phasor_transform` to consume `BioImageRef` (G/S or Harmonic) and produce `BioImageRef` (Transformed G/S).
**Rationale**: Matches FLIM workflows. `phasorpy` uses xarray/numpy; adapter must handle conversion to/from OME-Zarr/TIFF artifacts.
