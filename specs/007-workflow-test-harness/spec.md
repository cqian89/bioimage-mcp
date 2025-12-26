# Feature Specification: Axis Manipulation Tools, LLM Guidance Hints & Workflow Test Harness

**Feature Branch**: `007-workflow-test-harness`  
**Created**: 2025-12-26  
**Status**: Draft  
**Input**: User description: "P0 Implementation: Axis manipulation tools and automated MCP workflow test harness based on next_steps.md priorities"

## Overview

This specification addresses four critical items from the project roadmap based on phasor FLIM workflow testing and architecture review:

1. **Axis Manipulation Tools (P0)**: A suite of functions enabling users to relabel, reorder, squeeze, and expand dimensions in microscopy images. These tools unblock FLIM phasor analysis workflows where time bins are stored in non-standard axis positions.

2. **Automated MCP Workflow Test Harness (P0)**: A testing framework that simulates LLM tool-calling sequences, enabling developers to verify end-to-end workflows without manual testing after each code change.

3. **LLM Guidance Hints (P1)**: Structured hints in tool responses that guide LLMs through workflows by providing input requirements, next-step suggestions, and corrective error guidance.

4. **Rich Artifact Metadata (P2)**: Enhanced metadata returned with artifact references, including shape, dtype, axes configuration, and file metadata, reducing the need for separate inspection calls.

**Why This Matters**: Current FLIM workflows fail because time bins are stored in the Z axis instead of T axis, and there's no systematic way to test that multi-step MCP workflows work correctly. Additionally, LLMs lack context about tool requirements and workflow sequences, leading to incorrect tool calls and wasted retry cycles. This specification provides the axis manipulation primitives, testing infrastructure, workflow guidance, and rich context needed to make bioimage-mcp truly usable for LLM-driven analysis.

## Clarifications

### Session 2025-12-26

- Q: How should the system handle downstream tools that don't support reading from OME-Zarr (`zarr-temp`)? → A: Per-tool declared supported storage types; orchestrator chooses/auto-converts when needed.
- Q: Where should per-tool supported storage types be declared and surfaced? → A: In `manifest.yaml` and exposed via `describe_function` (manifest is source of truth).
- Q: How should `base.relabel_axes` apply `axis_mapping` when keys/values overlap (e.g., `{\"Z\":\"T\",\"T\":\"Z\"}`)? → A: Apply mapping atomically (simultaneous rename) so swaps are well-defined.
- Q: What should `base.expand_dims` set for the new axis's physical size metadata by default? → A: `None` (unknown / not applicable).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Axis Relabeling for FLIM Analysis (Priority: P0)

A scientist loads a FLIM dataset that has time bins stored in the Z axis (a common vendor-specific convention). They need to relabel the Z axis as T (time) before running phasor analysis, which expects a T axis for time bins.

**Why this priority**: Without axis manipulation tools, users cannot prepare their FLIM data for phasor analysis. This directly blocks the core use case identified in phasor workflow testing. The FLUTE dataset has time bins in Z, single-sample T, and `base.phasor_from_flim` requires time bins in T.

**Independent Test**: Can be tested by loading Embryo.tif from FLUTE dataset (shape [1, 1, 56, 512, 512] with axes TCZYX), relabeling axes to swap Z↔T, and verifying `base.phasor_from_flim` executes successfully.

**Acceptance Scenarios**:

1. **Given** a BioImageRef with time bins stored in Z axis (56 samples) and single-sample T axis, **When** user calls `base.relabel_axes` with mapping {"Z": "T", "T": "Z"}, **Then** output artifact has 56 time bins in T axis and single sample in Z axis
2. **Given** a relabeled image with proper T axis containing 56 time bins, **When** user runs `base.phasor_from_flim`, **Then** function executes without "not enough samples in dimension T" error
3. **Given** a BioImageRef with axes "CZYX", **When** user relabels {"Y": "Z", "Z": "Y"}, **Then** output has axes "CZXY" (Y and Z meanings swapped)

---

### User Story 2 - Dimension Manipulation for Pipeline Compatibility (Priority: P0)

A scientist has a 2D image that needs to be processed by a function expecting 3D input (or vice versa). They need to squeeze singleton dimensions or expand dimensions to match function input requirements.

**Why this priority**: Dimension mismatches are a common source of pipeline failures. Providing squeeze/expand_dims enables users to adapt data for different processing steps without re-exporting from acquisition software.

**Independent Test**: Can be tested by loading a 3D image with singleton Z, squeezing it, and verifying the output is 2D with correct axis labels.

**Acceptance Scenarios**:

1. **Given** a BioImageRef with shape [1, 512, 512] and axes "ZYX", **When** user calls `base.squeeze` with axis=0, **Then** output has shape [512, 512] and axes "YX"
2. **Given** a BioImageRef with shape [512, 512, 3] and axes "YXC", **When** user calls `base.squeeze` without specifying axis, **Then** system returns error "No singleton axes to squeeze"
3. **Given** a 2D BioImageRef with shape [512, 512] and axes "YX", **When** user calls `base.expand_dims` with axis=0 and new_axis_name="Z", **Then** output has shape [1, 512, 512] and axes "ZYX"
4. **Given** a BioImageRef, **When** user calls `base.expand_dims` with axis=-1 and new_axis_name="C", **Then** new singleton dimension is added at the last position

---

### User Story 3 - Axis Reordering for Algorithm Requirements (Priority: P2)

A scientist needs to reorder axes in their image to match the expected input format of a processing algorithm. For example, moving the channel axis from position 0 to position 2 for a function that expects channels-last format.

**Why this priority**: Axis order requirements vary between algorithms (channels-first vs channels-last, time before/after spatial dims). This enables interoperability but is less critical than relabeling for FLIM workflows since most bioimage tools use standard TCZYX ordering.

**Independent Test**: Can be tested by loading a CZYX image, moving C axis to last position, and verifying the output axis order and data integrity.

**Acceptance Scenarios**:

1. **Given** a BioImageRef with axes "CZYX", **When** user calls `base.moveaxis` with source=0, destination=2, **Then** output has axes "ZYCX" and data is correctly transposed
2. **Given** a BioImageRef with axes "TYXC", **When** user calls `base.moveaxis` with source=-1, destination=0, **Then** output has axes "CTYX"
3. **Given** a BioImageRef with axes "ZYX", **When** user calls `base.swap_axes` with axis1="Z", axis2="Y", **Then** output has axes "YZX" and both data array and axis metadata reflect the swap
4. **Given** a BioImageRef, **When** user swaps two axes and then swaps them back, **Then** output is identical to original input (operation is reversible)

---

### User Story 4 - Automated Workflow Testing for Developers (Priority: P0)

A developer makes changes to the MCP server and needs to verify that common workflows still work end-to-end. They run an automated test suite that simulates LLM tool calling sequences through the full discovery-to-execution pipeline.

**Why this priority**: Without automated workflow testing, developers cannot safely iterate on the codebase. Every change to the MCP API, artifact handling, or runtime execution requires manual testing of complex multi-step workflows, which is error-prone and time-consuming.

**Independent Test**: Can be tested by running `pytest tests/integration/test_workflows.py` and seeing pass/fail results for each workflow scenario without needing to run an actual LLM or MCP client.

**Acceptance Scenarios**:

1. **Given** an MCP test harness, **When** developer runs phasor FLIM workflow test, **Then** test executes the full sequence: `search_functions("phasor FLIM")` → `activate_functions(["base.relabel_axes", "base.phasor_from_flim"])` → `describe_function("base.relabel_axes")` → `call_tool("base.relabel_axes")` → `call_tool("base.phasor_from_flim")`
2. **Given** a workflow test with 5 steps, **When** step 3 fails (e.g., invalid parameters), **Then** test reports which step failed with clear error information including tool name, parameters, and error message
3. **Given** a workflow test, **When** developer runs test without tool environments installed, **Then** test runs in mock mode and validates orchestration logic (tool selection, parameter passing, artifact flow)
4. **Given** test case definitions in YAML format, **When** developer adds a new cellpose workflow test, **Then** they can define: input artifacts, tool call sequence, expected output types, and assertions without writing Python code

---

### User Story 5 - Systematic Tool Validation (Priority: P2)

A developer wants to ensure every registered tool has a valid schema and can be called with known-good inputs. They run a parametrized test that validates all tools in the registry conform to MCP contracts.

**Why this priority**: Ensures tool quality across the entire toolkit, preventing runtime errors from malformed schemas or incorrect function signatures. Less critical than workflow testing because individual tool failures are easier to debug than multi-step workflow failures.

**Independent Test**: Can be tested by running a parametrized test that iterates over all registered functions and validates schemas without executing tool logic.

**Acceptance Scenarios**:

1. **Given** all registered functions in the base toolkit, **When** test calls describe_function for each, **Then** every function returns a valid JSON schema with required fields: id, summary, inputs, outputs, params_schema
2. **Given** test case definitions for base.gaussian_blur with multiple parameter sets, **When** test calls the tool with each parameter set, **Then** tool executes successfully and returns expected output type (BioImageRef)
3. **Given** a new tool added to the registry, **When** developer runs the validation suite, **Then** test automatically discovers and validates the new tool without code changes
4. **Given** all registered tools, **When** validation test runs, **Then** test reports: total tools tested, schema validation pass/fail count, and any tools missing test cases

---

### User Story 6 - LLM Discovers Input Requirements for Tools (Priority: P1)

An LLM queries a tool's requirements before calling it. The describe_function response includes not just parameter schema, but also:
- What input artifact types are expected
- What axis configurations work best (e.g., "FLIM data needs T axis with multiple samples")
- Preprocessing hints if the data might not be in the right format

**Why this priority**: Without clear input requirements, LLMs make incorrect tool calls, causing failures and requiring multiple retries. This wastes user time and creates frustration.

**Independent Test**: Can be tested by calling describe_function("base.phasor_from_flim") and verifying the response includes inputs schema with expected_axes and preprocessing_hint fields.

**Acceptance Scenarios**:

1. **Given** fn_id "base.phasor_from_flim", **When** LLM calls describe_function, **Then** response includes `inputs` object with dataset field containing: type (BioImageRef), required (true), description, expected_axes (["T", "Y", "X"]), and preprocessing_hint
2. **Given** a function with specific axis requirements, **When** describe_function is called, **Then** the `expected_axes` field lists the expected axis order for optimal processing
3. **Given** a function that commonly fails due to data format issues, **When** describe_function is called, **Then** the `preprocessing_hint` field explains how to prepare data correctly

---

### User Story 7 - LLM Receives Next-Step Guidance After Tool Execution (Priority: P1)

After a tool executes successfully, the LLM receives guidance about what to do next. For example, after computing raw phasors, the response suggests calibration as the next step.

**Why this priority**: LLMs don't inherently know the typical workflow sequence in bioimage analysis. Providing next-step hints enables LLMs to guide users through complete analysis pipelines without requiring domain expertise.

**Independent Test**: Can be tested by calling `base.phasor_from_flim` and verifying the response includes a `hints` object with `next_steps` array.

**Acceptance Scenarios**:

1. **Given** successful execution of base.phasor_from_flim, **When** result is returned, **Then** response includes `hints.next_steps` array with at least one suggested function (e.g., base.phasor_calibrate)
2. **Given** a next_step suggestion, **Then** it includes: fn_id, reason (why this is the next step), and required_inputs (what additional data is needed)
3. **Given** successful execution, **When** result is returned, **Then** response includes `hints.common_issues` array explaining potential problems with the output (e.g., "Raw phasors are uncalibrated")

---

### User Story 8 - LLM Receives Corrective Hints on Errors (Priority: P2)

When a tool fails due to a correctable problem (e.g., wrong axis configuration), the error response includes a diagnosis and suggested fix that the LLM can execute.

**Why this priority**: Error recovery is important for robust workflows, but P1 items (successful path guidance) are more impactful for initial usability.

**Independent Test**: Can be tested by calling `base.phasor_from_flim` on an image with time bins in Z axis and verifying the error response includes a suggested fix.

**Acceptance Scenarios**:

1. **Given** `base.phasor_from_flim` fails with "not enough samples in axis T", **When** error is returned, **Then** response includes `hints.diagnosis` explaining the likely cause
2. **Given** a correctable error, **When** error response is returned, **Then** `hints.suggested_fix` includes: fn_id (tool to fix the problem), params (suggested parameters), and explanation (why this fixes it)
3. **Given** an error related to axis configuration, **When** error is returned, **Then** `hints.related_metadata` includes: detected_axes, shape, and any relevant OME hints from the input file

---

### User Story 9 - Rich Artifact Metadata Returned from I/O Operations (Priority: P2)

When an image is loaded or processed, the artifact reference includes rich metadata that helps the LLM understand the data without making additional calls.

**Why this priority**: Reduces round-trips and context usage. The LLM can inspect artifact metadata to diagnose issues instead of needing separate describe/inspect calls.

**Independent Test**: Can be tested by loading Embryo.tif and verifying the artifact reference includes shape, dtype, axes, axes_inferred flag, and physical_pixel_sizes.

**Acceptance Scenarios**:

1. **Given** a BioImageRef returned from any tool, **Then** it includes metadata object with: shape, dtype, axes, physical_pixel_sizes
2. **Given** an image loaded from a FLIM TIFF file, **When** artifact is returned, **Then** metadata includes `axes_inferred` boolean indicating whether axes were guessed or read from file metadata
3. **Given** an image with vendor-specific metadata, **When** artifact is returned, **Then** metadata includes `file_metadata` object with ome_xml_summary and custom_attributes extracted from the file
4. **Given** metadata indicates axes_inferred=true, **Then** LLM can proactively suggest axis verification before processing

---

### Edge Cases

#### Axis Manipulation Edge Cases

- **Duplicate axis names after relabeling**:
  - What happens: User tries to relabel {"Z": "Y"} when Y already exists
  - Expected: System returns error "Cannot relabel Z to Y: axis Y already exists"
  
- **Relabel non-existent axis**:
  - What happens: User tries to relabel {"W": "T"} but image has no W axis
  - Expected: System returns error "Axis W not found in image with axes TCZYX"

- **Squeeze non-singleton axis**:
  - What happens: User calls squeeze(axis=2) on axis with size 56
  - Expected: System returns error "Cannot squeeze axis Z (index 2) with size 56 > 1"

- **Squeeze all singleton axes**:
  - What happens: User calls squeeze() without axis argument on image with shape [1, 1, 3, 512, 512]
  - Expected: All singleton axes removed, output shape [3, 512, 512], axes "CYX"

- **Moveaxis source equals destination**:
  - What happens: User calls moveaxis(source=2, destination=2)
  - Expected: System returns input unchanged (no-op), no error

- **Moveaxis with negative indices**:
  - What happens: User calls moveaxis(source=-1, destination=0)
  - Expected: Last axis moved to first position, correctly handled

- **Expand dims with duplicate axis name**:
  - What happens: User calls expand_dims(axis=0, new_axis_name="Z") but Z already exists
  - Expected: System returns error "Axis name Z already exists in axes CZYX"

- **Swap same axis**:
  - What happens: User calls swap_axes(axis1="Y", axis2="Y")
  - Expected: System returns input unchanged or error "Cannot swap axis with itself"

- **Physical metadata preservation**:
  - What happens: User reorders axes on image with pixel size metadata
  - Expected: Physical size metadata is reordered to match new axis order

#### Test Harness Edge Cases

- **Workflow test with missing tool environment**:
  - What happens: Cellpose test runs but cellpose environment not installed
  - Expected: Test uses mock execution to verify orchestration logic, clearly marks as "mock mode", skips actual tool execution

- **Test case references non-existent artifact**:
  - What happens: YAML test case references "datasets/missing.tif"
  - Expected: Test fails with clear error "Input artifact not found: datasets/missing.tif"

- **Workflow step depends on previous step output**:
  - What happens: Step 2 uses output artifact from step 1
  - Expected: Test harness automatically wires artifact references between steps

- **Mock execution returns wrong artifact type**:
  - What happens: Mock is configured to return TableRef but function signature expects BioImageRef
  - Expected: Test fails with type mismatch error

- **Parametrized test discovers new tool mid-run**:
  - What happens: Tool registry updated while parametrized test is collecting test cases
  - Expected: Test uses snapshot of registry at collection time, consistent results

- **YAML test case has syntax error**:
  - What happens: Invalid YAML in test case file
  - Expected: Test fails during collection phase with clear parsing error message

#### LLM Guidance Hints Edge Cases

- **No next steps available**:
  - What happens: Tool has no logical next step (e.g., export function)
  - Expected: hints.next_steps is empty array [], not missing field

- **Multiple possible next steps**:
  - What happens: Tool output can be used by several downstream functions
  - Expected: hints.next_steps contains all valid options, ordered by relevance

- **Error without corrective hint**:
  - What happens: Tool fails with an error that has no known fix (e.g., out of memory)
  - Expected: hints.diagnosis explains the error, hints.suggested_fix is null

- **Axis inference disagrees with file metadata**:
  - What happens: File has ambiguous axis metadata (e.g., OME says ZYX but custom attribute says T is time)
  - Expected: axes_inferred=true, and file_metadata.custom_attributes includes the conflicting info

- **Large file metadata truncation**:
  - What happens: OME-XML is very large (>10KB)
  - Expected: file_metadata.ome_xml_summary is truncated with "..." and byte count

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

#### 1. Stable MCP Surface (Anti-Context-Bloat)

**Impact**: No changes to MCP endpoints or pagination behavior. Axis manipulation tools are new functions exposed via existing `list_tools`, `search_functions`, and `describe_function` APIs.

**Compliance**:
- Axis tools discovered via standard function discovery (paginated)
- Tool schemas returned only via `describe_function(fn_id="base.relabel_axes")`, not in summary listings
- Test harness simulates discovery flow, validating that new tools integrate without protocol changes

#### 2. Isolated Tool Execution

**Impact**: Axis manipulation tools run in `bioimage-mcp-base` environment. Test harness must work with and without tool environments installed.

**Compliance**:
- Axis tools implemented in `tools/base/bioimage_mcp_base/axis_ops.py`, executed via subprocess
- Test harness provides mock execution mode to test orchestration without spawning subprocesses
- Crashes in axis manipulation code (e.g., invalid axis index) do not affect MCP server process

#### 3. Artifact References Only

**Impact**: All axis manipulation inputs/outputs are typed artifact references. Test harness validates artifact flow through workflows.

**Compliance**:
- All axis tools take `BioImageRef` input and return `BioImageRef` output
- Axis metadata (labels, physical size) updated in output artifact's OME-TIFF metadata
- Test harness assertions can verify artifact types without downloading/inspecting large arrays

#### 4. Reproducibility & Provenance

**Impact**: Axis operations must be recorded in workflow provenance for replay. Test harness validates that workflows can be replayed.

**Compliance**:
- All axis tool parameters (axis mappings, indices, new axis names) captured in run records
- Workflow test harness includes test for `replay_workflow` functionality
- Axis transformations are deterministic: same input + params = same output

#### 5. Safety & Observability

**Impact**: All new axis tools and test utilities must have unit tests. Test harness must provide clear error reporting.

**Compliance**:
- Minimum 2 test cases per axis tool (10 tests for 5 tools)
- Test harness includes structured error reporting: step number, tool name, parameters, error message
- Mock execution mode allows testing without external dependencies
- All axis tools validate parameters before execution (fail-fast on invalid axis names/indices)

#### 6. Test-Driven Development

**Impact**: Implementation follows red-green-refactor cycle.

**Compliance**:
- Write failing tests for each axis tool before implementation
- Test harness tests written before MCPTestClient implementation
- Contract tests validate axis tool schemas match implementations

### Functional Requirements

#### Axis Manipulation Tools

- **FR-001**: System MUST provide a `base.relabel_axes` function that renames axis labels without moving data
  - Inputs: BioImageRef, axis_mapping (dict mapping old axis names to new names)
  - Outputs: BioImageRef with updated axis labels
  - Behavior: Apply the mapping atomically (simultaneous rename) so swaps like `{\"Z\":\"T\",\"T\":\"Z\"}` are well-defined
  - Validation: Reject mappings that reference non-existent axes or that result in duplicate axis names after applying the mapping

- **FR-002**: System MUST provide a `base.squeeze` function that removes singleton dimensions
  - Inputs: BioImageRef, optional axis (int or str) to squeeze
  - Outputs: BioImageRef with singleton dimension(s) removed
  - Behavior: If axis not specified, remove all singleton dimensions
  - Validation: Reject attempts to squeeze non-singleton axes

- **FR-003**: System MUST provide a `base.expand_dims` function that adds a new singleton dimension at a specified position
  - Inputs: BioImageRef, axis (int index or position), new_axis_name (str)
  - Outputs: BioImageRef with new singleton dimension
  - Validation: Reject duplicate axis names, invalid axis positions

- **FR-004**: System MUST provide a `base.moveaxis` function that reorders axes
  - Inputs: BioImageRef, source (int or str), destination (int)
  - Outputs: BioImageRef with reordered axes and transposed data
  - Behavior: Move axis from source position to destination position
  - Validation: Handle negative indices, reject out-of-bounds indices

- **FR-005**: System MUST provide a `base.swap_axes` function that swaps two axis positions
  - Inputs: BioImageRef, axis1 (int or str), axis2 (int or str)
  - Outputs: BioImageRef with swapped axes
  - Behavior: Convenience wrapper for moveaxis that swaps two axes
  - Validation: Reject invalid axis names/indices

- **FR-006**: All axis tools MUST preserve physical size metadata when applicable
  - When axes are reordered, physical_pixel_sizes must be reordered to match
  - When axes are removed (squeeze), corresponding physical sizes removed
  - When axes are added (expand_dims), physical size for new axis defaults to `None` (unknown / not applicable)

- **FR-007**: All axis tools MUST update axis labels in output artifact metadata
  - Output OME-TIFF metadata must reflect new axis configuration
  - Axis order in DimensionOrder field must match actual data layout
  - SizeZ, SizeT, SizeC fields updated if those axes are modified

#### Workflow Test Harness

- **FR-008**: System MUST provide an MCPTestClient class that simulates LLM tool calling
  - Instantiate with temporary artifact store and test config
  - Provide async context manager interface for setup/teardown
  - Support session management (create, resume, export)

- **FR-009**: MCPTestClient MUST support core MCP operations:
  - `list_tools()`: Returns available tools with pagination
  - `search_functions(query, tags, io_in, io_out)`: Searches function registry
  - `activate_functions(fn_ids)`: Filters active function set
  - `describe_function(fn_id)`: Returns full schema for a function
  - `call_tool(fn_id, inputs, params)`: Executes a tool and returns output refs

- **FR-010**: System MUST support mock execution mode to test orchestration without installed tool environments
  - Mock mode configurable per test or per tool call
  - Mocks return predefined artifact references with correct types
  - Validation and parameter checking still performed
  - Clear indication in logs when running in mock mode

- **FR-011**: System MUST provide pytest fixtures for setting up MCP test environments
  - `mcp_test_client`: Configured MCPTestClient with temp artifact store
  - `sample_flim_image`: BioImageRef to Embryo.tif from FLUTE dataset
  - `mock_executor`: Mock subprocess executor for testing without tool environments

- **FR-012**: System MUST support defining test cases in YAML format for data-driven testing
  - YAML schema: test name, description, steps (list of tool calls), assertions
  - Each step: fn_id, inputs (artifact paths or refs from previous steps), params
  - Assertions: output_type, artifact_exists, metadata_contains
  - Support for parametrized tests from single YAML file

- **FR-013**: System MUST provide parametrized tests that validate all registered functions have valid schemas
  - Auto-discover all functions in registry
  - For each function, call describe_function and validate schema structure
  - Check required fields: id, summary, inputs, outputs, params_schema
  - Validate inputs/outputs are recognized artifact types

- **FR-014**: System MUST provide at least one "golden path" workflow test (FLIM phasor analysis)
  - Steps: `search_functions("phasor FLIM")` → `activate_functions(["base.relabel_axes", "base.phasor_from_flim"])` → `describe_function("base.relabel_axes")` → `call_tool("base.relabel_axes")` → `call_tool("base.phasor_from_flim")`
  - Validates full discovery-to-execution flow
  - Uses real FLUTE dataset (Embryo.tif)
  - Asserts: workflow completes, output artifacts exist, output types correct

#### LLM Guidance Hints

- **FR-015**: describe_function responses MUST include an `inputs` object with structured input requirements
  - Each input: type (artifact type), required (boolean), description, expected_axes (list), preprocessing_hint (string, optional), supported_storage_types (list of allowed `storage_type` values, optional)
  - Example: `{"dataset": {"type": "BioImageRef", "required": true, "expected_axes": ["T", "Y", "X"], "preprocessing_hint": "If T has only 1 sample, check if FLIM bins are in Z", "supported_storage_types": ["zarr-temp", "file"]}}`

- **FR-016**: describe_function responses MUST include an `outputs` object describing each output artifact
  - Each output: type (artifact type), description
  - Example: `{"g_image": {"type": "BioImageRef", "description": "Phasor G coordinates (real component)"}}`

- **FR-017**: Successful tool execution responses MUST include a `hints` object with next-step guidance
  - hints.next_steps: array of {fn_id, reason, required_inputs}
  - hints.common_issues: array of strings describing potential problems with output

- **FR-018**: Failed tool execution responses MUST include a `hints` object with corrective guidance
  - hints.diagnosis: string explaining likely cause of failure
  - hints.suggested_fix: {fn_id, params, explanation} or null if no fix available
  - hints.related_metadata: {detected_axes, shape, ome_hint} for axis-related errors

- **FR-019**: Hint definitions MUST be configurable per function in manifest.yaml
  - next_step_hints, error_hints, and input_requirements defined in function schema
  - Input requirements MAY include per-input `supported_storage_types` (e.g., `["zarr-temp", "file"]`)
  - `describe_function` MUST surface the manifest-defined `supported_storage_types` to callers (LLMs and test harness)
  - System can auto-generate some hints from docstrings and type signatures

#### Rich Artifact Metadata

- **FR-020**: All artifact references returned from tool execution MUST include a `metadata` object
  - Required fields: shape (array of ints), dtype (string), axes (string like "TCZYX")
  - Optional fields: axes_inferred (boolean), physical_pixel_sizes (dict), file_metadata (object)

- **FR-021**: When axes are inferred rather than read from file metadata, `axes_inferred` MUST be true
  - Helps LLM identify when axis relabeling may be needed

- **FR-022**: For images loaded from files with OME metadata, `file_metadata` MUST include:
  - ome_xml_summary: concise string summarizing key OME fields (truncated if >1KB)
  - custom_attributes: dict of vendor-specific or non-standard attributes

- **FR-023**: Artifact metadata MUST be included in both success and error responses
  - On error, metadata helps LLM diagnose the issue (e.g., wrong axis configuration)

### Non-Functional Requirements

- **NFR-001**: Axis manipulation operations MUST complete in under 1 second for images up to 100 MB
  - Rationale: Interactive workflows require fast feedback
  - Measurement: Time from call_tool request to output artifact written

- **NFR-002**: Test harness MUST execute workflow tests in under 10 seconds (mock mode) or under 60 seconds (full execution mode)
  - Rationale: Fast test feedback enables iterative development
  - Measurement: Total pytest execution time for `tests/integration/test_workflows.py`

- **NFR-003**: Mock execution mode MUST cover at least 80% of orchestration code paths
  - Rationale: Developers need to test without installing all tool environments
  - Measurement: Code coverage report for MCP API layer when running mock tests

- **NFR-004**: Axis tool error messages MUST include: function name, invalid parameter, and suggested correction
  - Example: "Error in base.squeeze: Cannot squeeze axis Z (index 2) with size 56. Only singleton axes (size 1) can be squeezed."
  - Rationale: Actionable error messages reduce user frustration

### Key Entities

#### AxisMapping
Dictionary mapping source axis names to target axis names for relabeling operations.

**Example**:
```python
{"Z": "T", "T": "Z"}  # Swap Z and T axes
{"Y": "Z", "Z": "Y"}  # Swap Y and Z axes
```

**Constraints**:
- Keys must be existing axis names in the input image
- Mapping is applied atomically (simultaneous rename) so swaps like `{\"Z\":\"T\",\"T\":\"Z\"}` are supported
- Values must not create duplicate axis names after mapping
- Case-sensitive (Z ≠ z)

#### MCPTestClient
Test utility that wraps MCP protocol calls for simulating LLM interactions.

**Responsibilities**:
- Manages temporary artifact store for test isolation
- Provides async interface matching MCP server API
- Supports both real execution and mock execution modes
- Records tool call sequences for debugging

**Usage Pattern**:
```python
async with MCPTestClient() as client:
    # Discovery
    tools = await client.list_tools()
    
    # Function activation
    await client.activate_functions(["base.relabel_axes"])
    
    # Tool execution
    output = await client.call_tool(
        fn_id="base.relabel_axes",
        inputs={"image": image_ref},
        params={"axis_mapping": {"Z": "T", "T": "Z"}}
    )
```

#### WorkflowTestCase
YAML-defined test case with steps, inputs, params, and expected outputs.

**Structure**:
```yaml
test_name: "flim_phasor_workflow"
description: "End-to-end FLIM phasor analysis with axis relabeling"
steps:
  - fn_id: "base.relabel_axes"
    inputs:
      image: "datasets/FLUTE_FLIM_data_tif/Embryo.tif"
    params:
      axis_mapping: {"Z": "T", "T": "Z"}
    output_ref: "relabeled_image"
  
  - fn_id: "base.phasor_from_flim"
    inputs:
      flim_image: "{relabeled_image}"  # Reference to previous step output
    params:
      harmonic: 1
    output_ref: "phasor_result"

assertions:
  - artifact_exists: "phasor_result"
  - output_type: "TableRef"
```

**Features**:
- Steps executed sequentially
- Output references passed between steps using `{ref_name}` syntax
- Assertions checked after all steps complete
- Support for parametrized inputs (multiple test cases from one definition)

#### MockExecutor
Subprocess mock that returns predefined outputs for testing orchestration.

**Responsibilities**:
- Intercepts subprocess calls to tool executors
- Returns predefined artifact references without running actual tools
- Validates that orchestration layer passes correct parameters
- Simulates execution time and resource usage for performance testing

**Configuration**:
```python
mock_executor.register_mock(
    fn_id="base.relabel_axes",
    output_type="BioImageRef",
    output_metadata={"axes": "TCZYX", "shape": [56, 1, 1, 512, 512]}
)
```

## Cross-Environment Artifact Handling

### Problem Statement

Tools run in isolated conda environments as subprocesses. When tool A (in env-base) produces an artifact and tool B (in env-cellpose) needs to consume it, how do we share data efficiently?

### Design Decision

**Chosen approach**: Memory-mapped OME-Zarr temporary files (Option C from next_steps.md)

**Rationale**:
- Simpler than persistent worker processes or IPC/shared memory
- Cross-platform compatible (works on Linux, macOS, Windows)
- Natural fit with OME-Zarr chunked format
- Memory-mapped access means no full copy between processes
- Falls back gracefully to disk I/O when needed

### How It Works

1. **Tool A produces output**:
   - Writes output to temp OME-Zarr directory: `/tmp/bioimage-mcp/{session_id}/{ref_id}/`
   - Returns artifact reference with URI pointing to temp location

2. **MCP server receives artifact reference**:
   - Stores lightweight reference in session artifact index
   - Does NOT load array data into server memory

3. **Tool B consumes input**:
   - Receives artifact URI from MCP server
   - Memory-maps the OME-Zarr chunks (lazy loading)
   - Only loads chunks actually accessed during processing

4. **Session cleanup**:
   - On session end or explicit cleanup, temp directories are removed
   - Explicit `export_artifact` persists to user-specified location before cleanup

### Scope for This Spec

**In scope (MVP)**:
- Artifact references include `storage_type`: "file" or "zarr-temp"
- Tools can read from zarr-temp locations via standard bioio/zarr APIs
- Tool definitions declare supported input `storage_type` values (e.g., `["zarr-temp", "file"]`)
- Orchestrator selects a compatible representation per tool, auto-materializing a temp file representation (e.g., OME-TIFF) when needed and possible
- Any auto-materialization/conversion step is recorded in workflow provenance for replay
- Session cleanup removes temp artifacts

**Out of scope (future)**:
- In-memory LRU cache with spill-to-disk (requires more complex memory management)
- True shared memory between processes (requires platform-specific IPC)
- Lazy/chunked processing for very large (>4GB) datasets

### Constitution Compliance

- **Artifact References Only**: Artifact references still point to files (temp Zarr), not in-memory buffers
- **Isolated Execution**: No shared memory between processes; each process memory-maps independently
- **Reproducibility**: Temp Zarr files can be persisted via export_artifact before cleanup

## Dependencies

### Prerequisites
- **Spec 000 (v0-bootstrap)**: Tool discovery and basic execution infrastructure
- **Spec 002 (base-tool-schema)**: Base toolkit with OME-TIFF I/O
- **Spec 006 (phasor-usability-fixes)**: FLIM phasor functions (to test workflows against)

### External Libraries
- **Axis tools**: `numpy` (array transpose), `bioio` (OME metadata manipulation)
- **Test harness**: `pytest`, `pytest-asyncio`, `pyyaml` (test case loading)

### Test Data
- **FLUTE dataset**: `datasets/FLUTE_FLIM_data_tif/Embryo.tif` for FLIM workflow tests
- **Sample images**: 2D and 3D test images for axis manipulation validation

## Out of Scope

### Explicitly Excluded

1. **Advanced array transformations**: Crop, pad, resize, rotate, flip
   - Rationale: Axis manipulation focuses on metadata/dimension changes, not pixel data transformations
   - Future: Consider in separate "image preprocessing" milestone

2. **Arbitrary axis permutations**: Multi-axis reordering in single operation
   - Rationale: `moveaxis` and `swap_axes` can achieve any permutation through composition
   - Future: Add `transpose(axes_order)` if users find multi-step reordering cumbersome

3. **Automatic axis inference**: Guessing correct axis labels from data shape
   - Rationale: Too error-prone for scientific data (e.g., is [512, 512, 3] YXC or YXZ?)
   - Future: Consider heuristics with confidence scores and user confirmation

4. **Performance optimization**: Lazy evaluation, in-place operations, chunked processing
   - Rationale: Premature optimization; target images are <1 GB
   - Future: Add chunked processing when users report performance issues with large datasets

5. **Test harness UI**: Web dashboard, interactive test explorer, visual diff tools
   - Rationale: Focus on programmatic testing for CI/CD integration
   - Future: Consider Allure or similar reporting tools if manual test inspection becomes bottleneck

6. **Property-based testing**: Hypothesis-style generative tests for axis tools
   - Rationale: Combinatorial explosion of axis configurations; start with targeted test cases
   - Future: Add property tests for critical invariants (e.g., swap(swap(img)) == img)

### Deferred to Future Milestones

1. **Workflow composition DSL**: Higher-level syntax for defining multi-step workflows
   - Current: YAML test cases are imperative (step-by-step)
   - Future: Declarative workflow graphs with automatic dependency resolution

2. **Performance regression testing**: Automated detection of performance degradation
   - Current: Manual timing checks in test logs
   - Future: Persist timing data, alert on >10% slowdown

3. **Snapshot testing**: Record expected outputs and diff against future runs
   - Current: Type and existence assertions only
   - Future: Pixel-level comparison for image outputs (with tolerance for floating-point differences)

4. **Multi-session workflows**: Test cases spanning multiple MCP sessions
   - Current: All tests run in single session
   - Future: Test session export/import and workflow resumption

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: FLIM phasor workflow completes end-to-end on FLUTE test data (Embryo.tif) without manual axis manipulation by user
  - Measurement: Integration test `test_flim_phasor_workflow_with_relabel` passes
  - Verification: Workflow calls base.relabel_axes → base.phasor_from_flim → succeeds with phasor plot artifact

- **SC-002**: Users can relabel, squeeze, expand, and reorder axes in under 1 second for typical microscopy images (up to 100 MB)
  - Measurement: pytest duration log shows each axis tool call < 1000ms
  - Verification: Run tests with `pytest --durations=20` and check axis tool timings

- **SC-003**: All 5 axis manipulation tools have at least 2 test cases each (10 tests minimum)
  - Measurement: `pytest tests/unit/base/test_axis_ops.py -v` shows ≥10 passing tests
  - Verification: Code coverage report shows 100% branch coverage for axis tool parameter validation

- **SC-004**: Workflow test harness validates the complete tool discovery → execution flow
  - Measurement: Test `test_full_discovery_to_execution_flow` passes
  - Verification: Test logs show: list_tools → search_functions → activate_functions → describe_function → call_tool sequence

- **SC-005**: All new functions pass describe_function schema validation
  - Measurement: Contract test `test_axis_tools_schema_validation` passes
  - Verification: Each axis tool returns valid JSON schema with required fields: id, summary, inputs, outputs, params_schema

- **SC-006**: New tests can be run without requiring cellpose or other external tool environments to be installed
  - Measurement: `pytest tests/integration/test_workflows.py --mock-execution` passes on minimal install (core + base toolkit only)
  - Verification: CI pipeline runs workflow tests in "fast mode" without installing cellpose env

- **SC-007**: Developer can add test cases for new tools by editing YAML files without modifying Python test code
  - Measurement: Add new YAML test case to `tests/integration/workflow_cases/`, run pytest, new test discovered and executed
  - Verification: Parametrized test `test_workflow_from_yaml` dynamically loads and runs all YAML test cases

- **SC-008**: describe_function returns structured inputs schema with expected_axes for FLIM functions
  - Measurement: Contract test validates inputs schema structure for base.phasor_from_flim
  - Verification: Schema includes expected_axes: ["T", "Y", "X"] and preprocessing_hint

- **SC-009**: Tool responses include next_step hints that guide LLM through FLIM workflow
  - Measurement: Integration test verifies base.phasor_from_flim response includes hints.next_steps
  - Verification: At least one next_step references base.phasor_calibrate

- **SC-010**: Error responses include corrective hints with suggested_fix for axis errors
  - Measurement: Integration test triggers axis error and verifies hints.suggested_fix is present
  - Verification: suggested_fix includes fn_id (base.relabel_axes) and appropriate params

- **SC-011**: Artifact references include rich metadata (shape, dtype, axes, axes_inferred)
  - Measurement: Contract test validates BioImageRef metadata structure
  - Verification: Metadata includes all required fields after loading Embryo.tif

### Acceptance Criteria

**For Axis Manipulation Tools:**
- [ ] All 5 axis tools (relabel, squeeze, expand_dims, moveaxis, swap) implemented and registered in base toolkit
- [ ] Each tool has complete JSON schema with input/output types and parameter validation rules
- [ ] All tools preserve OME-TIFF metadata (physical sizes, axis labels) correctly
- [ ] Error messages include function name, invalid parameter, and suggested fix
- [ ] Unit tests achieve 100% branch coverage for all axis tools
- [ ] Integration test demonstrates FLIM workflow: load Embryo.tif → relabel Z↔T → base.phasor_from_flim

**For Workflow Test Harness:**
- [ ] MCPTestClient class provides async interface for all MCP operations (list, search, activate, describe, call)
- [ ] Mock execution mode allows testing orchestration without tool environments
- [ ] Pytest fixtures provide: test client, sample images, mock executor
- [ ] YAML test case loader supports: steps, input artifacts, parameter passing, output assertions
- [ ] Parametrized test validates all registered functions have valid schemas
- [ ] Golden path test (FLIM phasor) runs full discovery-to-execution flow
- [ ] Test harness documentation includes: example YAML test case, fixture usage, mock configuration

**For LLM Guidance Hints:**
- [ ] describe_function returns inputs schema with type, required, expected_axes, preprocessing_hint
- [ ] describe_function returns outputs schema with type, description
- [ ] Success responses include hints.next_steps and hints.common_issues
- [ ] Error responses include hints.diagnosis and hints.suggested_fix (when applicable)
- [ ] Hints are configurable per function in manifest.yaml
- [ ] At least 3 base toolkit functions have complete hint definitions

**For Rich Artifact Metadata:**
- [ ] All BioImageRef artifacts include metadata with shape, dtype, axes
- [ ] axes_inferred flag correctly indicates when axes were guessed
- [ ] file_metadata includes ome_xml_summary for OME-TIFF files
- [ ] Metadata is present in both success and error responses

### Quality Gates

Before merging this feature:

1. **Test Coverage**: 100% branch coverage for axis tools, ≥80% for test harness utilities
2. **Performance**: All axis tools complete in <1s for 100 MB images (measured on CI hardware)
3. **Documentation**: All axis tools documented in `docs/reference/tools.md` with examples
4. **Contract Tests**: Schema validation passes for all 5 new axis tools
5. **Integration Tests**: FLIM workflow test passes in both real and mock execution modes
6. **Migration Guide**: If any existing tests break due to new axis metadata requirements, provide migration guide

## Future Considerations

### Potential Enhancements

1. **Axis algebra**: Support expression-based axis transformations
   - Example: `transform_axes("TCZYX → CZYX")` (drop T)
   - Example: `transform_axes("YXC → CYX")` (move C to front)

2. **Batch axis operations**: Apply same transformation to multiple images
   - Use case: Relabel axes for all images in a directory
   - API: `batch_relabel(image_refs, axis_mapping)`

3. **Axis validation rules**: Declarative constraints on axis configurations
   - Example: Function requires "T axis with ≥10 samples for FLIM analysis"
   - Test harness can validate inputs against rules before execution

4. **Workflow visualization**: Generate diagrams showing tool call sequences
   - Use case: Debug complex workflows by visualizing data flow
   - Output: GraphViz DOT file or Mermaid diagram

5. **Test case generation**: Auto-generate test cases from function schemas
   - Use case: Ensure every parameter combination is tested
   - Approach: Property-based testing with Hypothesis

### Integration Opportunities

1. **ImageJ/Fiji compatibility**: Support XYCZT axis order for ImageJ interop
   - Provide `to_imagej_axes()` and `from_imagej_axes()` convenience functions

2. **OME-Zarr multiscale**: Axis operations on multiscale images
   - Apply transformations to all resolution levels atomically

3. **Dask integration**: Lazy axis operations on large datasets
   - Avoid loading full arrays into memory for metadata-only changes

## Migration & Compatibility

### Backward Compatibility

- **No breaking changes**: All new functionality (axis tools are additions, test harness is dev-only)
- **Existing workflows**: Continue to work without modification
- **Artifact format**: OME-TIFF format unchanged; only metadata fields updated

### Migration Path

Not applicable (no breaking changes).

### Deprecations

None.

## References

### Related Specifications
- [Spec 006: Phasor Usability Fixes](../006-phasor-usability-fixes/spec.md) - FLIM analysis functions that depend on correct axis configuration
- [Spec 002: Base Tool Schema](../002-base-tool-schema/spec.md) - Base toolkit architecture and OME-TIFF handling

### External Documentation
- [OME Data Model](https://docs.openmicroscopy.org/ome-model/6.3.1/) - Axis metadata conventions
- [NumPy axis manipulation](https://numpy.org/doc/stable/reference/routines.array-manipulation.html) - Reference implementations for moveaxis, squeeze, expand_dims
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/) - MCP tool calling semantics

### Test Data Sources
- [FLUTE FLIM Dataset](../../../datasets/FLUTE_FLIM_data_tif/README.md) - Sample FLIM data for workflow testing

---

**Next Steps After Approval**:
1. Create feature branch `007-workflow-test-harness`
2. Write contract tests for axis tool schemas (TDD red phase)
3. Implement axis tools in `tools/base/bioimage_mcp_base/axis_ops.py`
4. Write MCPTestClient and pytest fixtures
5. Implement YAML test case loader
6. Write golden path workflow test (FLIM phasor)
7. Update `docs/reference/tools.md` with axis tool examples
8. Run full test suite and validate success criteria
