# Proposal: Persistent Worker Subprocesses and Real Memory Artifacts

## Executive Summary
This proposal outlines the transition from the current "Phase 1" metadata-only worker management to a fully compliant "Phase 2" architecture with true persistent worker subprocesses. The goal is to eliminate artifact simulation, reduce IPC overhead for chained operations, and satisfy Constitution requirements (II, III) regarding isolated execution and delegated materialization.

## Current State (Phase 1)
As of the current implementation, the system uses a hybrid approach that provides the API of persistent workers with per-call subprocess isolation, but lacks worker persistence and worker-owned memory:

1.  **`PersistentWorkerManager` (src/bioimage_mcp/runtimes/persistent.py)**: Tracks metadata (session_id, env_id, and artifact references) but does not maintain long-lived subprocesses. 
2.  **One-shot Execution**: Every tool call spawns a fresh process via `src/bioimage_mcp/runtimes/executor.py:execute_tool`.
3.  **Tool Entrypoints**: Scripts like `tools/base/bioimage_mcp_base/entrypoint.py` read a single JSON request from `stdin` and exit immediately after execution.
4.  **Simulated `mem://` Artifacts**: In-memory artifacts are currently simulated in the core process (e.g., `src/bioimage_mcp/api/execution.py`) by writing data to temporary files and tracking them via `_simulated_path` in metadata.
5.  **Core-side Materialization**: The core process often performs heavy I/O (using `bioio`) to resolve formats or move data, which violates the architectural constraint that Core should only coordinate.

## Unbiased Assessment: Phase 1 vs. Phase 2

| Feature | Phase 1 (Current) | Phase 2 (Proposed) | Assessment |
| :--- | :--- | :--- | :--- |
| **Start-up Overhead** | High (Conda env activation per tool call) | Low (Single activation per session) | Phase 2 significantly improves latency for short-running tools. |
| **Memory Isolation** | None (Core process materializes data) | Full (Worker process owns data) | Phase 1 violates Constitution II/III by involving Core in heavy I/O. |
| **State Retention** | Disk-based (slow) | RAM-based (fast) | Phase 2 allows true `mem://` residency without "hidden" disk writes. |
| **Complexity** | Low | High (Async IPC, resource management) | Phase 2 requires robust framing and crash recovery. |
| **Fault Isolation** | Process-level (per call) | Session-level (per worker) | A worker crash in Phase 2 loses all `mem://` data for that session. |

**Conclusion**: Phase 1 was a necessary bootstrap but is unsustainable for high-performance interactive analysis. Transitioning to Phase 2 is required for Constitution compliance.

## Target State (Phase 2)
A fully compliant architecture where:
1.  **Workers are Persistent**: One subprocess per `(session_id, env_id)` remains alive across tool calls.
2.  **Real Memory Artifacts**: `mem://` artifacts are resident in the worker process's memory (e.g., as XArray objects). No disk I/O occurs for intra-worker handoffs.
3.  **Delegated Materialization**: The core process never performs heavy image I/O. It dispatches `materialize` commands to workers.
4.  **Core as Orchestrator**: Core manages the routing of artifact references and worker lifecycles.

## Delegated Materialization Strategy

### 1. `mem://` Artifacts
If a worker owns a `mem://` artifact that must be used by another environment, the owning worker is tasked with exporting it to a file-backed format (e.g., OME-Zarr/OME-TIFF) via a `materialize` command.

### 2. User-Ingested & Proprietary Files
For files ingested directly by users (e.g., a `.czi` file on disk) that haven't been touched by a worker yet:
- **First Step**: Propose a "Materializer Environment" (defaults to `bioimage-mcp-base` as it has broad `bioio` support). 
- **Future**: Use a manifest-driven "capability selection" where Core asks which running worker is best suited to materialize format X into format Y.

## IPC Protocol & Framing

To support persistent communication, we need a framing protocol over `stdin`/`stdout`.

### Proposed Protocol: `src/bioimage_mcp/runtimes/worker_ipc.py`
*(Note: This file does not exist yet and will be added in Milestone 1.)*

We will use **NDJSON (Newline Delimited JSON)** for simplicity and cross-platform compatibility. Each request/response is a single line of JSON followed by `\n`.

**Tradeoff Analysis**:
- **NDJSON**: Easiest to debug, native support in most languages, handles pipe buffering well.
- **Length-Prefixed**: More robust for binary data, but since we only send small JSON metadata (paths/URIs), NDJSON is preferred for developer experience.

## Transition Plan

### Milestone 1: IPC Infrastructure
- Create `src/bioimage_mcp/runtimes/worker_ipc.py` for NDJSON framing.
- Refactor `src/bioimage_mcp/runtimes/executor.py` to support persistent pipes.
- **Update**: `src/bioimage_mcp/runtimes/protocol.py` to clarify it is for workflow compatibility types only.

### Milestone 2: Worker Persistence
- Implement `src/bioimage_mcp/runtimes/persistent.py` logic to manage long-lived `subprocess.Popen` instances.
- Update `tools/base/bioimage_mcp_base/entrypoint.py` to run a loop reading from `stdin` until a `shutdown` command or EOF.

### Milestone 3: Delegated Materialization
- Update `src/bioimage_mcp/api/execution.py` to remove `bioio` imports and direct file reading.
- Implement the `materialize` IPC command in `entrypoint.py`.
- Update `PersistentWorkerManager` to route materialization requests to the correct worker.

### Milestone 4: De-simulation
- Remove simulated memory logic from `src/bioimage_mcp/api/execution.py` (memory output simulation and mem input resolution) and the `_simulated_path` metadata field in `MemoryArtifactStore`.
- Update all integration tests to verify zero-disk-I/O intra-environment chains.
- Finalize resource cleanup (worker shutdown on session timeout).

## Testing Strategy

We will validate the Phase 2 implementation using a combination of existing and new integration tests:

1.  **Regression & Adaptation**:
    *   `tests/integration/test_worker_resilience.py`: Update to verify that worker PIDs remain identical across sequential tool calls in the same session.
    *   `tests/integration/test_cross_env_handoff.py`: Verify that delegated materialization correctly moves data between workers using file-backed intermediates.
    *   `tests/integration/test_artifact_export.py`: Ensure `materialize` commands correctly trigger worker-side exports for external consumption.

2.  **New Phase 2 Tests**:
    *   **PID Reuse**: Explicitly check that `os.getpid()` (returned in tool output) is stable across calls.
    *   **True Memory Residency**: Verify that `mem://` artifacts have no corresponding file on disk during the session lifetime.
    *   **Worker Crash Invalidation**: Simulate a real process death (e.g., `kill -9`) and verify that Core correctly invalidates all `mem://` artifacts owned by that worker and restarts it on the next call.

## Risks & Mitigations
- **Pipe Deadlocks**: If a worker writes too much to `stderr`, `stdout` may block.
    - *Mitigation*: Core always reads `stderr` in a separate background thread.
- **Memory Leaks**: Workers might keep large arrays alive indefinitely.
    - *Mitigation*: Implement `evict_artifact` and `shutdown` commands.
- **Environment Incompatibility**: Some older Python versions in tool envs might lack `sys.stdin.buffer`.
    - *Mitigation*: Stick to standard `json` and `sys.stdin` with `\n` delimiters.

## Out of Scope

The following items are explicitly excluded from this phase of work:

1.  **Shared Memory (SHM) Transports**: Using `multiprocessing.shared_memory` or similar for zero-copy IPC between *different* worker processes.
2.  **GPU Memory Retention**: Explicit management or optimization of VRAM residency between calls (this is left to the individual tool libraries like PyTorch).
3.  **Worker Resource Quotas**: Enforcing hard CPU/RAM limits per worker via cgroups or Docker containers.
