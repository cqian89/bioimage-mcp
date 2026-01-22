# Architecture

**Analysis Date:** 2026-01-22

## Pattern Overview

**Overall:** Layered Modular Architecture with Artifact-Based I/O

**Key Characteristics:**
- **Tool Isolation:** Heavy dependencies (e.g., PyTorch, Cellpose) are isolated in separate Conda environments and executed as subprocesses.
- **Artifact Boundary:** Inter-tool communication occurs via typed, file-backed or memory-backed pointers (`ArtifactRef`). Core server does not handle raw image arrays.
- **Stateless Core / Stateful Sessions:** The server maintains session context (artifacts, history) while tool execution remains mostly stateless (or persistent via workers).
- **Extensible Registry:** Tools are discovered via YAML manifests, allowing dynamic expansion without core server changes.

## Layers

**API Layer:**
- Purpose: Exposes MCP tools and resources to LLMs.
- Location: `src/bioimage_mcp/api/`
- Contains: `server.py` (FastMCP setup), `discovery.py` (search/list), `execution.py` (run orchestration), `artifacts.py` (metadata info).
- Depends on: Core Logic Layer, Registry Layer.
- Used by: MCP Clients (Cursor, Claude Desktop, etc.).

**Core Logic Layer:**
- Purpose: Manages session lifecycle, workflow recording, and execution orchestration.
- Location: `src/bioimage_mcp/sessions/`, `src/bioimage_mcp/runs/`
- Contains: `manager.py` (session tracking), `recorder.py` (provenance capture), `store.py` (DB persistence).
- Depends on: Storage Layer, Registry Layer.
- Used by: API Layer.

**Registry Layer:**
- Purpose: Tool discovery, manifest loading, and function indexing.
- Location: `src/bioimage_mcp/registry/`
- Contains: `loader.py` (YAML parser), `index.py` (SQLite search index), `search.py` (natural language query logic).
- Depends on: None.
- Used by: API Layer, Core Logic Layer.

**Runtime Layer:**
- Purpose: Low-level subprocess execution and persistent worker management.
- Location: `src/bioimage_mcp/runtimes/`
- Contains: `executor.py` (one-shot execution), `persistent.py` (long-running workers), `protocol.py` (IPC JSON-RPC).
- Depends on: Bootstrap (for env management).
- Used by: Core Logic Layer (via `ExecutionService`).

**Storage Layer:**
- Purpose: Persistence of artifacts, run logs, and database state.
- Location: `src/bioimage_mcp/artifacts/`, `src/bioimage_mcp/storage/`
- Contains: `store.py` (artifact filesystem), `models.py` (Pydantic schemas), `sqlite.py` (DB backend).
- Depends on: None.
- Used by: All layers.

## Data Flow

**Tool Execution Flow:**

1. **Request:** MCP client calls `run(fn_id, inputs, params)`.
2. **Resolution:** `ExecutionService` looks up `fn_id` in `RegistryIndex` to find the tool pack and environment.
3. **Materialization:** Input `ArtifactRefs` are checked; if they live in a different environment, they are materialized to files (e.g., OME-TIFF) via `IOBridge`.
4. **Dispatch:** `Executor` (or `PersistentWorker`) starts/reuses a subprocess in the target Conda env.
5. **IPC:** Request is sent as JSON via `stdin`. Tool logic processes data using `bioio` for I/O.
6. **Response:** Tool returns JSON via `stdout` containing new `ArtifactRefs` and logs.
7. **Ingestion:** Core server imports new artifacts into `ArtifactStore` and records the step in `RunStore`.
8. **Return:** Serialized `RunResponse` is returned to the MCP client.

**State Management:**
- **Persistent State:** SQLite database tracks tools, functions, sessions, and runs (`artifacts/state/bioimage_mcp.sqlite3`).
- **File State:** Artifacts (images, tables, logs) are stored in the filesystem (`artifacts/objects/`).
- **In-Memory State:** `MemoryArtifactStore` and persistent workers keep objects alive across calls within a session.

## Key Abstractions

**ArtifactRef:**
- Purpose: A typed pointer to data (image, table, scalar, plot).
- Examples: `src/bioimage_mcp/artifacts/models.py`
- Pattern: Data Transfer Object (DTO) with metadata.

**Function Manifest:**
- Purpose: YAML file describing tools, functions, I/O ports, and environments.
- Examples: `tools/base/manifest.yaml`
- Pattern: Declarative configuration.

**Persistent Worker:**
- Purpose: Long-running subprocess that keeps data in memory for faster subsequent calls.
- Examples: `src/bioimage_mcp/runtimes/persistent.py`
- Pattern: Worker Pool / Sidecar.

## Entry Points

**CLI (bioimage-mcp):**
- Location: `src/bioimage_mcp/cli.py`
- Triggers: User command line.
- Responsibilities: Routing to `configure`, `install`, `doctor`, or `serve`.

**MCP Server:**
- Location: `src/bioimage_mcp/api/server.py`
- Triggers: MCP Client connection (stdio or SSE).
- Responsibilities: Handling `list`, `search`, `run`, `describe`.

## Error Handling

**Strategy:** Structured exceptions with stable error codes for LLM diagnosis.

**Patterns:**
- **BioimageMcpError:** Base class for all user-facing errors in `src/bioimage_mcp/errors.py`.
- **Validation Errors:** Captured during workflow setup or Pydantic model validation.
- **Execution Errors:** Captured from tool stderr or non-zero exit codes.

## Cross-Cutting Concerns

**Logging:** Centralized in `src/bioimage_mcp/logging.py`, tool logs are captured and stored as artifacts.
**Validation:** Pydantic v2 used throughout for API and manifest validation.
**Authentication:** Not implemented (local-first design); session-based isolation for multi-tenant simulation.

---

*Architecture analysis: 2026-01-22*
