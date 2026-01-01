# Research: Persistent Worker Runtime (Phase 0)

This document outlines the research findings and architectural decisions for the transition from one-shot subprocess execution to persistent worker subprocesses with real in-memory artifacts and NDJSON IPC protocol.

## 1. Current Runtime Implementation

### Current State (Phase 1)
- **Metadata-only Persistence**: `PersistentWorkerManager` in `src/bioimage_mcp/runtimes/persistent.py` tracks worker metadata, but no actual process persistence exists.
- **One-shot Execution**: Each tool call spawns a fresh process via `subprocess.Popen` in `executor.py`.
- **Communication Pattern**: Uses `proc.communicate()`, which closes stdin after sending a single request, triggering EOF in the worker.
- **Worker ID**: The `process_id` is currently a placeholder (0).

**Key Files:**
- `src/bioimage_mcp/runtimes/executor.py`: One-shot subprocess spawning.
- `src/bioimage_mcp/runtimes/persistent.py`: Worker metadata tracking.
- `src/bioimage_mcp/runtimes/protocol.py`: Request/Response models.

### Decision
Extend `PersistentWorkerManager` to manage real `subprocess.Popen` instances with persistent stdin/stdout pipes that remain open across multiple tool calls.

### Rationale
Maintains the existing API while adding true subprocess lifecycle management. This approach allows the core server to reuse warm environments and retain in-memory state (artifacts) between calls.

### Alternatives Considered
- **Socket-based IPC**: More complex to implement and manage across different platforms; requires port management.
- **Shared Memory**: While efficient for data, it does not solve the requirement for process persistence and environment isolation.

---

## 2. IPC Protocol Choice

### Decision
Standardize on **NDJSON (Newline-Delimited JSON)** over stdin/stdout pipes.

### Rationale
- **Simplicity**: Human-readable, grep-able, and easy to debug.
- **Native Support**: Built-in support in the Python standard library via the `json` module.
- **Reliability**: Works predictably with standard subprocess pipes without complex binary framing.
- **Low Overhead**: Sufficient for the metadata-heavy control plane messages.

### Alternatives Considered
- **Length-prefixed Binary**: Robust for binary data but adds unnecessary complexity for JSON metadata.
- **JSON-RPC**: Adds protocol overhead (id, jsonrpc version) without significant benefit for our internal IPC.
- **gRPC**: Introduces heavy dependencies and complex setup requirements for tool environments.

### Implementation Pattern
- **Core to Worker**: `proc.stdin.write(json.dumps(msg) + "\n"); proc.stdin.flush()`
- **Worker to Core**: Reads via `for line in sys.stdin:` loop.

---

## 3. Artifact Handling

### Current State
- **Simulated In-Memory**: `mem://` artifacts are currently simulated by writing data to temporary files and storing the path in `_simulated_path` metadata.
- **Constitution Violation**: The core server currently imports `bioio` directly for format conversion in `src/bioimage_mcp/api/execution.py` (lines 469-547), violating the principle of tool isolation.

### Decision
Implement true in-memory artifacts owned by worker processes. The core server will only coordinate via artifact references.

### Rationale
**Constitution Principle III** requires delegating artifact I/O to workers. Core should remain agnostic of specific image formats and heavy processing libraries.

### Files Requiring Remediation
- `src/bioimage_mcp/api/execution.py`: Remove `bioio` imports and delegation logic for materialization.
- `src/bioimage_mcp/artifacts/metadata.py`: Remove `BioImage` imports for metadata extraction; delegate to workers.

---

## 4. Tool Entrypoint Changes

### Current Pattern (One-shot)
```python
def main() -> int:
    request = json.loads(sys.stdin.read() or "{}")  # Reads until EOF
    # ... process ...
    print(json.dumps(response))
    return 0
```

### Target Pattern (Persistent)
```python
def main() -> int:
    for line in sys.stdin:  # Loop until EOF or explicit shutdown
        if not line.strip():
            continue
        request = json.loads(line)
        if request.get("command") == "shutdown":
            break
        response = process_request(request)
        print(json.dumps(response), flush=True)
    return 0
```

### Decision
Modify tool entrypoints to use a non-terminating NDJSON loop that listens for commands, including an explicit `shutdown` command.

### Rationale
Minimal change to existing tool structure while enabling persistence. Explicit shutdown ensures clean resource cleanup.

---

## 5. Configuration Patterns

### Decision
Add worker-specific settings to the main `Config` class using the `_seconds` suffix for time-based durations.

**Proposed Schema Additions:**
```python
worker_timeout_seconds: int = 600  # Maximum time for a single operation
max_workers: int = 8             # Maximum number of concurrent worker processes
session_timeout_seconds: int = 1800 # Idle timeout before worker shutdown (30 min)
```

### Rationale
Consistent with existing Pydantic v2 patterns used in `src/bioimage_mcp/config/schema.py`. Clear units in variable names prevent configuration errors.

---

## 6. Test Patterns

### Existing Tests
- `tests/integration/test_worker_resilience.py`: Currently tests metadata-level crash handling using mock PIDs.

### New Test Requirements
1. **PID Persistence**: Verify that the same subprocess PID is reused across sequential function calls within the same worker context.
2. **Lifecycle Management**: Verify explicit `spawn` and `shutdown` cycles.
3. **NDJSON Integrity**: Test handling of multiple messages, empty lines, and malformed JSON.
4. **Stderr Capture**: Ensure that worker `stderr` is captured asynchronously (via background thread) and not blocking the main IPC flow.
5. **Memory Artifact Continuity**: Verify that an object stored in worker memory in Step A is accessible in Step B without disk round-trip.
