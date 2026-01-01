# Feature Specification: Persistent Worker Subprocesses

**Feature Branch**: `012-persistent-worker`  
**Created**: 2026-01-01  
**Status**: Draft  
**Input**: User description: "Transition from Phase 1 (one-shot subprocess execution) to Phase 2 (persistent worker subprocesses) with real memory artifacts, delegated materialization, and NDJSON IPC protocol for Constitution II/III compliance"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sequential Tool Calls Without Startup Overhead (Priority: P1)

An analyst runs multiple image processing operations in sequence on a large microscopy dataset. Each operation after the first executes near-instantly because the worker subprocess is already running and doesn't need to re-activate the conda environment.

**Why this priority**: This is the core value proposition - eliminating the high startup overhead that makes interactive analysis painfully slow. Every subsequent tool call should feel immediate.

**Independent Test**: Can be validated by timing two sequential tool calls in the same session; the second call should complete significantly faster than the first (no conda activation overhead).

**Acceptance Scenarios**:

1. **Given** a session with no active worker for environment "bioimage-mcp-base", **When** the first tool call is made, **Then** a persistent worker is spawned and the call completes successfully
2. **Given** an active worker for environment "bioimage-mcp-base", **When** a second tool call is made, **Then** the same worker process handles the request (same PID) without re-activating the environment
3. **Given** an active worker, **When** a tool call is made, **Then** the warm-start tool execution latency is < 20% of cold-start latency (verified in CI via ratio)

---

### User Story 2 - Memory Artifact Retention Between Calls (Priority: P1)

An analyst loads a large image (e.g., 2GB OME-TIFF) and performs multiple operations on it. The image data remains in worker memory between calls, avoiding repeated disk I/O for each operation.

**Why this priority**: True memory residency is essential for interactive analysis workflows. Without this, every operation re-reads from disk, making chained analysis unacceptably slow.

**Independent Test**: Can be validated by loading an image, performing a transform, then verifying via inspection of the configured `artifact_store` root that no intermediate files were created on disk for `mem://` artifacts.

**Acceptance Scenarios**:

1. **Given** a worker with no loaded images, **When** an image is loaded with output storage "mem://", **Then** the data resides in worker process memory (no disk file created)
2. **Given** a mem:// artifact in worker memory, **When** a subsequent tool uses it as input, **Then** the data is accessed directly from memory without disk I/O
3. **Given** a mem:// artifact, **When** the session ends or worker shuts down, **Then** the memory is properly released

---

### User Story 3 - Cross-Environment Data Handoff (Priority: P2)

An analyst runs a preprocessing step in the base environment, then passes the result to a specialized environment (e.g., Cellpose) for segmentation. The system automatically materializes the memory artifact to a file-backed format for the handoff.

**Why this priority**: Multi-environment workflows are common (preprocessing → ML inference → post-processing). Seamless handoff enables sophisticated analysis pipelines.

**Independent Test**: Can be validated by running a two-step workflow across different tool environments and verifying the intermediate artifact is correctly transferred.

**Acceptance Scenarios**:

1. **Given** a mem:// artifact owned by Worker A (env: base), **When** Worker B (env: cellpose) needs to use it, **Then** the Core requests Worker A to materialize the artifact to file-backed format
2. **Given** Worker A receives a materialize command, **When** it exports the data, **Then** the output is written in the negotiated standard format (OME-TIFF by default, or OME-Zarr if preferred) readable by Worker B
3. **Given** materialization is complete, **When** Worker B accesses the artifact, **Then** it can load the file-backed data successfully

---

### User Story 4 - Graceful Worker Crash Recovery (Priority: P2)

A tool crashes due to an out-of-memory error or bug. The system detects the crash, invalidates any memory artifacts owned by that worker, and spawns a fresh worker for subsequent calls.

**Why this priority**: Crashes are inevitable; graceful recovery prevents session corruption and gives users clear feedback about what was lost.

**Independent Test**: Can be validated by forcefully killing a worker process and verifying the system correctly handles the next tool call.

**Acceptance Scenarios**:

1. **Given** an active worker owns mem:// artifacts, **When** the worker process crashes, **Then** the Core detects the crash within 5 seconds
2. **Given** a worker crash is detected, **When** the Core updates artifact state, **Then** all mem:// artifacts owned by that worker are marked as invalid
3. **Given** a crashed worker, **When** the next tool call is made for that environment, **Then** a new worker is spawned automatically
4. **Given** invalid artifacts, **When** a tool tries to use them, **Then** a clear error message indicates the data was lost due to worker crash

---

### User Story 5 - Controlled Worker Shutdown (Priority: P3)

An analyst finishes their session or the system needs to reclaim resources. Workers are gracefully shut down, ensuring any pending operations complete and resources are properly released.

**Why this priority**: Clean shutdown prevents resource leaks and ensures data integrity for any in-flight operations.

**Independent Test**: Can be validated by initiating a shutdown command and verifying the worker exits cleanly with proper resource cleanup.

**Acceptance Scenarios**:

1. **Given** an active worker with pending operations, **When** a shutdown command is sent, **Then** the worker completes in-flight operations before exiting
2. **Given** a shutdown command, **When** the worker exits, **Then** all allocated memory is properly released
3. **Given** idle timeout configuration, **When** no tool calls occur within the timeout period, **Then** the worker is automatically shut down

---

### Edge Cases

- What happens when a worker is killed during materialization? → Partial files are cleaned up and the operation returns an error
- How does the system handle a tool that hangs indefinitely? → Worker timeout mechanism terminates hung operations after configurable limit (default: 600 seconds)
- What happens when disk space is exhausted during materialization? → Clear error returned, partial files cleaned up, mem:// artifact remains valid
- How does the system handle rapid sequential calls that arrive before worker is ready? → Calls are queued and processed in order once worker is available
- How does the system handle concurrent artifact access? → Sequential only; worker processes one request at a time, concurrent calls queue
- What happens when the maximum worker limit is reached? → New worker requests queue until an existing worker is released or times out

## Requirements *(mandatory)*

### Constitution Constraints *(mandatory)*

- **MCP API impact**: No changes to external MCP endpoints or payload shapes. Internal IPC protocol is new but hidden from MCP clients.
- **Artifact I/O**: All artifact I/O delegated to workers. Core never imports bioio or performs heavy I/O. Memory artifacts (mem://) are true in-memory. File-backed artifacts use OME-Zarr (intermediate/large volumes) and OME-TIFF (default interchange/export). Cross-environment transfer MUST use negotiated formats (driven by target manifest defaults/overrides); source worker exports via bioio writers and target worker imports.
- **Isolation**: Workers run in isolated subprocess environments. Each (session_id, env_id) pair has at most one worker. Worker crashes don't affect Core stability.
- **Reproducibility**: Worker version info and artifact provenance are recorded in run logs. Memory artifacts are ephemeral and explicitly excluded from replay (must be re-derived).
- **Safety/observability**: Structured logs capture worker lifecycle events (spawn, crash, shutdown). Worker stderr captured by Core. Health checks detect hung workers.

### Functional Requirements

- **FR-001**: System MUST spawn persistent worker subprocesses that remain alive across multiple tool calls within a session
- **FR-002**: System MUST reuse existing workers for subsequent tool calls targeting the same (session_id, env_id) pair
- **FR-003**: System MUST store mem:// artifacts in worker process memory without writing to disk
- **FR-004**: System MUST route mem:// artifact access to the owning worker process
- **FR-005**: System MUST delegate all materialization (format conversion, disk I/O) to worker processes
- **FR-006**: Core process MUST NOT import bioio or perform any heavy image I/O operations
- **FR-007**: System MUST use NDJSON (newline-delimited JSON) protocol for IPC between Core and workers
- **FR-008**: System MUST detect worker process termination and update artifact validity accordingly
- **FR-009**: System MUST perform a cold-start spawn of a new worker when a tool call targets an environment with no active worker for the session
- **FR-010**: System MUST support explicit artifact eviction to free worker memory
- **FR-011**: System MUST support graceful worker shutdown via IPC command
- **FR-012**: System MUST capture worker stderr in a background thread to prevent pipe deadlocks
- **FR-013**: System MUST support a configurable idle timeout (config key: `session_timeout_seconds`) for automatic worker cleanup after inactivity
- **FR-014**: Workers MUST implement a read loop processing NDJSON messages until shutdown or EOF
- **FR-015**: System MUST process requests sequentially per worker; concurrent calls to the same worker are queued
- **FR-016**: System MUST enforce a configurable maximum concurrent worker limit (default: 8); requests beyond this limit queue until a worker is released
- **FR-017**: System MUST enforce a configurable per-operation timeout (default: 600 seconds); operations exceeding this limit are terminated and return an error
- **FR-018**: System MUST implement format negotiation for cross-worker handoff based on target tool manifest preferred formats/overrides, defaulting to OME-TIFF if no match is found (per Constitution III).

### Non-Functional Requirements

- **Performance**: Warm-start tool execution latency MUST be < 20% of cold-start latency for identical tool calls.
- **Reliability**: Worker crashes MUST NOT destabilize the Core process or affect workers in other environments/sessions.
- **Observability**: Worker lifecycle events (spawn, ready, busy, crash, shutdown) and stderr MUST be captured in Core logs.
- **Portability**: IPC protocol MUST use standard NDJSON over stdin/stdout to ensure compatibility across Linux, macOS, and Windows.
- **Safety**: File access by workers MUST be restricted to allowlisted paths as defined in global/local configuration.

### Key Entities

- **Worker**: A persistent subprocess running in a specific conda environment, processing tool requests and owning memory artifacts. Identified by (session_id, env_id) pair.
- **Worker State**: Workers follow a 4-state lifecycle: `spawning` (process starting, environment activating) → `ready` (idle, awaiting requests) → `busy` (processing a request) → `terminated` (exited normally or crashed). Crash is a `terminated` variant with exit code != 0.
- **Memory Artifact (mem://)**: An artifact whose data resides in a worker's process memory. Invalidated on worker crash. Cannot be directly accessed across environments.
- **File-backed Artifact (file://)**: An artifact persisted to disk in standard format (OME-Zarr, OME-TIFF). Can be accessed by any worker or exported externally.
- **IPC Message**: A single-line JSON message exchanged between Core and Worker over stdin/stdout. Types include: execute, materialize, evict, shutdown, and corresponding responses.
- **Worker Manager**: Core component that tracks active workers, routes requests, and handles lifecycle events.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Workers persist across tool calls—verified by same process ID (PID) for sequential calls in same session/environment
- **SC-002**: Warm-start latency is < 20% of cold-start latency for identical tool calls
- **SC-003**: Memory artifacts (`mem://`) have zero corresponding files on disk (verified by checking the configured `artifact_store` root during session lifetime)
- **SC-004**: Core process contains zero imports of bioio or similar heavy I/O libraries (verified via static analysis)
- **SC-005**: Worker crash correctly invalidates all owned mem:// artifacts within 5 seconds of detection
- **SC-006**: Cross-environment handoff completes successfully with automatic materialization
- **SC-007**: All existing integration tests continue to pass after transition to persistent workers
- **SC-008**: Worker shutdown releases all memory (no persistent memory leaks across worker lifetimes)

## Assumptions

- All tool environments have Python 3.10+ with standard library json module
- stdin/stdout are available for IPC (not redirected by conda activation)
- Worker memory usage is bounded by available system RAM (no explicit quotas in this phase)
- Tool environments remain stable (no package conflicts requiring restart)
- Idle timeouts (`session_timeout_seconds`) are configurable but defaults to reasonable period (e.g., 30 minutes)
- Maximum concurrent workers defaults to 8, configurable via config.yaml
- Per-operation timeout defaults to 600 seconds (10 minutes), configurable via config.yaml

## Out of Scope

The following capabilities are explicitly deferred to future phases:

- **Per-worker memory quotas** — No enforcement of memory limits per worker; bounded only by system RAM
- **Multi-node / distributed workers** — All workers run on the same machine as the Core process
- **GPU affinity / device assignment** — No explicit GPU pinning or device selection for workers

## Clarifications

### Session 2026-01-01

- Q: When multiple tool calls reference the same mem:// artifact concurrently, what is the expected behavior? → A: Sequential only; worker processes one request at a time, concurrent calls queue
- Q: What is the maximum concurrent worker limit? → A: Configurable limit, default 8 workers; configurable via config.yaml
- Q: What are the valid worker states and transitions? → A: 4-state model: spawning → ready → busy → terminated (crash is terminated variant)
- Q: Which capabilities are explicitly out-of-scope for this phase? → A: Memory quotas, multi-node distribution, GPU affinity — all deferred
- Q: What is the default operation timeout for hung workers? → A: 600 seconds (10 minutes), configurable via config.yaml
