# Feature Specification: Dynamic Function Registry

**Feature Branch**: `005-dynamic-function-registry`
**Created**: 2025-12-25
**Status**: Draft
**Input**: User description: "Implement dynamic function registry based on @docs/plan/005-dynamic-function-registry.md"

This feature extends the existing static tool registry with a dynamic discovery + dispatch layer for allowlisted scientific Python libraries (initially `phasorpy`, `scikit-image`, and `scipy.ndimage`).

## Clarifications

### Session 2025-12-25

- Q: How should the system detect when cached function metadata needs to be refreshed? → A: On environment lockfile hash change.
- Q: How should the system handle functions with **required** parameters of unsupported types? → A: Exclude the function entirely from discovery.
- Q: How should the system handle **optional** parameters with unsupported types? → A: Exclude the parameter from the schema (use default).
- Q: How to handle functions with missing docstrings? → A: Register using signature only (best effort).
- Q: How to handle function name collisions? → A: Rely on fully qualified IDs (module path) to distinguish.
- Q: Behavior on introspection failure? → A: Log warning and skip.

## User Scenarios & Testing

### User Story 1 - Calibrate FLIM Data (Priority: P1)

As a researcher, I need to use `phasor_transform` to calibrate my FLIM data against a reference standard so I can obtain accurate lifetime measurements.

**Why this priority**: Calibration is a blocking requirement for the FLIM analysis workflow (specifically for the FLUTE dataset) and is currently impossible because the necessary function is not exposed.

**Independent Test**: Can be tested by running the calibration workflow on the FLUTE dataset (reference image -> calibrate -> sample image) and verifying the phasor coordinates shift correctly.

**Acceptance Scenarios**:

1. **Given** a reference FLIM image with known lifetime (e.g., Fluorescein = 4ns), **When** I calculate its phasor coordinates and determine the offset/rotation needed, **Then** I can use `phasorpy.phasor.phasor_transform` to apply this calibration to a sample image.
2. **Given** calibrated phasor data, **When** I convert it to polar coordinates, **Then** the lifetime values match the expected biological range.
3. **Given** a known-lifetime reference, **When** I compute the expected reference phasor using `phasorpy.phasor.phasor_from_polar` and derive phase/modulation correction, **Then** applying `phasorpy.phasor.phasor_transform` aligns measured reference phasors to the expected position.

---

### User Story 2 - Access Image Filters (Priority: P2)

As a user, I want to use standard `scikit-image` filters (Gaussian, median, etc.) without waiting for them to be manually added to the tool manifest.

**Why this priority**: Users expect standard image processing functions to be available. Manually wrapping each function is inefficient and error-prone.

**Independent Test**: Can be tested by listing available tools and verifying `skimage.filters.*` are present, then running one (e.g., `skimage.filters.gaussian`) on a test image.

**Acceptance Scenarios**:

1. **Given** the system is running, **When** I list available tools, **Then** I see functions like `skimage.filters.gaussian`, `skimage.filters.median`, and `skimage.morphology.binary_erosion`.
2. **Given** an input image, **When** I call `skimage.filters.gaussian` with `sigma=2`, **Then** the output is a valid Gaussian-blurred image artifact.

---

### User Story 3 - Extensibility for New Libraries (Priority: P3)

As a developer, I want to expose a new library's functions by writing a simple adapter, so that I don't have to write wrapper code for every function.

**Why this priority**: Ensures the system scales to support future libraries (e.g., OpenCV, ITK) without architectural changes.

**Independent Test**: Can be tested by verifying the `scipy.ndimage` adapter, which follows the same pattern as `skimage`.

**Acceptance Scenarios**:

1. **Given** the `scipy.ndimage` adapter is configured, **When** I search for "distance transform", **Then** I find `scipy.ndimage.distance_transform_edt`.

### Edge Cases

Edge case handling is specified normatively in FR-013 and FR-017. Summary for reference:

- **Unsupported Types**: See FR-013.
- **Missing Docs**: See FR-013.
- **Name Collisions**: Handled by fully-qualified IDs (module path).
- **Introspection Failures**: See FR-017.
- **Side Effects**: Must be excluded via `exclude_patterns` configuration.

### Terminology

- **DynamicSource**: A configuration entry in `manifest.yaml` under `dynamic_sources` that defines which library/modules to expose.
- **Adapter**: A Python class implementing the `BaseAdapter` protocol that handles library-specific introspection and execution.
- **Prefix**: The fn_id namespace prefix (e.g., `skimage`, `phasorpy`, `scipy`) used in tool identifiers.

## Requirements

### Constitution Constraints

- **MCP API impact**: Increases the number of discoverable tools significantly. Must ensure `list_tools` remains performant and supports pagination if not already implemented.
- **Artifact I/O**: All dynamic functions MUST use `BioImageRef`, `LabelImageRef`, `TableRef`, or `NativeOutputRef` for inputs/outputs. No large arrays in payloads.
- **Isolation**: Dynamic function execution occurs within the tool environment specified by the manifest containing the `dynamic_sources` configuration. For v0.4, this is `bioimage-mcp-base`. Future tool packs may define their own dynamic sources within their respective environments.
- **Reproducibility**: Dynamic function calls MUST be recorded in the workflow history with their fully qualified IDs (e.g., `skimage.filters.gaussian`) and version information from the environment.
- **Safety/observability**: Access to arbitrary code execution must be prevented. Only modules and functions explicitly allowlisted in the manifest `dynamic_sources` configuration can be loaded.

### Functional Requirements

- **FR-001**: System MUST support a `dynamic_sources` configuration section in `manifest.yaml` to define adapters, modules, and include/exclude patterns.
- **FR-002**: System MUST implement a standardized adapter interface that defines methods for function discovery, I/O pattern inference, artifact loading/saving, parameter adaptation, and function invocation.
- **FR-003**: System MUST provide an adapter for `scikit-image` that maps functions to MCP tools and infers I/O patterns using module-level defaults (e.g., `filters`, `transform`, `exposure` as image->image; `segmentation` as image->labels; `measure` as labels->table) with function-specific overrides where needed. Function-specific overrides include: `threshold_otsu`/`threshold_yen` as ARRAY_TO_SCALAR, `label` as IMAGE_TO_LABELS, `regionprops`/`regionprops_table` as LABELS_TO_TABLE. See `plan.md` for complete I/O pattern definitions.
- **FR-004**: System MUST provide an adapter for `phasorpy` that maps functions and supports common FLIM patterns, including tuple outputs. At minimum:
  - `phasorpy.phasor.phasor_from_signal` MUST be callable and return multiple output artifacts (e.g., intensity, G image, S image).
  - `phasorpy.phasor.phasor_transform` MUST be callable and return multiple output artifacts (e.g., transformed G image, transformed S image).
- **FR-005**: System MUST provide an adapter for `scipy.ndimage` functions, including common filters and transforms (e.g., `*_filter`, `binary_*`, `distance_transform_*`, `zoom`, `rotate`).
- **FR-006**: System MUST parse documentation from source code (NumPy-style docstrings) using `numpydoc` (or equivalent) to generate user-facing tool descriptions and parameter documentation.
- **FR-007**: System MUST generate JSON Schemas for dynamic function parameters based on the signature, type hints (when present), and default values.
- **FR-008**: System MUST dynamically dispatch tool execution requests to the appropriate adapter and underlying library function.
- **FR-009**: System MUST cache introspection results to minimize startup overhead. Cache invalidation MUST be triggered by changes to the tool pack's environment lockfile hash (e.g., `envs/bioimage-mcp-base.lock.yml` for the base toolkit). The cache SHOULD be stored in `~/.bioimage-mcp/cache/dynamic/<tool_pack_id>/`.
- **FR-010**: System MUST expose dynamic functions under fully qualified MCP `fn_id`s that match the Python import path plus function name (e.g., `skimage.filters.gaussian`, `phasorpy.phasor.phasor_transform`, `scipy.ndimage.gaussian_filter`). Each `dynamic_sources` entry MUST include both an `adapter` field (identifying the adapter implementation class) and a `prefix` field (defining the fn_id namespace). These MAY differ: e.g., `adapter: scipy_ndimage` with `prefix: scipy` produces fn_ids like `scipy.ndimage.gaussian_filter`.
- **FR-011**: Runtime dispatch MUST be backwards compatible and lazy: static function routing remains unchanged; if a `fn_id` is not static, the system selects the adapter by `fn_id` prefix and imports the target module/function only at call time.
- **FR-012**: Discovery MUST honor allowlisted `modules` and `include_patterns`/`exclude_patterns` so that internal helpers and side-effectful functions can be excluded.
- **FR-013**: Introspection MUST degrade gracefully:
  - If docstrings are missing, tools MUST register with a best-effort schema derived from the signature.
  - If a **required** parameter has an unsupported type, the function MUST be excluded.
  - If an **optional** parameter has an unsupported type, it MUST be omitted from the schema.
- **FR-017**: Discovery resilience: If introspection fails for a specific module or function (e.g., import error), the system MUST log a warning and skip the failing item.
- **FR-014**: The implementation MUST include automated verification for dynamic functionality:
  - Unit tests for discovery/introspection and schema generation.
  - Contract tests for each adapter (representative function per module/pattern).
  - An integration test covering the FLIM calibration workflow end-to-end using the FLUTE dataset (`Embryo.tif` calibrated against `Fluorescein_Embryo.tif` with 4ns known lifetime).
- **FR-015**: Discovered dynamic functions MUST be indexed into the same registry store as static functions (SQLite) so they are searchable/describeable via the existing discovery APIs.
- **FR-016**: Adapter `prefix` values MUST be unique across configured `dynamic_sources` to avoid ambiguous dispatch.

### Configuration Example

The manifest MUST support configuration equivalent to:

```yaml
# tools/base/manifest.yaml

dynamic_sources:
  - adapter: skimage
    modules:
      - skimage.filters
      - skimage.morphology
      - skimage.segmentation
      - skimage.measure
      - skimage.transform
      - skimage.exposure
      - skimage.restoration
    include_patterns: ["*"]
    exclude_patterns: ["_*", "test_*", "*_coords"]

  - adapter: phasorpy
    modules: ["phasorpy.phasor", "phasorpy.io", "phasorpy.cluster"]
    include_patterns: ["phasor_*", "signal_from_*", "*_cluster_*"]
    exclude_patterns: ["parse_*", "number_threads"]

  - adapter: scipy_ndimage
    modules: ["scipy.ndimage"]
    include_patterns: ["*_filter", "binary_*", "label", "find_objects", "distance_transform_*", "zoom", "rotate"]
```

Note: the `adapter` field identifies an adapter implementation; the tool `fn_id` prefix comes from the adapter’s `prefix` (e.g., the `scipy_ndimage` adapter may expose tools under the `scipy.*` namespace).

### Key Entities

- **Adapter Interface**: Abstraction for handling translation between MCP artifact references and library-native data structures.
- **IOPattern**: Categorization of common bioimage I/O shapes (e.g., image->image, image->labels, labels->table, signal->phasor, phasor transform).
- **FunctionInfo**: Metadata about a discovered function, including its ID, description, parameters schema, and I/O pattern.
- **DynamicSource**: Configuration object defining a library to expose (adapter name, modules list, filters).

## Success Criteria

### Measurable Outcomes

- **SC-001**: `phasorpy.phasor.phasor_transform` is discoverable, callable, and produces correct output artifacts.
- **SC-002**: Bioimage-relevant functions from configured dynamic sources are discoverable and callable without manual wrappers (including broad coverage across the configured `skimage.*` submodules).
- **SC-003**: System startup time increases by no more than 2 seconds due to dynamic discovery (measured with warm cache, excluding initial cold-cache population).
- **SC-004**: End-to-end FLIM calibration workflow (Reference -> Calibrate -> Sample) completes successfully using dynamic functions.
- **SC-005**: 100% of dynamically discovered functions have a non-empty description and parameter schema; parameter descriptions are derived from docstrings when available.
- **SC-006**: No regressions in existing static function discovery and execution behavior.
- **SC-007**: Adapter contract tests pass for all configured adapters.
