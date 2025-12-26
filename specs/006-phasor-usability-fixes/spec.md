# Feature Specification: Phasor Workflow Usability Fixes

**Feature Branch**: `006-phasor-usability-fixes`  
**Created**: 2025-12-26  
**Status**: Draft  
**Input**: User description: "Fix issues identified in phasor_workflow_usability_report.md. For issue 4, package the bioio-bioformats plugin"

## Clarifications

### Session 2025-12-26

- Q: How should phasor coordinates be stored as artifacts? → A: 2-channel BioImageRef (G as channel 0, S as channel 1)
- Q: What is the IO reader fallback priority order? → A: bioio-ome-tiff → bioio-bioformats → tifffile (lightweight first)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tool Discovery Works (Priority: P1)

A scientist wants to explore what analysis capabilities are available in Bioimage-MCP. They use the discovery tools to list available tools and search for specific functionality like "phasor" or "segmentation".

**Why this priority**: Discovery is the entry point to the entire system. If users cannot discover tools, they cannot use the platform at all. This is a critical infrastructure fix that blocks all other workflows.

**Independent Test**: Can be tested by calling `list_tools` and `search_functions` and receiving valid paginated responses instead of ServerSession errors.

**Acceptance Scenarios**:

1. **Given** a fresh MCP session, **When** user calls `list_tools`, **Then** system returns a paginated list of available tools without errors
2. **Given** a fresh MCP session, **When** user calls `search_functions` with query "phasor", **Then** system returns matching functions with their summaries
3. **Given** an MCP session, **When** user calls any discovery endpoint, **Then** no `AttributeError: 'ServerSession' object has no attribute 'id'` occurs

---

### User Story 2 - Function Schema Introspection (Priority: P1)

A scientist finds a tool they want to use and needs to understand what parameters it requires. They use `describe_function` to get the full parameter schema including required inputs, optional parameters, and expected formats.

**Why this priority**: Without schema introspection, users must guess parameters or read source code, making the platform unusable for practical workflows. This is tied with discovery as a foundational capability.

**Independent Test**: Can be tested by calling `describe_function("base.phasor_from_flim")` and receiving a complete schema with all parameters documented.

**Acceptance Scenarios**:

1. **Given** a valid function ID like `base.phasor_from_flim`, **When** user calls `describe_function`, **Then** system returns a complete parameter schema with all properties defined
2. **Given** a function with required parameters, **When** user requests its schema, **Then** the schema clearly indicates which parameters are required vs optional
3. **Given** a function with typed parameters, **When** user requests its schema, **Then** parameter types, descriptions, and defaults are included

---

### User Story 3 - Phasor Calibration Workflow (Priority: P2)

A scientist has computed raw phasor coordinates from a FLIM dataset and a reference standard (e.g., Fluorescein). They need to calibrate the sample phasors using the reference to obtain quantitatively meaningful G/S coordinates for biological interpretation.

**Why this priority**: Raw uncalibrated phasors have limited scientific utility. Calibration is essential for quantitative FLIM analysis, but the system is usable for other workflows without it.

**Independent Test**: Can be tested by computing phasors for both sample and reference, then applying calibration to get calibrated coordinates.

**Acceptance Scenarios**:

1. **Given** raw phasor coordinates from a sample and a known reference standard, **When** user applies calibration, **Then** system returns calibrated G/S coordinates as a 2-channel BioImageRef (G in channel 0, S in channel 1)
2. **Given** a reference with known lifetime (e.g., Fluorescein at 4.04 ns), **When** user specifies the reference lifetime, **Then** calibration uses this value to compute the phase shift and modulation correction
3. **Given** phasor data at a specific harmonic, **When** user calibrates, **Then** the calibration is applied at the same harmonic

---

### User Story 4 - OME-TIFF Compatibility with bioio-bioformats (Priority: P2)

A scientist has microscopy data in OME-TIFF format that uses advanced metadata tags (like `AnnotationRef`). They want to load this data without errors and preserve all available metadata.

**Why this priority**: Data loading is fundamental, but the current fallback to tifffile works for most datasets. Adding bioio-bioformats as a packaged plugin provides better compatibility without blocking existing workflows.

**Independent Test**: Can be tested by loading `datasets/FLUTE_FLIM_data_tif/Embryo.tif` through the bioio-bioformats reader and verifying metadata is preserved.

**Acceptance Scenarios**:

1. **Given** an OME-TIFF file with AnnotationRef metadata tags, **When** user loads it with bioio-bioformats, **Then** file loads without errors
2. **Given** a FLIM dataset with time dimension, **When** loaded through bioio-bioformats, **Then** axis metadata is correctly parsed (not inferred)
3. **Given** bioio-bioformats plugin is available, **When** user loads OME-TIFF, **Then** system attempts bioio-ome-tiff first, then bioio-bioformats, then tifffile as final fallback

---

### Edge Cases

- What happens when `describe_function` is called with an invalid function ID?
  - System returns a clear error message indicating the function was not found
- What happens when calibration reference has different dimensions than sample?
  - System returns an error explaining the dimension mismatch
- What happens when bioio-bioformats cannot read a specific file format?
  - System falls back to tifffile with a warning about potential metadata loss
- What happens when phasor calculation encounters NaN/Inf values (e.g., zero-intensity pixels)?
  - System returns NaN values in G/S channels for zero-intensity pixels; downstream functions (plotting, calibration) must handle NaN appropriately

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: Fixes to discovery endpoints (`list_tools`, `search_functions`, `describe_function`) must maintain existing API contracts. No breaking changes to response shapes.
- **Artifact I/O**: Phasor coordinates are stored as 2-channel `BioImageRef` artifacts (channel 0 = G, channel 1 = S), reusing existing artifact infrastructure. All outputs as file-backed artifacts.
- **Isolation**: 
  - Discovery/schema fixes are in core server (no new env)
  - Calibration functionality added to `base` tool pack
  - bioio-bioformats added to `base` environment dependencies
- **Reproducibility**: Calibration operations must record reference parameters (known lifetime, harmonic) in workflow provenance
- **Safety/observability**: All fixes must include unit tests and contract tests. Discovery errors must produce helpful diagnostics.

### Functional Requirements

- **FR-001**: System MUST resolve the ServerSession attribute error in discovery endpoints
- **FR-002**: System MUST return complete parameter schemas from `describe_function`, reflecting the underlying Pydantic models
- **FR-003**: System MUST provide a mechanism to calibrate raw phasor coordinates using a reference standard
- **FR-004**: System MUST include bioio-bioformats as an available reader plugin in the base environment
- **FR-005**: System MUST attempt IO readers in priority order: bioio-ome-tiff → bioio-bioformats → tifffile, falling back on failure
- **FR-006**: Calibration MUST accept the known lifetime of the reference standard as a parameter
- **FR-007**: Calibration MUST support specifying the harmonic for multi-harmonic phasor data
- **FR-008**: Discovery endpoints MUST return paginated responses for large result sets
- **FR-009**: Phasor coordinate outputs MUST be stored as 2-channel BioImageRef (G in channel 0, S in channel 1)
- **FR-010**: Function schema responses MUST include an `introspection_source` field indicating the schema origin ("pydantic", "docstring", or "manual")

### Key Entities *(include if feature involves data)*

- **PhasorCoordinates**: G (real) and S (imaginary) components of phasor transform, stored as a 2-channel BioImageRef (channel 0 = G, channel 1 = S), associated with spatial coordinates and harmonic number
- **CalibrationReference**: Known lifetime value, reference phasor coordinates (as 2-channel BioImageRef), harmonic
- **FunctionSchema**: Complete description of a function's inputs, outputs, parameters with types and documentation

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can call `list_tools` and `search_functions` without errors in a fresh session
- **SC-002**: `describe_function("base.phasor_from_flim")` returns a schema with at least 3 documented parameters: `inputs` (required BioImageRef), `harmonic` (integer, default 1), and `time_axis` (string or integer specifying the time/histogram dimension)
- **SC-003**: Users can complete a phasor calibration workflow (compute reference phasors → compute sample phasors → calibrate) end-to-end
- **SC-004**: OME-TIFF files with AnnotationRef tags load successfully when bioio-bioformats is available
- **SC-005**: All new functionality has corresponding test coverage (unit + contract tests)
- **SC-006**: Existing tests continue to pass after fixes (no regressions)
