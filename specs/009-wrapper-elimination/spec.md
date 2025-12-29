# Feature Specification: Wrapper Elimination & Enhanced Dynamic Discovery

**Feature Branch**: `009-wrapper-elimination`  
**Created**: 2025-12-29  
**Status**: Draft  
**Input**: User description: "Remove thin wrapper duplication and enable full dynamic discovery"
**Parent Spec**: 008-api-refinement

## Overview

This specification addresses critical issues identified during code review:

1. **Function naming mismatch**: Spec says `base.skimage.filters.gaussian`, implementation uses `base.bioimage_mcp_base.preprocess.gaussian`
2. **Thin wrapper duplication**: 15 functions are near-identical wrappers (~10-15 lines of I/O boilerplate)
3. **Essential wrappers obscured**: High-value functions (phasor, axis ops) buried among thin wrappers
4. **Dynamic discovery underutilized**: System is built but not fully integrated

## User Scenarios & Testing *(mandatory)*

### User Story 1 - LLM Agent Uses Library Functions Directly (Priority: P1)

An LLM agent needs to apply a Gaussian blur to an image. Instead of navigating through duplicative wrapper functions, the agent discovers and calls the library function directly via dynamic discovery.

**Why this priority**: This is the core value proposition - reducing function bloat and providing clear, consistent naming that matches library conventions LLMs are trained on.

**Independent Test**: Can be fully tested by calling `search_functions(query="gaussian blur")`, selecting `base.skimage.filters.gaussian`, and executing it on a test image.

**Acceptance Scenarios**:

1. **Given** a registered image artifact, **When** agent searches for "gaussian blur", **Then** results include `base.skimage.filters.gaussian` with appropriate description
2. **Given** a dynamically discovered function `base.skimage.filters.gaussian`, **When** agent calls `describe_function(fn_id="base.skimage.filters.gaussian")`, **Then** response includes complete schema with parameters from library introspection
3. **Given** a valid image artifact, **When** agent calls `run_function(fn_id="base.skimage.filters.gaussian", inputs={"image": image_ref}, params={"sigma": 2.0})`, **Then** function executes successfully and returns a smoothed image artifact

---

### User Story 2 - Essential Wrappers Clearly Identified (Priority: P2)

A developer or LLM agent can easily identify functions that provide value beyond thin wrappers - such as format bridging, metadata-aware axis operations, and multi-output orchestration.

**Why this priority**: Essential wrappers serve critical purposes (OME metadata sync, multi-output handling) and must remain accessible with clear naming that distinguishes them from passthrough functions.

**Independent Test**: Can be tested by calling `list_tools(path="base.wrapper")` and verifying all 10 essential wrappers are present with descriptive names.

**Acceptance Scenarios**:

1. **Given** the manifest is loaded, **When** agent calls `list_tools(path="base.wrapper")`, **Then** response lists all essential wrappers grouped by category (io, axis, phasor, denoise)
2. **Given** the function `base.wrapper.phasor.phasor_from_flim`, **When** agent calls `describe_function()`, **Then** response shows multi-output schema returning G, S, and DC components
3. **Given** a FLIM image artifact, **When** agent calls `base.wrapper.axis.relabel_axes(inputs={"image": ref}, params={"mapping": {"T": "H"}})`, **Then** resulting artifact has updated OME metadata with renamed axis

---

### User Story 3 - Dynamic Functions Enriched with Overlays (Priority: P3)

A LLM agent discovering dynamic functions receives enriched metadata (hints, workflow guidance, better descriptions) that helps it make informed decisions about function selection and chaining.

**Why this priority**: Dynamic discovery from docstrings produces functional but potentially terse or technical descriptions; overlays improve LLM usability without duplicating function implementations.

**Independent Test**: Can be tested by comparing `describe_function()` output for a function with an overlay versus one without, verifying merged fields.

**Acceptance Scenarios**:

1. **Given** an overlay exists for `base.skimage.filters.gaussian`, **When** agent calls `describe_function("base.skimage.filters.gaussian")`, **Then** response includes custom description, tags, and success hints from overlay
2. **Given** an overlay specifies `io_pattern: labels_to_labels` for `base.skimage.morphology.remove_small_objects`, **When** agent calls `describe_function()`, **Then** response shows overridden io_pattern instead of default
3. **Given** a dynamically discovered function without an overlay, **When** agent calls `describe_function()`, **Then** response shows description and schema derived from library introspection

---

### User Story 4 - Legacy Function Names Supported Temporarily (Priority: P4)

Existing workflows that use old wrapper names continue to function during a transition period, with clear deprecation warnings directing users to new names.

**Why this priority**: Breaking existing workflows is unacceptable for user trust, but legacy support should not be permanent.

**Independent Test**: Can be tested by calling a legacy function name and verifying it executes while logging a deprecation warning.

**Acceptance Scenarios**:

1. **Given** a workflow using `base.bioimage_mcp_base.transforms.phasor_from_flim`, **When** agent calls this function, **Then** system redirects to `base.wrapper.phasor.phasor_from_flim` with deprecation notice
2. **Given** multiple legacy function calls in a session, **When** each is executed, **Then** deprecation warnings are logged and function executes normally

---

### Edge Cases

- What happens when an overlay references a dynamically discovered function that no longer exists (library updated)?
  - System logs warning during manifest load, overlay is ignored
- What happens when a user calls a thin wrapper name that was removed?
  - If dynamic equivalent exists, return helpful error with suggested replacement
  - If no equivalent, return clear error stating function was removed
- What happens when dynamic discovery fails for a module?
  - System logs error, continues with other modules, includes diagnostic info in `doctor` output

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: No changes to MCP tool signatures. Function IDs change (internal), documented in migration notes.
- **Artifact I/O**: All I/O continues through typed artifact references (BioImageRef, LabelImageRef). Adapters handle array ↔ artifact conversion.
- **Isolation**: All functions run in `bioimage-mcp-base` tool environment via subprocess. No changes to isolation model.
- **Reproducibility**: Workflow recordings will use new function IDs. Legacy recordings can be replayed via redirect mappings.
- **Safety/observability**: Deprecation warnings logged. Overlay merge failures logged as warnings. Full test coverage for overlay merging.

### Functional Requirements

- **FR-001**: System MUST remove 15 thin wrapper functions from static manifest and rely on dynamic discovery for equivalent functionality
- **FR-002**: System MUST rename 10 essential wrapper functions to `base.wrapper.<category>.<function>` namespace
- **FR-003**: System MUST support `function_overlays` section in manifest.yaml that merges metadata into dynamically discovered functions
- **FR-004**: System MUST deep-merge overlay fields (description, tags, io_pattern, hints, params_override) with discovered function schemas
- **FR-005**: System MUST provide legacy redirects for renamed wrapper functions during transition period (until v1.0.0)
- **FR-006**: System MUST expose dynamic functions via `list_tools(path="base.skimage")` returning hierarchical function listing
- **FR-007**: System MUST propagate OME metadata (axes, physical_pixel_sizes, shape) through adapter execution for dynamically discovered functions
- **FR-008**: System MUST validate that all overlay fn_id references match existing dynamically discovered functions during manifest load

### Essential Wrappers to Retain

The following 10 functions provide significant value beyond thin wrapping:

| Category | Function | Purpose |
|----------|----------|---------|
| I/O Bridging | `base.wrapper.io.convert_to_ome_zarr` | Format bridging for pipeline processing |
| I/O Bridging | `base.wrapper.io.export_ome_tiff` | Format bridging with dtype handling |
| Axis Operations | `base.wrapper.axis.relabel_axes` | OME metadata synchronization |
| Axis Operations | `base.wrapper.axis.squeeze` | OME metadata synchronization |
| Axis Operations | `base.wrapper.axis.expand_dims` | OME metadata synchronization |
| Axis Operations | `base.wrapper.axis.moveaxis` | OME metadata synchronization |
| Axis Operations | `base.wrapper.axis.swap_axes` | OME metadata synchronization |
| Phasor Analysis | `base.wrapper.phasor.phasor_from_flim` | Multi-output orchestration (G, S, DC) |
| Phasor Analysis | `base.wrapper.phasor.phasor_calibrate` | Multi-input handling |
| Preprocessing | `base.wrapper.denoise.denoise_image` | Per-plane processing hub |

### Thin Wrappers to Remove

The following 15 functions are thin passthroughs that will be replaced by dynamic discovery:

1. `base.bioimage_mcp_base.transforms.resize` → `base.skimage.transform.resize`
2. `base.bioimage_mcp_base.transforms.rescale` → `base.skimage.transform.rescale`
3. `base.bioimage_mcp_base.transforms.rotate` → `base.skimage.transform.rotate`
4. `base.bioimage_mcp_base.preprocess.gaussian` → `base.skimage.filters.gaussian`
5. `base.bioimage_mcp_base.preprocess.median` → `base.skimage.filters.median`
6. `base.bioimage_mcp_base.preprocess.bilateral` → `base.skimage.restoration.denoise_bilateral`
7. `base.bioimage_mcp_base.preprocess.unsharp_mask` → `base.skimage.filters.unsharp_mask`
8. `base.bioimage_mcp_base.preprocess.sobel` → `base.skimage.filters.sobel`
9. `base.bioimage_mcp_base.preprocess.threshold_otsu` → `base.skimage.filters.threshold_otsu`
10. `base.bioimage_mcp_base.preprocess.threshold_yen` → `base.skimage.filters.threshold_yen`
11. `base.bioimage_mcp_base.preprocess.morph_opening` → `base.skimage.morphology.opening`
12. `base.bioimage_mcp_base.preprocess.morph_closing` → `base.skimage.morphology.closing`
13. `base.bioimage_mcp_base.preprocess.remove_small_objects` → `base.skimage.morphology.remove_small_objects`
14. `base.bioimage_mcp_base.preprocess.denoise_nl_means` → `base.skimage.restoration.denoise_nl_means`
15. `base.bioimage_mcp_base.preprocess.equalize_adapthist` → `base.skimage.exposure.equalize_adapthist`

### Edge Case Functions

| Function | Issue | Resolution |
|----------|-------|------------|
| `crop` | No direct library equivalent | Retain as `base.wrapper.transform.crop` |
| `normalize_intensity` | Custom percentile logic | Retain as `base.wrapper.preprocess.normalize_intensity` |
| `project_sum/max` | Requires axis parameter handling | Retain as `base.wrapper.transform.project_*` |
| `flip/pad` | No existing dynamic adapter | Retain as `base.wrapper.transform.*` |

### Key Entities

- **FunctionOverlay**: Configuration object specifying fields to merge into a dynamically discovered function (description, tags, io_pattern, hints, params_override)
- **LegacyRedirect**: Mapping from old function ID to new function ID for backward compatibility
- **DynamicSource**: Configuration for adapter-based library introspection (adapter type, prefix, modules list)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Static manifest function count reduced from 31 to 16 (10 essential + 6 edge cases)
- **SC-002**: `list_tools(path="base.skimage")` returns 50+ dynamically discovered functions
- **SC-003**: `describe_function("base.skimage.filters.gaussian")` returns schema with merged overlay hints within 100ms (warm cache)
- **SC-004**: All existing integration tests pass with updated function names (no functional regressions)
- **SC-005**: All functions follow consistent `base.<source>.<module>.<func>` naming pattern
- **SC-006**: Legacy function redirects work for all renamed/removed wrappers during transition period
- **SC-007**: 100% of thin wrapper functionality covered by dynamic discovery equivalents
- **SC-008**: `list_tools()` and `search_functions()` return results within 200ms (cold start)

## Assumptions

- Dynamic discovery adapters (skimage, scipy, phasorpy) are already implemented and functional
- Existing adapter execution handles array ↔ artifact conversion correctly
- Library versions in lockfile include all functions that thin wrappers currently expose
- OME metadata propagation in adapters can be enhanced without breaking existing behavior

## Dependencies

- Existing dynamic discovery infrastructure (adapters, introspection)
- Manifest loader supporting new `function_overlays` schema
- SQLite registry index for function search

## Out of Scope

- In-memory pipeline optimization (documented as future enhancement)
- New adapter implementations beyond existing skimage/scipy/phasorpy
- Changes to Cellpose tool pack (separate environment)
- Security sandboxing beyond existing subprocess isolation
