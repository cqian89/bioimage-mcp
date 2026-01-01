# Data Model: Persistent Worker Subprocesses (Spec 012)

This document defines the data structures, entities, and state transitions for the Persistent Worker feature. It establishes the models for worker lifecycle management, in-memory artifacts, and the IPC protocol for Core-to-Worker communication.

## Entities

### 1. Worker
A persistent subprocess running in a specific conda environment, processing tool requests and owning memory artifacts. It is uniquely identified by the combination of `session_id` and `env_id`.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | Owning session identifier. |
| `env_id` | `str` | Conda environment name (e.g., "bioimage-mcp-base"). |
| `process_id` | `int` | OS process ID of the worker subprocess. |
| `started_at` | `datetime` | Timestamp when the worker was spawned. |
| `active_artifacts` | `list[str]` | List of `ref_id`s for `mem://` artifacts currently in worker memory. |
| `state` | `WorkerState` | Current lifecycle state of the worker. |
| `stdin` | `BinaryIO` | Write pipe to worker's standard input (NDJSON). |
| `stdout` | `BinaryIO` | Read pipe from worker's standard output (NDJSON). |
| `stderr_thread` | `Thread` | Background thread reading and logging worker stderr. |

**Key**: Unique by `(session_id, env_id)` pair.

### 2. WorkerState (Enum)
Represents the lifecycle phases of a persistent worker.

| Value | Description |
|-------|-------------|
| `spawning` | Process is starting and conda environment is being activated. |
| `ready` | Worker is idle and awaiting the next request. |
| `busy` | Worker is currently processing a tool request or IPC command. |
| `terminated` | Process has exited (normally or crashed). |

### 3. Memory Artifact (mem://)
An artifact whose data resides exclusively in a worker's process memory. These are ephemeral and lost if the worker process terminates.

**URI Format**: `mem://<session_id>/<env_id>/<artifact_id>`

| Property | Value/Description |
|----------|-------------------|
| `storage_type` | `"memory"` |
| `uri` | `mem://...` |
| `format` | `"memory"` (internal representation) |
| `metadata` | Standard artifact metadata (dims, shape, etc.) |

**Constraints**:
- **Invalidation**: Invalidated on worker crash or shutdown.
- **Access**: Cannot be directly accessed across environments.
- **Handoff**: Must be materialized for cross-env handoff.

### 4. File-backed Artifact (file://)
An artifact persisted to disk in standard format.

**URI Format**: `file:///<absolute/path>`

| Property | Value/Description |
|----------|-------------------|
| `storage_type` | `"file"` |
| `uri` | `file://...` |
| `format` | `OME-Zarr` (intermediate), `OME-TIFF` (export), etc. |

**Constraints**:
- **Access**: Can be accessed by any worker.
- **Handoff**: Used for cross-env handoff and external export.

---

## IPC Message Types (NDJSON)

Communication between Core and Worker uses single-line JSON messages (NDJSON) exchanged over stdin/stdout.

### 1. Request Types (Core -> Worker)

| Type | Description | Payload Example |
|------|-------------|-----------------|
| `execute` | Run a tool function. | `{"type": "execute", "fn_id": "...", "inputs": {...}, "params": {...}}` |
| `materialize` | Export `mem://` artifact to file. | `{"type": "materialize", "ref_id": "...", "format": "OME-TIFF"}` |
| `evict` | Free a memory artifact. | `{"type": "evict", "ref_id": "..."}` |
| `shutdown` | Graceful worker stop. | `{"type": "shutdown"}` |

### 2. Response Types (Worker -> Core)

| Type | Description | Payload Example |
|------|-------------|-----------------|
| `execute_result` | Tool output or error. | `{"type": "execute_result", "outputs": {...}, "error": null}` |
| `materialize_result`| Exported file details. | `{"type": "materialize_result", "uri": "file://...", "ref_id": "..."}` |
| `evict_result` | Confirmation of eviction. | `{"type": "evict_result", "ref_id": "...", "status": "success"}` |
| `shutdown_ack` | Acknowledgment before exit. | `{"type": "shutdown_ack"}` |

---

## State Transitions

Workers follow a strict state machine to ensure request synchronization and resource cleanup.

```text
       [ Start ]
           |
           v
     +-----------+
     | spawning  | <--------- (Initial Spawn)
     +-----------+
           |
           | (Process Started / Ready)
           v
     +-----------+      (Request)      +-----------+
     |   ready   | ------------------> |   busy    |
     +-----------+ <------------------ +-----------+
           |          (Complete)             |
           |                                 |
           | (Shutdown / Idle / Crash)       | (Crash)
           v                                 v
     +-----------+                     +-----------+
     | terminated| <------------------ | terminated|
     +-----------+                     +-----------+
```

| Transition | Event | Description |
|------------|-------|-------------|
| `spawning -> ready` | Bootstrap Complete | Process started successfully and environment activated. |
| `ready -> busy` | Request Received | Core sent an `execute`, `materialize`, or `evict` command. |
| `busy -> ready` | Request Completed | Worker finished task and sent result back. |
| `* -> terminated` | Exit/Crash | Process exited (exit code 0) or crashed (exit code != 0). |

---

## WorkerManager (Core Component)

The `WorkerManager` is the core component responsible for managing the lifecycle of all worker processes.

**Responsibilities**:
- **Registry**: Track active workers by `(session_id, env_id)` pair.
- **Lifecycle**: Spawn workers on demand and handle graceful shutdown.
- **Routing**: Route tool requests to the correct active worker.
- **Fault Tolerance**: Detect crashes, invalidate owned `mem://` artifacts, and report errors.
- **Resource Management**: Enforce `max_workers` limit and cleanup idle workers.

**State**:
- `_workers: dict[tuple[str, str], Worker]` - Map of active workers.
- `_lock: threading.Lock` - Thread safety for registry operations.
- `_memory_store: MemoryArtifactStore` - Registry of in-memory artifacts.

---

## Validation Rules

1. **Worker Limit**: `max_workers` (default 8) is enforced at spawn time. New requests queue if limit is reached.
2. **Operation Timeout**: `worker_timeout_seconds` (default 600) enforced per request. Workers exceeding this are terminated.
3. **Idle Timeout**: `session_timeout_seconds` (default 1800) before auto-shutdown of idle workers.
4. **Artifact Ownership**: `mem://` artifacts can only be accessed by the worker that created them (verified via `session_id` and `env_id` in URI).
5. **Isolation**: Core process MUST NOT import `bioio` or perform heavy I/O; all such operations are delegated to workers.
