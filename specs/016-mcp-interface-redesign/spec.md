# Feature Specification: MCP Interface Redesign (Clean Surface)

**Feature Branch**: `016-mcp-interface-redesign`  
**Created**: 2026-01-05  
**Status**: Draft  
**Input**: User description: "Redesign MCP tool surface to 8 clean tools with consistent naming, proper error handling, session replay, and LLM-friendly discovery"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover and Execute a Tool (Priority: P1)

An LLM or user wants to find a tool, understand its requirements, and execute it correctly with minimal back-and-forth.

**Why this priority**: This is the core use case - discovering and running tools efficiently. If this doesn't work well, the entire system fails its primary purpose.

**Independent Test**: Can be fully tested by navigating the catalog, describing a function, and executing it successfully with proper inputs.

**Acceptance Scenarios**:

1. **Given** an LLM needs to apply a Gaussian filter to an image, **When** it calls `list` to browse functions, `describe` to get parameter details, and `run` to execute, **Then** the entire flow completes in ≤3 API calls with clear artifact outputs.

2. **Given** a user provides invalid parameters to `run`, **When** the system validates the request, **Then** it returns a structured error with JSON Pointer paths and actionable hints for correction.

3. **Given** an LLM calls `describe` on a function, **When** the response is returned, **Then** artifact ports (`inputs`/`outputs`) are separate from `params_schema`, and all JSON Schema types are correct.

---

### User Story 2 - Search for Functions by Criteria (Priority: P1)

An LLM needs to quickly find functions by keyword, tag, or I/O type without manually browsing the entire catalog.

**Why this priority**: Search is critical for LLM efficiency - browsing large catalogs is impractical. This enables semantic discovery.

**Independent Test**: Can be tested by searching for "threshold" with `io_out: LabelImageRef` and receiving relevant segmentation functions.

**Acceptance Scenarios**:

1. **Given** an LLM needs a segmentation tool, **When** it calls `search` with `query: "segment"` and `io_out: "LabelImageRef"`, **Then** it receives ranked results with I/O summaries included.

2. **Given** a search request with no query or keywords, **When** the system validates the request, **Then** it returns a structured validation error explaining that one of `query` or `keywords` is required.

---

### User Story 3 - Navigate Catalog with Child Counts (Priority: P1)

An LLM or user needs to browse the catalog hierarchy and make informed decisions about whether to expand nodes or use search.

**Why this priority**: Child counts prevent expensive over-expansion and help LLMs decide navigation strategy. Critical for anti-context-bloat.

**Independent Test**: Can be tested by calling `list` on a module and verifying child counts are returned for all non-leaf nodes.

**Acceptance Scenarios**:

1. **Given** an LLM calls `list` on path `base.skimage`, **When** the response is returned, **Then** each module/package includes `children.total` and `children.by_type` counts.

2. **Given** a module has 46 functions, **When** `list` is called, **Then** the response shows `{"total": 46, "by_type": {"function": 46}}` instead of just `has_children: true`.

---

### User Story 4 - Export and Replay Workflows (Priority: P2)

A user wants to record a multi-step analysis session and replay it on different input data for reproducibility.

**Why this priority**: Reproducibility is a core architectural constraint, but replay on new data is an advanced use case. Discovery and execution must work first.

**Independent Test**: Can be tested by running a 3-step workflow, exporting the session, then replaying with different input images.

**Acceptance Scenarios**:

1. **Given** a completed session with 3 function calls, **When** `session_export` is called, **Then** it returns a `workflow_ref` (type `TableRef`, format `workflow-record-json`) whose contents include `external_inputs` (user-provided data) and `steps` with input sources clearly marked as `external` or `step` references.

2. **Given** an exported workflow record and new input images, **When** `session_replay` is called with new artifact bindings, **Then** the system executes all steps in order with the new inputs.

3. **Given** a replay request with a missing required external input, **When** `session_replay` validates the request, **Then** it returns a structured error indicating which input binding is missing.

---

### User Story 5 - Dry-Run Validation (Priority: P2)

An LLM wants to validate a tool call before committing to execution to catch errors early.

**Why this priority**: Dry-run prevents wasted computation and enables LLMs to correct mistakes before running expensive operations.

**Independent Test**: Can be tested by calling `run` with `dry_run: true` and missing required inputs, verifying the same validation as real execution.

**Acceptance Scenarios**:

1. **Given** an LLM calls `run` with `dry_run: true` and valid inputs, **When** validation succeeds, **Then** the response indicates readiness without executing the function.

2. **Given** an LLM calls `run` with `dry_run: true` and missing required `image` input, **When** validation runs, **Then** the response is `status: "validation_failed"` with the same error as a real run would produce.

---

### User Story 6 - Retrieve Artifact Metadata and Preview (Priority: P3)

A user needs to inspect artifact metadata or preview small text artifacts (like logs) without downloading full files.

**Why this priority**: Convenience feature that improves debugging and observability, but not critical for core workflows.

**Independent Test**: Can be tested by calling `artifact_info` on a log artifact and receiving metadata plus text preview.

**Acceptance Scenarios**:

1. **Given** a log artifact from a previous run, **When** `artifact_info` is called with `text_preview_bytes: 4096`, **Then** the response includes `mime_type`, `size_bytes`, checksums, and a truncated `text_preview`.

2. **Given** a large image artifact, **When** `artifact_info` is called, **Then** the response includes metadata (dims, dtype, shape) but no binary preview.

---

### Edge Cases

- What happens when `list` is called on a non-existent path? → Return structured error with `code: "NOT_FOUND"` and the attempted path.
- What happens when `run` is called on a function that crashes? → Return `status: "failed"` with error details and log reference.
- What happens when `session_replay` encounters a function that no longer exists? → Return validation error before execution begins.
- What happens when `session_export.dest_path` is outside allowed roots? → Return error listing allowed roots (redacted if sensitive).
- How does the system handle concurrent runs on the same session? → Session state is append-only; concurrent runs are allowed but may interleave.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: Complete redesign of MCP tool surface. Migration from 12+ tools to 8 tools. Breaking change - no backward compatibility. All existing client code must be updated.
- **Artifact I/O**: All I/O via typed artifact references (BioImageRef, LabelImageRef, TableRef, ScalarRef, ModelRef, LogRef). Artifacts include bounded metadata (dims, dtype, shape, size_bytes).
- **Isolation**: No changes to tool execution isolation. Functions still run in subprocess environments. Session/workflow recording happens in core server.
- **Reproducibility**: Workflow records capture `external_inputs` vs `step` outputs. Records include provenance (tool_pack_id, tool_pack_version, lock_hash, timestamps) and step provenance (function_id, inputs, params). `session_replay` (the MCP surface for the internal replay_workflow capability) enables deterministic reuse.
- **Safety/observability**: Structured error model per Constitution V and FR-024..FR-026, with contract tests required for all 8 tools.

### Functional Requirements

#### Discovery Tools

- **FR-001**: System MUST provide a `list` tool that returns catalog nodes (environments, packages, modules, functions) with deterministic ordering and cursor-based pagination (`cursor`, `limit`, max 200) and a `next_cursor` in responses.
- **FR-002**: `list` MUST return child counts (`total` and `by_type`) for every non-leaf node.
- **FR-003**: `list` MUST include lightweight I/O summaries for function nodes to reduce follow-up describe calls.
- **FR-004**: System MUST provide a `describe` tool that returns full details for any catalog node type.
- **FR-005**: `describe` for functions MUST return `inputs`, `outputs`, and `params_schema` as separate fields - artifact ports MUST NOT appear inside params_schema.
- **FR-006**: `describe` MUST return correct JSON Schema types (numbers as numbers, booleans as booleans).
- **FR-007**: System MUST provide a `search` tool that finds functions by query, tags, or I/O types.
- **FR-008**: `search` MUST require exactly one of `query` or `keywords` parameters.
- **FR-009**: `search` results MUST include I/O summaries for all returned functions.

#### Execution Tools

- **FR-010**: System MUST provide a single `run` tool for function execution (replacing both `run_function` and `run_workflow`).
- **FR-011**: `run` MUST accept separate `inputs` (artifact references) and `params` (JSON values) fields.
- **FR-012**: `run` MUST support `dry_run` mode that performs full validation identically to real execution.
- **FR-013**: `run` responses MUST include output artifact references with bounded metadata (dims, dtype, shape, size_bytes).
- **FR-014**: System MUST provide a `status` tool to poll running executions with progress information.

#### Artifact Tools

- **FR-015**: System MUST provide an `artifact_info` tool that retrieves artifact metadata.
- **FR-016**: `artifact_info` MUST support optional `text_preview_bytes` parameter for safe text artifacts.
- **FR-017**: `artifact_info` MUST include checksums for artifact integrity verification.

#### Session/Workflow Tools

- **FR-018**: System MUST provide a `session_export` tool that exports workflow records (and may optionally write the record to a caller-provided `dest_path`).
- **FR-019**: Workflow records MUST distinguish `external_inputs` (caller-provided) from step-derived artifacts.
- **FR-020**: Workflow records MUST include step input sources with `source` field indicating `external` or `step` origin.
- **FR-021**: System MUST provide a `session_replay` tool that re-runs workflows on new external inputs.
- **FR-022**: `session_replay` MUST validate all external input bindings before execution.
- **FR-023**: `session_replay` MUST support `params_overrides` (by function id) and `step_overrides` (by step index).

#### Error Handling

- **FR-024**: All tools MUST return structured errors with `code`, `message`, and `details` array.
- **FR-025**: Error details MUST include JSON Pointer `path` to the problematic field.
- **FR-026**: Error details MUST include actionable `hint` text for automated retry.

#### Removals

- **FR-027**: System MUST remove `describe_tool` (non-functional or redundant with `describe`).
- **FR-028**: System MUST remove `activate_functions` and `deactivate_functions` (complexity without benefit).
- **FR-029**: System MUST remove `run_workflow` (consolidated into `run` + session accumulation).
- **FR-030**: System MUST remove `export_artifact` (artifacts are accessed via URI returned by `artifact_info`).
- **FR-031**: System MUST remove `resume_session` (session state is tracked implicitly via `session_id` on `run` and replay via `session_export`/`session_replay`).

### Non-Functional Requirements

- **NFR-001 (Payload bounds)**: MCP responses MUST remain bounded; `list`/`search` responses MUST be paginated and MUST NOT include large schemas or binary payloads.
- **NFR-002 (Deterministic ordering)**: `list` and `search` results MUST be returned in a deterministic order; pagination MUST be stable (no duplicates/missing items across pages given a consistent catalog snapshot).
- **NFR-003 (Versioning + migration notes)**: Because this is a breaking MCP API change, the release MUST include a version bump rationale and migration notes for the old tool names/requests.
- **NFR-004 (Filesystem policy)**: Any request that writes to disk or accepts a filesystem path (e.g., `session_export.dest_path`) MUST enforce allowed roots and return structured errors for denied paths (allowed roots may be redacted if sensitive).

### Key Entities

- **CatalogNode**: Represents any item in the catalog hierarchy. Types: environment, package, module, function. Has exactly one stable `id`.
- **FunctionDescriptor**: Full description of a callable function including `inputs`, `outputs`, `params_schema`, examples, tags, and `next_steps` suggestions.
- **ArtifactRef**: Typed reference to a file-backed artifact. Includes `ref_id`, `type`, `uri`, metadata (dims, dtype, shape, size_bytes).
- **WorkflowRecord**: Exportable session record with `external_inputs`, `steps` array, and provenance data. Enables replay on new data.
- **StructuredError**: Error response with `code`, `message`, and `details` array containing JSON Pointer paths and hints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: LLMs can complete a discover-describe-run flow in ≤3 API calls for common single-tool tasks.
- **SC-002**: All catalog browse operations include child counts, enabling informed navigation decisions (verified by contract tests).
- **SC-003**: 100% of function descriptions have correct JSON Schema types (verified by contract tests).
- **SC-004**: Artifact ports never appear inside params_schema (verified by contract tests).
- **SC-005**: Dry-run validation catches 100% of errors that would occur during real execution.
- **SC-006**: Workflow export and replay round-trips successfully for multi-step sessions.
- **SC-007**: All error responses include actionable hints that enable LLMs to self-correct.
- **SC-008**: MCP tool count reduced from 12+ to exactly 8 tools.
- **SC-009**: All 8 tools have contract tests and integration tests before release.

## Assumptions

- Backward compatibility is explicitly not a priority (per proposal).
- Multi-step workflows are built via repeated `run` calls under a `session_id`, not via a separate workflow tool.
- `session_export.dest_path` is a server-filesystem path with allowlist enforcement.
- Session state is append-only; concurrent runs within a session are allowed.
- Tool pack environments are already functional; this feature focuses on the MCP surface, not execution internals.
