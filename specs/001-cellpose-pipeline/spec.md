# Feature Specification: v0.1 First Real Pipeline

**Feature Branch**: `001-cellpose-pipeline`  
**Created**: 2025-12-18  
**Status**: Draft  
**Input**: User description: "Create the spec for v0.1 (First Real Pipeline) from @initial_planning/Bioimage-MCP_PRD.md and @initial_planning/Bioimage-MCP_ARCHITECTURE.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a Cell Segmentation Pipeline (Priority: P1)

A microscopy researcher can run a simple, end-to-end segmentation workflow on a single image: provide an input image reference, execute segmentation, and receive a label image reference plus run logs.

**Why this priority**: This is the first tangible “real pipeline” value: running a real segmentation algorithm end-to-end with file-backed inputs/outputs.

**Independent Test**: Using a provided sample microscopy image, a user can run the segmentation workflow and receive a label output reference that can be exported to a local file and inspected.

**Acceptance Scenarios**:

1. **Given** a valid input image reference to a supported microscopy image, **When** the user runs the segmentation workflow with valid parameters, **Then** the system returns (a) a label image reference, (b) a run log reference, and (c) a workflow record reference.
2. **Given** an input image reference whose file cannot be read (missing or permission denied), **When** the user attempts to run the workflow, **Then** the system fails fast with a clear error message and returns a run log reference describing the failure.

---

### User Story 2 - Replay a Recorded Workflow (Priority: P2)

A platform engineer or analyst can reproduce a prior run by replaying a saved workflow record, without manually re-authoring steps.

**Why this priority**: Reproducibility is a core differentiator for bioimage analysis pipelines; replay turns “one-off” LLM runs into auditable, repeatable analysis.

**Independent Test**: Using the workflow record produced by User Story 1, a user can request a replay and receive a new run with equivalent outputs and new artifact references.

**Acceptance Scenarios**:

1. **Given** a workflow record reference produced by a prior successful run, **When** the user requests a replay, **Then** the system starts a new run and produces output artifacts of the same types as the original workflow.
2. **Given** a workflow record reference that points to a record with missing required inputs, **When** the user requests a replay, **Then** the system rejects the request with a clear explanation of what is missing.

---

### User Story 3 - Validate Pipeline Reliability on Sample Data (Priority: P3)

A maintainer can validate that the v0.1 pipeline continues to work by running an automated validation workflow on 1–2 small sample datasets.

**Why this priority**: A real pipeline must be verifiably stable; basic automated checks reduce regressions when adding tools and workflow features.

**Independent Test**: Running the predefined sample workflows produces the expected artifact types and finishes successfully.

**Acceptance Scenarios**:

1. **Given** the repository’s included sample datasets, **When** the maintainer runs the pipeline validation, **Then** the workflow completes successfully and produces a label image reference for each dataset.

---

### Edge Cases

- What happens when the input image reference points to an unsupported format?
- What happens when the segmentation step produces an empty result (no detected objects)?
- How does the system handle a segmentation tool failure while still producing useful logs?
- How does the system handle timeouts for long-running segmentation on large images?
- What happens when the workflow attempts to read/write outside configured allowed filesystem locations?

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: Additive capability only. No breaking changes to existing discovery behavior; v0.1 introduces the ability to execute a linear workflow, record it as an artifact, and replay it for reproducibility.
- **Artifact I/O**: All pipeline inputs/outputs MUST be passed as artifact references (file-backed). Minimum artifacts for the v0.1 pipeline: input image reference, output label image reference, run log reference, workflow record reference. Exports MUST support local filesystem destinations only.
- **Isolation**: Segmentation MUST execute in an isolated runtime that is independent from the core server runtime, so tool dependencies do not destabilize the server.
- **Reproducibility**: Each successful run MUST produce a workflow record artifact that captures: ordered steps, input/output artifact references, user-supplied parameters, tool identity/version, and an environment fingerprint sufficient to explain differences between runs.
- **Safety/observability**: Each run MUST produce logs as an artifact reference. The system MUST provide user-friendly errors for invalid references and MUST enforce configured filesystem allowlists for workflow reads/writes.

### Functional Requirements

- **FR-001**: The system MUST support executing an end-to-end v0.1 workflow that reads one microscopy image (by reference), runs a cell segmentation step, and writes a label image (by reference). **Acceptance**: Running the predefined sample workflow produces a label image reference.
- **FR-002**: The system MUST NOT embed large image or label payloads directly in messages; it MUST pass data via artifact references. **Acceptance**: A successful run returns only references/metadata, not pixel arrays.
- **FR-003**: For each workflow run (success or failure), the system MUST produce a run log artifact reference that is retrievable by the user. **Acceptance**: A failed run still yields a log reference that contains an error summary.
- **FR-004**: For each successful workflow run, the system MUST produce a workflow record artifact reference that can be used later to reproduce the run. **Acceptance**: The run results include a workflow record reference.
- **FR-005**: The system MUST support replaying a workflow record to start a new run without requiring manual re-entry of all steps. **Acceptance**: Replaying a saved record starts a new run and yields new output references.
- **FR-006**: The system MUST validate workflow step compatibility before execution, ensuring that each step’s produced artifact types satisfy the next step’s required inputs. **Acceptance**: An incompatible workflow is rejected before any tool execution begins.
- **FR-007**: The system MUST provide clear, actionable error messages when an artifact reference cannot be accessed (missing file, permission denied, unsupported format). **Acceptance**: The error identifies the problematic reference and the reason.
- **FR-008**: The system MUST allow users to export any artifact reference produced by a run to a local filesystem destination. **Acceptance**: Exporting a label artifact creates a local file at the requested path.
- **FR-009**: The system MUST enforce configured filesystem allowlists such that workflows cannot read or write outside permitted locations. **Acceptance**: A workflow referencing a forbidden path is rejected with an authorization error.
- **FR-010**: The system MUST include a minimal automated validation that runs the v0.1 pipeline on 1–2 small sample datasets and confirms that label outputs are produced. **Acceptance**: The validation run reports success and produces label references for each dataset.

### Assumptions & Dependencies

- The product is local-first for v0.1; inputs and outputs are stored on the local filesystem.
- The v0.1 “first real pipeline” scope is a linear, single-image segmentation workflow; it does not include parallel execution, batch scheduling, or an interactive GUI.
- The default intermediate artifact format is **OME-TIFF** for maximum interoperability; OME-Zarr support is deferred as a future goal.
- The project provides 1–2 small sample datasets suitable for routine validation.
- Users have permission to read the input image location and write to the configured artifact/output locations.

### Implementation Tasks (v0.1)

- Implement the OME-TIFF pivot: add `builtin.convert_to_ome_tiff` and update built-in/pipeline outputs to write OME-TIFF by default; keep OME-Zarr as a future goal.

### Key Entities *(include if feature involves data)*

- **Artifact Reference**: A metadata-rich pointer to a file-backed artifact, including a URI/location, format/mime information, size/checksum, and relevant image metadata (e.g., axes, pixel sizes, channels) when applicable.
- **Workflow**: An ordered set of steps representing a linear analysis plan, including step identifiers, required input artifact types, produced output artifact types, and user-provided parameters.
- **Run**: A single execution instance of a workflow, including status (running/succeeded/failed), timestamps, produced artifact references, and a log reference.
- **Tool Pack**: A discoverable analysis capability (e.g., segmentation) that can be executed in an isolated runtime and exposes one or more functions usable in workflows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Using a provided sample image and following the documented happy path, a user can obtain a label image reference within 15 minutes from starting the workflow.
- **SC-002**: On each provided sample dataset, a v0.1 run produces (at minimum) one label image reference and one run log reference.
- **SC-003**: Replaying a recorded workflow record produces outputs of the same artifact types as the original run, and the replayed run record clearly links back to the original record.
- **SC-004**: A user can discover and select the segmentation capability without loading the full tool catalog at once, and can complete User Story 1 after retrieving no more than 2 pages of tool listings and no more than 1 detailed function description.