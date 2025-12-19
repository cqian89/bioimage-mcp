# Feature Specification: Base Tool Schema Expansion

**Feature Branch**: `002-base-tool-schema`  
**Created**: 2025-12-19  
**Status**: Draft  
**Input**: User description: "Start a new feature branch to address the issues identified in @specs/001-cellpose-pipeline/code_review.md . There needs to be research on expanding the tool and function schema for the base toolset. We need to identify common image processing functions (covering image io, transformations, pre-processing) within the base toolkit that should be added. Ideally we can convert these to the tool schema from the documentation of each tool. Additionally, a full 'live' end-to-end workflow should be implemented as a test. The end goal should be a functional mcp server that one can use agentic LLM IDEs/CLIs to call a large set of functions from the base environment as well as the cellpose environment."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get complete function details on demand (Priority: P1)

As a user of an agentic IDE/CLI, I want to request a function’s full parameter details and get complete, accurate inputs/outputs (even when the initial catalog entry is minimal), so I can reliably call tools without guesswork.

**Why this priority**: Incomplete parameter details prevent tool calling and reduce confidence in discovery.

**Independent Test**: Can be fully tested by starting the server, requesting a detailed description for a known function that starts with minimal details, and verifying the response contains a complete schema; a second request should return the same schema without needing to recompute it.

**Acceptance Scenarios**:

1. **Given** the server is running and a function exists whose initial listing is minimal, **When** the client requests the function’s detailed description, **Then** the server returns a complete parameter schema including required/optional parameters, types, defaults (when applicable), and human-readable descriptions.
2. **Given** the server has already returned a complete schema for that function at least once, **When** the client requests the function’s detailed description again, **Then** the server returns an equivalent schema without requiring repeated expensive enrichment work.

---

### User Story 2 - Build workflows using a richer base toolkit (Priority: P2)

As a user building image analysis workflows, I want a base toolkit with common image I/O, transformations, and pre-processing functions (with reliable schemas), so I can assemble workflows without pulling in specialized environments for basic steps.

**Why this priority**: A capable base toolkit reduces friction and makes the server useful across many workflows, not just segmentation.

**Independent Test**: Can be fully tested by discovering base toolkit functions in the catalog, retrieving schemas for a representative subset, and successfully running a small workflow that reads an image, applies pre-processing/transforms, and writes an output artifact.

**Acceptance Scenarios**:

1. **Given** the server is running, **When** the client searches for image-processing functions (I/O, transforms, pre-processing), **Then** the server lists a curated set of base functions with clear names and summaries suitable for selection.
2. **Given** the client selects a base function, **When** the client requests the detailed description, **Then** the response includes enough detail (parameter semantics and expected inputs/outputs) to call the function correctly.

---

### User Story 3 - Validate a live end-to-end workflow (Priority: P3)

As a maintainer, I want at least one automated end-to-end workflow validation that uses real tool execution and real image I/O (not mocked execution), so regressions in tool invocation, artifact handling, and function/schema alignment are caught early.

**Why this priority**: Mocked tests can pass even when real executions fail; a live workflow validation provides practical confidence.

**Independent Test**: Can be fully tested by running a single automated test that executes a real workflow end-to-end and verifies that expected output artifacts are produced and readable.

**Acceptance Scenarios**:

1. **Given** the runtime prerequisites for the workflow are available, **When** the live workflow validation test is executed, **Then** the workflow completes successfully and produces expected output artifacts (e.g., a label/mask output) that can be opened/validated.
2. **Given** required runtime prerequisites are not available, **When** the test suite is executed, **Then** the live workflow validation is clearly skipped with an actionable reason (rather than failing or silently passing without meaningful validation).

---

### Edge Cases

- A function exists in the catalog, but detailed schema enrichment fails (missing dependency, unexpected error, incompatible version).
- A client requests details for an unknown function name.
- Inputs reference a missing/unreadable image artifact.
- An input image is present but malformed or in an unsupported format.
- A tool call takes too long (timeouts) or produces excessively large outputs.
- Multiple workflow runs happen concurrently, and output artifacts must not collide or overwrite each other.

## Clarifications

### Session 2025-12-19

- Q: What library ecosystem should be used for the base image processing functions? → A: **scikit-image**.
- Q: How should the enriched schema cache be persisted? → A: **Local JSON file**.
- Q: What data source should be used for validation? → A: **Existing `datasets/FLUTE_FLIM_data_tif`**.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: Client-facing tool discovery remains “summary-first”. Detailed schemas are returned only when a client asks for a specific function’s detailed description. Changes must be backward-compatible for existing clients; new information should be additive.
- **Artifact I/O**: The system handles image artifacts (input images, processed images, label/mask outputs) and the metadata needed to interpret them. Artifacts must be referenced consistently so workflows can be replayed.
- **Isolation**: Each function runs in its owning environment (base vs. specialized). Schema enrichment must execute in the same environment as the function it describes.
- **Reproducibility**: Each workflow run records inputs, selected functions, resolved parameter values, produced output references, and relevant tool-pack version information needed to reproduce the run.
- **Safety/observability**: The system provides clear errors for invalid calls and records sufficient logs/events to debug failures. Automated tests cover both schema enrichment and at least one live workflow path.

### Functional Requirements

- **FR-001**: System MUST support listing and searching tools/functions without requiring full parameter schemas to be computed or returned.
- **FR-002**: System MUST return a complete, machine-readable parameter schema when a client requests a detailed description for a specific function.
- **FR-003**: System MUST enrich function schemas on demand when the initially stored schema is incomplete, and MUST store the enriched schema for reuse in a **local JSON file**.
- **FR-004**: System MUST refresh stored enriched schemas when the owning tool pack changes version (to avoid serving stale information).
- **FR-005**: System MUST provide a curated set of common base image-processing functions (primarily using **scikit-image**) spanning:
  - image I/O (load/open and save/export)
  - transformations (resize, crop, pad, reformat)
  - pre-processing (normalization, smoothing/denoising, simple thresholding)
- **FR-006**: For every base function included in scope, the system MUST provide a detailed description that includes parameter meanings, constraints when applicable, and expected inputs/outputs.
- **FR-007**: The project MUST produce a “base function catalog” document that explains which functions are included, why they were selected, and any known limitations.
- **FR-008**: The project MUST provide at least one automated “live” end-to-end workflow validation that exercises real image reading, real tool execution (no mocked execution), and writing/validating at least one output artifact.
- **FR-009**: The system MUST make workflow runs output-isolated so repeated or concurrent runs do not overwrite each other’s artifacts.
- **FR-010**: The system MUST allow clients to run workflows that combine base functions and a specialized segmentation function in the same workflow definition (where applicable).
- **FR-011**: The command-line entrypoint MUST be invokable from a clean subprocess in the automated test environment.
- **FR-012**: The live workflow validation MUST use the existing `datasets/FLUTE_FLIM_data_tif` dataset for now (expanding later). Provenance for this dataset must be confirmed/documented.

### Acceptance Coverage

- User Story 1 validates FR-001 through FR-004.
- User Story 2 validates FR-005 through FR-007 and contributes to FR-010.
- User Story 3 validates FR-008, FR-009, FR-011, and FR-012.

### Assumptions & Dependencies

- The project will utilize the existing `datasets/FLUTE_FLIM_data_tif` for validation, with plans to expand datasets as more workflows are gathered.
- Live workflow validation may require optional runtime prerequisites; when unavailable, the test is expected to skip with a clear reason.
- Base toolkit functions selected for inclusion are those that are broadly applicable across microscopy image analysis workflows and can be described unambiguously.

### Out of Scope

- Adding new specialized tool packs beyond the base toolkit and the existing segmentation environment.
- Building a graphical user interface for constructing workflows.
- Guaranteeing that all conceivable image formats are supported; the focus is on common microscopy formats already supported by the project.

### Key Entities *(include if feature involves data)*

- **Tool Pack**: A collection of functions that can be discovered and executed in a particular environment.
- **Function**: An addressable operation exposed to clients with a name, a summary, and a detailed parameter schema.
- **Parameter Schema**: The machine-readable description of a function’s parameters and expected inputs/outputs, suitable for automated tool calling.
- **Schema Cache Entry**: A stored enriched schema tied to a specific tool pack version and function.
- **Workflow Run**: A record of one execution of a workflow including inputs, parameters, outputs, and status.
- **Artifact Reference**: A stable reference to an input or output produced/consumed by functions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The base toolkit exposes at least 20 curated image-processing functions across the three categories (I/O, transformations, pre-processing), each with a complete detailed description.
- **SC-002**: For a function that starts with minimal details, the first detailed-description request returns a complete schema, and subsequent requests return equivalent schemas without requiring repeated enrichment work.
- **SC-003**: At least one automated live workflow validation runs end-to-end and produces a readable output label/mask artifact.
- **SC-004**: The standard test suite remains reliable: the live workflow validation is either successfully executed (when prerequisites exist) or explicitly skipped with a clear, actionable reason.
- **SC-005**: Users can complete a discovery-to-execution workflow in a single session: find a function, retrieve its detailed schema, and execute it successfully using only the information returned by the system.
