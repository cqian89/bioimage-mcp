# Feature Specification: v0.0 Bootstrap

**Feature Branch**: `[001-v0-bootstrap]`  
**Created**: 2025-12-18  
**Status**: Draft  
**Input**: User description: "Create spec for v0.0 (Bootstrap) based on @initial_planning/Bioimage-MCP_PRD.md and @initial_planning/Bioimage-MCP_ARCHITECTURE.md"

This milestone establishes the “minimum usable core” for Bioimage-MCP: install/readiness checks, server startup, tool discovery, and one end-to-end artifact-based execution.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and verify locally (Priority: P1)

A new user installs Bioimage-MCP on their workstation and confirms the system is ready to run bioimage analysis tools (including checks for optional capabilities like hardware acceleration).

**Why this priority**: Without a reliable install + readiness check, users cannot reach any product value and troubleshooting becomes the dominant experience.

**Independent Test**: Can be fully tested by running install/readiness checks on a clean machine (or clean environment) and confirming the result is either “ready” or an actionable remediation list.

**Acceptance Scenarios**:

1. **Given** a machine that meets published minimum prerequisites, **When** the user runs the documented installation flow, **Then** the system reports a successful install and indicates the baseline capabilities now available.
2. **Given** a machine missing at least one prerequisite, **When** the user runs the readiness check, **Then** the system reports a clear failure reason and provides at least one actionable next step per failed check.
3. **Given** a machine with optional acceleration available, **When** the user selects an acceleration profile during install, **Then** the system installs only what is compatible with that profile and reports what is enabled/disabled.

---

### User Story 2 - Start server and discover tools on demand (Priority: P2)

A user (or AI client) connects to the server and discovers available tools/functions through listing, search, and detailed per-function descriptions—without receiving the entire catalog at once.

**Why this priority**: Discovery is the primary interaction model for AI-driven workflows and must stay usable as the tool catalog grows.

**Independent Test**: Can be fully tested by starting the server with a small set of tool definition files and verifying discovery operations return correct, paginated, queryable results.

**Acceptance Scenarios**:

1. **Given** the server is running and at least one tool is registered, **When** the client requests a tool list, **Then** the client receives a paginated list of tool summaries suitable for browsing.
2. **Given** more tools/functions exist than fit in one response, **When** the client requests subsequent pages, **Then** it can retrieve the complete list without duplicates or omissions.
3. **Given** multiple functions are registered with descriptions/tags, **When** the client searches by keyword and/or tags, **Then** only matching functions are returned with enough detail to choose a next step.
4. **Given** a specific function identifier from search results, **When** the client requests the full function description, **Then** the client receives the complete input/output schema and parameter schema needed to call that function.

---

### User Story 3 - Run a trivial built-in function end-to-end (Priority: P3)

A user executes a simple, built-in image operation (for example: format conversion or a basic filter) using artifact references. An artifact reference is a compact pointer to a file on disk plus metadata (so large images are not sent through the protocol).

**Why this priority**: An end-to-end run proves the core contract: isolated execution, artifact-based I/O, and observable results.

**Independent Test**: Can be fully tested by executing the built-in function on a small sample image and validating that output and logs are produced as artifact references.

**Acceptance Scenarios**:

1. **Given** an input image available on disk within an allowed read location, **When** the client runs the built-in function with that image as an input artifact reference, **Then** the run completes successfully and returns an output artifact reference.
2. **Given** the built-in function produces an output artifact, **When** the client requests artifact metadata, **Then** it receives metadata (including size and checksum) without receiving the full pixel payload through the protocol.
3. **Given** a completed run, **When** the client exports the output artifact to a user-chosen local destination within an allowed write location, **Then** the exported file exists and matches the artifact’s recorded checksum.
4. **Given** an execution failure (invalid inputs or tool error), **When** the client checks the run record, **Then** it can retrieve a log artifact that explains the failure in human-readable terms.

---

### Edge Cases

- Tool definition files exist but are invalid or partially specified.
- Two tools/functions collide on identifiers.
- A requested tool/function is not installed or is temporarily unavailable.
- A referenced input artifact file is missing, unreadable, or outside allowed filesystem roots.
- An input image is in an unsupported format or contains unexpected dimensionality.
- A run exceeds a reasonable time limit and must be terminated while preserving logs.
- Disk is full or the artifact store location is read-only.
- The tool catalog is large enough that responses must be paginated to remain usable.

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: Establish the initial baseline external interface for discovery and execution; discovery and “describe” capabilities MUST remain stable and backwards-compatible once released.
- **Artifact I/O**: All function inputs/outputs MUST be represented as artifact references (file-backed) rather than embedding large binary payloads; image artifacts MUST support at least common microscopy image formats and a chunked intermediate format.
- **Isolation**: Tool execution MUST run in isolated tool runtimes (tool packs) so that adding tools does not destabilize other tools.
- **Reproducibility**: Each run MUST record sufficient provenance to understand and reproduce results (inputs, parameters, tool identity/version, timestamps, and produced artifacts).
- **Safety/observability**: The system MUST produce user-accessible logs per run, provide clear error messages, and enforce configurable filesystem read/write boundaries for artifact access and export.

### Out of Scope (v0.0)

- Multi-step workflow authoring, validation, recording, and replay.
- Integration of heavyweight third-party analysis tools (for example: deep-learning segmentation suites).
- Remote artifact storage (for example: object storage); bootstrap is local-first.
- Interactive viewer control and GUI features.

### Assumptions & Dependencies

- Users have local permissions to install and run the server and to read/write within at least one configured workspace directory.
- A compatible local AI client exists to connect to the server.
- Users provide images that are either in a supported microscopy format or can be converted into one by the baseline tooling.
- The host machine meets published minimum prerequisites (including sufficient disk space for artifacts).

### Functional Requirements

- **FR-001**: System MUST provide a documented installation flow that prepares the core server and at least one baseline tool pack needed for the built-in function.
- **FR-002**: System MUST provide a readiness check that validates prerequisites (including disk space and optional acceleration availability) and reports actionable remediation steps.
- **FR-003**: Users MUST be able to start the server locally and confirm it is accepting client connections.
- **FR-004**: System MUST discover tool definition files from a local filesystem location and build an index at startup.
- **FR-005**: System MUST provide a paginated tool listing capability that returns summaries (not full schemas) suitable for browsing.
- **FR-006**: System MUST provide a function search capability that supports at least keyword search and optional filtering by tags and input/output artifact types.
- **FR-007**: System MUST provide an on-demand function description capability that returns the full schema for exactly one function.
- **FR-008**: System MUST ensure discovery responses remain bounded in size by default (for example: via pagination and summary-first responses).
- **FR-009**: System MUST handle invalid tool definitions gracefully by excluding invalid entries from discovery results and surfacing clear diagnostics.
- **FR-010**: System MUST provide a local artifact store that persists outputs and logs as files and returns artifact references containing URI, format, size, checksum, and relevant metadata.
- **FR-011**: System MUST provide a trivial built-in function that reads an input image artifact reference and produces at least one output artifact reference.
- **FR-012**: System MUST produce a run record for each execution with status (at minimum: running/succeeded/failed), start/end timestamps, and a link to a log artifact reference.
- **FR-013**: System MUST support exporting an artifact reference to a user-specified local destination within configurable allowed filesystem roots.
- **FR-014**: System MUST enforce configurable filesystem allowlists/denylists for reading inputs and writing outputs/exports.
- **FR-015**: System MUST keep protocol messages compact by returning references and summaries rather than large binary payloads.

### Key Entities *(include if feature involves data)*

- **Tool Definition (Manifest)**: A file-based declaration of a tool pack, including its identity and the functions it exposes.
- **Tool**: A discoverable unit representing a packaged capability (one or more functions) available to the system.
- **Function**: A callable operation with a stable identifier, declared inputs/outputs, and parameter schema.
- **Artifact Reference**: A compact, metadata-rich pointer to a file-backed artifact produced or consumed by a function.
- **Run**: A single execution attempt of a function, with status, timestamps, parameters, inputs/outputs, and log references.
- **Log Artifact**: A run-produced artifact containing human-readable execution logs for diagnosis and provenance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can reach “server running and discoverable by a local client” within 30 minutes by following the documented installation flow, without requiring manual debugging beyond the readiness check’s remediation steps.
- **SC-002**: In a catalog of up to 500 functions, 95% of discovery requests (list/search/describe) return results to the client within 2 seconds on a machine meeting published minimum prerequisites.
- **SC-003**: The built-in function completes successfully on a supported sample image in at least 95% of attempts and produces an output artifact reference plus a log artifact reference.
- **SC-004**: For 100% of artifact references returned by the system, clients can retrieve artifact metadata (including size and checksums) without transferring the full binary payload through the protocol.
- **SC-005**: The readiness check detects and reports at least 10 common setup issues (for example: missing prerequisites, insufficient disk space, unsupported platform constraints) with a clear next action for each.
