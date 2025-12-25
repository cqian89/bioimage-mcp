# Implementation Plan: Dynamic Function Registry

**Branch**: `005-dynamic-function-registry` | **Date**: 2025-12-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-dynamic-function-registry/spec.md`

## Summary

Extend the static tool registry with a dynamic discovery + dispatch layer for allowlisted scientific Python libraries (initially `phasorpy`, `scikit-image`, and `scipy.ndimage`). This enables ~80+ bioimage analysis functions to be exposed via MCP without manual manifest entries, with the immediate goal of enabling FLIM calibration workflows via `phasorpy.phasor.phasor_transform`.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic`, `bioio`, `ngff-zarr`, `numpydoc`  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Testing**: `pytest` (TDD: tests written before implementation)  
**Target Platform**: Local/on-prem; Linux-first (macOS/Windows best-effort)  
**Project Type**: Python service + CLI  
**Performance Goals**: Bounded MCP payload sizes; discovery caching; <2s startup overhead  
**Constraints**: No large binary payloads in MCP; artifact references only  
**Scale/Scope**: Tool catalog can grow; discovery must remain paginated

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: Dynamic functions indexed in same SQLite registry; discovery remains paginated via existing `search_functions` API. No new MCP endpoints required.
- [x] Summary-first responses: Full schemas fetched on-demand via `describe_function(fn_id)`. Dynamic functions follow same pattern as static.
- [x] Tool execution isolated: Dynamic functions execute in per-tool envs (primarily `bioimage-mcp-base`). Heavy deps remain in tool envs, not core server.
- [x] Artifact references only: All dynamic function I/O uses `BioImageRef`, `LabelImageRef`, `TableRef`, `NativeOutputRef`. No arrays in MCP messages.
- [x] Reproducibility: Dynamic function calls recorded in workflow history with fully qualified fn_ids and environment lockfile hash. Cache invalidation tied to `envs/bioimage-mcp-base.lock.yml`.
- [x] Safety + debuggability: Only allowlisted modules/functions exposed via `dynamic_sources` config. Structured logs persisted. Full test coverage required (TDD).

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/005-dynamic-function-registry/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model definitions
├── quickstart.md        # Quick start guide
├── contracts/           # Contract test specifications
└── tasks.md             # Implementation tasks
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── registry/
│   ├── loader.py                    # Manifest loading (existing, extended)
│   ├── manifest_schema.py           # Manifest schema (existing, extended)
│   └── dynamic/                     # NEW: Dynamic registry subsystem
│       ├── __init__.py
│       ├── models.py                # FunctionMetadata, ParameterSchema, IOPattern
│       ├── discovery.py             # Dynamic function discovery engine
│       ├── introspection.py         # Signature/docstring parsing
│       ├── cache.py                 # Introspection result caching
│       └── adapters/                # Library-specific adapters
│           ├── __init__.py          # BaseAdapter protocol + registry
│           ├── skimage.py           # scikit-image adapter
│           ├── phasorpy.py          # phasorpy adapter
│           └── scipy_ndimage.py     # scipy.ndimage adapter

tools/base/
├── manifest.yaml                    # Extended with dynamic_sources
└── bioimage_mcp_base/
    └── dynamic_dispatch.py          # Runtime dispatch in tool env

tests/
├── unit/
│   └── registry/
│       ├── test_dynamic_discovery.py
│       ├── test_introspection.py
│       └── test_adapters.py
├── contract/
│   └── test_dynamic_functions.py    # Adapter contract tests
└── integration/
    ├── test_flim_calibration.py     # US1: FLIM workflow
    ├── test_skimage_dynamic.py      # US2: Image filters
    └── test_scipy_adapter.py        # US3: Extensibility
```

**Structure Decision**: Dynamic registry code lives under `src/bioimage_mcp/registry/dynamic/` as a cohesive subsystem. Adapters are grouped in `dynamic/adapters/` subdirectory. This follows existing registry patterns and keeps dynamic functionality isolated.

## Architecture

### Current Architecture (Static)

```
┌─────────────────────────────────────────────────────────────────┐
│  tools/base/manifest.yaml                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  functions:                                              │    │
│  │    - fn_id: base.phasor_from_flim   # Manually defined  │    │
│  │    - fn_id: base.gaussian           # Manually defined  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  src/bioimage_mcp/registry/loader.py                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  - Scans manifest YAML files                             │    │
│  │  - Indexes functions in SQLite                           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed Architecture (Dynamic)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Dynamic Library Function Registry                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  1. LIBRARY ADAPTER REGISTRY                                     │    │
│  │     Each library has an adapter that knows how to:               │    │
│  │     - Discover functions (which to expose)                       │    │
│  │     - Infer I/O types (image, labels, table, scalar)            │    │
│  │     - Map artifact refs ↔ numpy/library-native types            │    │
│  │     - Generate curated descriptions (from docstrings)            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  2. MANIFEST: dynamic_sources configuration                      │    │
│  │                                                                   │    │
│  │  dynamic_sources:                                                 │    │
│  │    - adapter: skimage        # Adapter implementation            │    │
│  │      prefix: skimage         # fn_id prefix for tools            │    │
│  │      modules: [skimage.filters, ...]                             │    │
│  │      include_patterns: ["*"]                                      │    │
│  │      exclude_patterns: ["_*", "test_*"]                          │    │
│  │                                                                   │    │
│  │    - adapter: phasorpy                                            │    │
│  │      prefix: phasorpy                                             │    │
│  │      modules: [phasorpy.phasor, phasorpy.io, ...]                │    │
│  │                                                                   │    │
│  │    - adapter: scipy_ndimage                                       │    │
│  │      prefix: scipy           # Note: adapter != prefix            │    │
│  │      modules: [scipy.ndimage]                                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  3. INTROSPECTION ENGINE (at startup/discovery time)             │    │
│  │                                                                   │    │
│  │  For each (adapter, module, function):                           │    │
│  │    1. Get function signature + type hints                        │    │
│  │    2. Parse numpy-style docstring for param descriptions         │    │
│  │    3. Infer input artifact types from first positional args      │    │
│  │    4. Infer output artifact types from return annotation         │    │
│  │    5. Generate JSON Schema for params                            │    │
│  │    6. Register as: {prefix}.{module_leaf}.{func_name}            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  4. DYNAMIC ENTRYPOINT ROUTER                                    │    │
│  │                                                                   │    │
│  │  def dispatch(fn_id: str, inputs: dict, params: dict):           │    │
│  │      if fn_id in STATIC_FN_MAP:                                  │    │
│  │          return STATIC_FN_MAP[fn_id](...)                        │    │
│  │                                                                   │    │
│  │      # Dynamic dispatch by prefix                                 │    │
│  │      adapter = get_adapter_by_prefix(fn_id)                      │    │
│  │      module_path, func_name = parse_fn_id(fn_id)                 │    │
│  │      func = import_function(module_path, func_name)              │    │
│  │      return adapter.call_function(func, inputs, params)          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Function ID Naming Convention

| Library | Adapter | Prefix | Module | Function | MCP fn_id |
|---------|---------|--------|--------|----------|-----------|
| scikit-image | `skimage` | `skimage` | filters | gaussian | `skimage.filters.gaussian` |
| scikit-image | `skimage` | `skimage` | measure | regionprops_table | `skimage.measure.regionprops_table` |
| phasorpy | `phasorpy` | `phasorpy` | phasor | phasor_transform | `phasorpy.phasor.phasor_transform` |
| scipy | `scipy_ndimage` | `scipy` | ndimage | gaussian_filter | `scipy.ndimage.gaussian_filter` |

**Key distinction**: The `adapter` field identifies the adapter implementation class. The `prefix` field defines the fn_id namespace. These MAY differ (e.g., `scipy_ndimage` adapter uses `scipy` prefix).

## I/O Pattern Definitions

```python
class IOPattern(Enum):
    """Common I/O patterns for bioimage functions."""
    IMAGE_TO_IMAGE = auto()      # BioImageRef -> BioImageRef
    IMAGE_TO_LABELS = auto()     # BioImageRef -> LabelImageRef
    LABELS_TO_TABLE = auto()     # LabelImageRef -> TableRef
    SIGNAL_TO_PHASOR = auto()    # BioImageRef -> (intensity, G, S) images
    PHASOR_TRANSFORM = auto()    # (G, S) -> (G', S')
    PHASOR_TO_OTHER = auto()     # (G, S) -> polar/signal
    ARRAY_TO_ARRAY = auto()      # Generic array transform
    ARRAY_TO_SCALAR = auto()     # Array -> scalar value (e.g., threshold_otsu)
    FILE_TO_SIGNAL = auto()      # File path -> signal array
```

### Module-Level Defaults (skimage)

| Module | Default I/O Pattern |
|--------|---------------------|
| `skimage.filters` | IMAGE_TO_IMAGE |
| `skimage.morphology` | IMAGE_TO_IMAGE |
| `skimage.transform` | IMAGE_TO_IMAGE |
| `skimage.exposure` | IMAGE_TO_IMAGE |
| `skimage.restoration` | IMAGE_TO_IMAGE |
| `skimage.segmentation` | IMAGE_TO_LABELS |
| `skimage.measure` | LABELS_TO_TABLE |

### Function-Level Overrides

| Function | Override Pattern | Reason |
|----------|------------------|--------|
| `threshold_otsu` | ARRAY_TO_SCALAR | Returns scalar threshold value |
| `threshold_yen` | ARRAY_TO_SCALAR | Returns scalar threshold value |
| `label` | IMAGE_TO_LABELS | Creates label image from binary |
| `regionprops` | LABELS_TO_TABLE | Extracts properties from labels |
| `regionprops_table` | LABELS_TO_TABLE | Extracts properties as table |

## Phases

### Phase 1: Setup (Foundation)
*Goal: Define data models and configuration structures.*

- Define `DynamicSource` config schema in `manifest_schema.py`
- Create `FunctionMetadata`, `ParameterSchema`, `IOPattern` models
- Extend `tools/base/manifest.yaml` with `dynamic_sources` section

### Phase 2: Core Infrastructure
*Goal: Implement discovery, introspection, and adapter infrastructure.*

- Create `BaseAdapter` protocol defining adapter interface
- Implement `Introspector` class with signature analysis and docstring parsing
- Implement dynamic discovery engine
- Integrate with existing manifest loader
- Implement caching with lockfile-based invalidation

### Phase 3: PhasorPy Adapter (US1 - P1)
*Goal: Enable FLIM calibration using phasorpy.*

- Implement `PhasorPyAdapter` with PHASOR_TRANSFORM pattern
- Map `phasor_from_signal`, `phasor_transform`, `phasor_from_polar`
- Integration test: FLIM calibration workflow with FLUTE dataset

### Phase 4: Skimage Adapter (US2 - P2)
*Goal: Expose standard scikit-image filters automatically.*

- Implement `SkimageAdapter` with module-level I/O inference
- Automatic scanning of configured submodules
- Integration test: filter discovery and execution

### Phase 5: Scipy Adapter (US3 - P3)
*Goal: Validate extensibility with scipy.ndimage.*

- Implement `ScipyNdimageAdapter`
- Integration test: distance_transform_edt discovery

### Phase 6: Polish & Validation
*Goal: Ensure robustness, performance, and documentation.*

- Validate all functions have descriptions (0 empty)
- Performance benchmark: startup overhead < 2s (warm cache)
- Full regression suite passes

## Technical Constraints

- **Backwards Compatibility**: Static function routing unchanged; dynamic dispatch only for unrecognized fn_ids
- **Lazy Loading**: Functions imported only at call time, not at discovery
- **Cache Invalidation**: Tied to `envs/bioimage-mcp-base.lock.yml` hash
- **Prefix Uniqueness**: Adapter prefixes must be unique; validated at manifest load time
- **Graceful Degradation**: Missing docstrings → best-effort schema; import errors → skip with warning

## Data Model References

See [data-model.md](./data-model.md) for:
- `DynamicSource` configuration schema
- `FunctionMetadata` introspection result model
- `ParameterSchema` JSON Schema generation
- `IOPattern` enumeration

## Migration Path

1. **Phase 1-2**: Add dynamic infrastructure (no breaking changes to existing static functions)
2. **Phase 3**: PhasorPy adapter enables FLIM calibration (immediate value)
3. **Phase 4-5**: Expand coverage with skimage and scipy
4. **Future**: Consider migrating redundant static functions to dynamic

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Library API changes break schemas | Pin versions in lockfiles; contract tests for critical functions |
| Introspection performance | Cache results; invalidate only on lockfile change |
| Complex I/O patterns | Function-level overrides in adapter; exclude via `exclude_patterns` |
| Side-effect functions exposed | Explicit exclusion patterns; code review of include lists |

## Success Criteria

1. `phasorpy.phasor.phasor_transform` available via MCP discovery
2. FLIM calibration workflow (Reference → Calibrate → Sample) completes end-to-end
3. `skimage.filters.*` functions searchable and callable
4. No regression in existing static function behavior
5. Contract tests pass for all adapters
6. Startup overhead < 2s with warm cache

## References

- PhasorPy documentation: https://www.phasorpy.org/
- scikit-image API: https://scikit-image.org/docs/stable/api/
- scipy.ndimage: https://docs.scipy.org/doc/scipy/reference/ndimage.html
- Existing introspection: `src/bioimage_mcp/runtimes/introspect.py`
- FLUTE dataset: `datasets/FLUTE_FLIM_data_tif/README.md`
- Proposal document: `docs/plan/005-dynamic-function-registry.md`
