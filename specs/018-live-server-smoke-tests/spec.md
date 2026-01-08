# Feature Specification: Live Server Smoke Tests

**Feature Branch**: `018-live-server-smoke-tests`  
**Created**: 2026-01-08  
**Status**: Draft  
**Input**: User description: "Address the gap where unit/integration tests pass but live agent-MCP interactions encounter blocking bugs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CI Blocks Live-Interaction Regressions (Priority: P1)

As a maintainer, I want an automated smoke test suite that talks to a real running server through its public interface (the same way supported clients do), so that regressions that only show up in true end-to-end communication are caught before merge.

**Why this priority**: This prevents “tests pass but real clients break” releases and reduces time spent debugging failures that are invisible to mocked tests.

**Independent Test**: Can be fully tested by running the minimal smoke suite and verifying it starts a fresh server, performs basic discovery and a simple execution, and produces an interaction log.

**Acceptance Scenarios**:

1. **Given** a change that introduces an end-to-end interaction regression, **When** CI runs the minimal smoke suite, **Then** CI fails with a clear error and an interaction log showing the failing request/response.
2. **Given** a compatible change with no regressions, **When** CI runs the minimal smoke suite, **Then** the suite passes and produces an interaction log artifact for traceability.

---

### User Story 2 - Developer Runs a Real Dataset Workflow (Priority: P2)

As a developer, I want smoke scenarios that exercise representative workflows using real datasets shipped with the repo, so that I can validate artifact handling and end-to-end execution without relying on mocks or synthetic inputs.

**Why this priority**: Real datasets and full workflows surface issues that synthetic tests miss (path handling, metadata quirks, serialization/validation edge cases, and timing).

**Independent Test**: Can be fully tested by running a dataset-backed scenario that performs discovery, loads a dataset, runs at least one analysis step, and validates outputs are returned as artifact references.

**Acceptance Scenarios**:

1. **Given** the repository dataset is available, **When** a developer runs a dataset-backed smoke scenario, **Then** the scenario completes successfully and returns valid output artifact references.
2. **Given** the dataset is missing or inaccessible, **When** a dataset-backed smoke scenario is started, **Then** it fails fast with a clear message indicating the missing input and where it was expected.

---

### User Story 3 - Debugging Produces Actionable Logs (Priority: P3)

As a developer debugging a reported client issue, I want to run smoke tests in a “recording” mode that captures the full sequence of requests/responses and server diagnostics, so that I can quickly compare failures across environments and reproduce issues.

**Why this priority**: Debugging speed and clarity directly impacts developer productivity and reduces repeated investigation cycles.

**Independent Test**: Can be fully tested by running a scenario in recording mode and confirming a detailed log is produced, is bounded in size, and includes timing and failure context.

**Acceptance Scenarios**:

1. **Given** a smoke scenario is run in recording mode, **When** it completes (pass or fail), **Then** a detailed interaction log is produced that includes requests, responses, timestamps, durations, and server diagnostics.

---

### Edge Cases

- What happens when the server fails to start (misconfiguration, missing dependency, or unexpected startup error)?
- How does the system handle server startup that exceeds a timeout (tests must fail fast and provide diagnostics)?
- What happens when an execution step crashes or terminates unexpectedly mid-scenario?
- How does the suite behave when optional capabilities are not available (scenario skipped with a clear reason)?
- What happens when a scenario produces large responses or logs (logs must remain size-bounded and still actionable)?
- How does the system handle operations that may not complete immediately (tests must handle transient “in progress” states without flakiness)?

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: No changes to the public server interface are required. The smoke suite validates the existing interface end-to-end; any unintended interface change is detected via failures.
- **Artifact I/O**: All scenario inputs and outputs MUST be handled as artifact references (no large payloads embedded in messages). The suite MUST validate returned references include usable identifiers and locations.
- **Isolation**: The suite MUST cover execution paths that use isolated tool execution, and it MUST not require optional tool environments for the minimal mode.
- **Reproducibility**: Each smoke run MUST produce a durable interaction log that records scenario identity, request/response sequence, timing, and failure context sufficient to reproduce the issue.
- **Safety/observability**: The suite MUST capture server diagnostics and ensure resources are cleaned up (server process termination) even on failure.

### Assumptions

- The repository includes known-good datasets under `datasets/`.
  - Primary: `datasets/FLUTE_FLIM_data_tif/` (e.g., `datasets/FLUTE_FLIM_data_tif/hMSC control.tif`).
  - Lightweight fallback: `datasets/synthetic/test.tif` for minimal/base-only runs when FLUTE data is not available.
- Some scenarios depend on optional tool environments (e.g., `bioimage-mcp-cellpose`); those scenarios MUST be conditionally skipped with a clear reason rather than failing the entire minimal suite.
- Smoke tests prioritize catching blocking regressions over exhaustive correctness validation; they are intentionally small and representative.

### Functional Requirements

- **FR-001**: System MUST provide an automated smoke test suite that interacts with a freshly started server instance through its public interface (without bypassing server layers).
- **FR-002**: System MUST support a “minimal” smoke mode that runs using only the core/base capabilities and is suitable to run as a frequent CI gate. Minimal mode MUST NOT require optional tool environments, and it SHOULD rely only on lightweight, repo-shipped inputs (e.g., `datasets/synthetic/test.tif`) if a dataset is needed.
- **FR-003**: System MUST support a “full” smoke mode that runs additional scenarios requiring optional tool environments and/or larger datasets when they are available. Full mode SHOULD include dataset-backed workflows (US2) and enhanced diagnostics (US3).
- **FR-004**: System MUST include at least one dataset-backed smoke scenario that performs: capability discovery, dataset load, at least one analysis step, and output validation.
- **FR-005**: System MUST validate that scenario outputs are returned as artifact references with non-empty identifiers and usable locations. (This is also a Constitution constraint; this FR exists to ensure the smoke suite explicitly asserts it.)
- **FR-006**: System MUST generate an interaction log for each smoke run, including: timestamps, direction (request/response), operation name, parameters (redacted/truncated if needed), result status, and duration.
- **FR-007**: System MUST keep interaction logs size-bounded and still useful for debugging (e.g., truncating large payload fields while keeping structural context). The concrete size budget is defined by SC-004.
- **FR-008**: System MUST fail fast with actionable diagnostics when the server fails to start or becomes unresponsive.
- **FR-009**: System MUST ensure server resources are cleaned up after each run (including termination on failures/timeouts).
- **FR-010**: System MUST clearly report skipped scenarios and the reason (e.g., missing optional capability or missing dataset).

### Dependencies

- A repository-provided dataset that is appropriate for a representative end-to-end workflow.
- A CI environment that can execute the minimal smoke suite and retain test artifacts (interaction logs).
- Optional tool environments may be required for “full” mode scenarios.

### Out of Scope

- Exhaustive correctness validation of scientific outputs (the suite focuses on smoke-level “does it run end-to-end”).
- Performance benchmarking beyond simple time limits used to keep CI reliable.
- Multi-client concurrency testing.

### Key Entities *(include if feature involves data)*

- **Smoke Scenario**: A named, testable journey (required inputs, required optional capabilities, and expected outputs as artifact references).
- **Interaction Log**: A record of the full request/response sequence for a smoke run, including timing and diagnostics, suitable for troubleshooting and audit.
- **Dataset Reference**: The identification of a repository-provided dataset used by a scenario, including where it is located and how the scenario selects it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The minimal smoke suite completes in under 2 minutes on the project’s standard CI runner.
- **SC-002**: The server becomes ready for smoke interactions within 30 seconds, or the suite fails with clear diagnostics.
- **SC-003**: Each dataset-backed smoke scenario completes in under 5 minutes on the project’s standard CI runner (or is explicitly excluded from the minimal gate).
- **SC-004**: Interaction logs are produced for 100% of smoke runs (pass or fail) and remain under 10 MB per run.
- **SC-005**: For at least one historically observed production-only failure class, a smoke test fails reliably when the regression is reintroduced. For this feature, the initial targeted failure class is **protocol/schema drift** that only appears in real client/server interaction (e.g., `describe()` response shape changes, `run()` returning embedded payloads instead of artifact references, missing structured error details).
- **SC-006**: In a controlled debugging exercise, a developer can identify the failing interaction step from the produced logs within 5 minutes.
