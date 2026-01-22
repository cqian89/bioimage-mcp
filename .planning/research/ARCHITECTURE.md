# Architecture Patterns

**Domain:** Bioimage-MCP
**Researched:** 2026-01-22

## Recommended Architecture

**Hub-and-Spoke with Persistent Subprocesses**

*   **Hub (Core):** Python 3.13 process. Acts as the MCP Server, State Manager, and Orchestrator.
*   **Spokes (Workers):** Python subprocesses (one per active environment). Run the actual analysis tools.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Core / API** | MCP Protocol, Session Mgmt, Request Routing | Clients (LLM), Workers (Stdio) |
| **Registry** | Tool Indexing, Manifest Loading, Search | Core |
| **Runtime Manager** | Worker Lifecycle, Process Spawning, IPC | Workers |
| **Worker Process** | Tool Execution, In-Memory Storage, Introspection | Runtime Manager (IPC) |
| **Artifact Store** | File Storage, Metadata | Core, Workers (Read/Write) |

### Data Flow

1.  **Request:** LLM sends `call_tool("base.func", inputs={"img": "ref-123"})`.
2.  **Routing:** Core resolves `base.func` to `tools/base` pack (env: `bioimage-mcp-base`).
3.  **Worker Check:** Core checks if `bioimage-mcp-base` worker is `READY`. If not, spawns it.
4.  **IPC Request:** Core sends `ExecuteRequest` (NDJSON) to Worker via Stdin.
5.  **Execution:** Worker parses request, loads inputs (from file or memory), runs function.
6.  **Result:** Worker stores result (file or memory), sends `ExecuteResponse` via Stdout.
7.  **Response:** Core returns result to LLM.

## Patterns to Follow

### Pattern 1: The "Shim" Entrypoint
**What:** A lightweight Python script (`entrypoint.py`) inside the tool environment that loops on Stdin.
**When:** Always. This bridges the specific env's Python to the Core's IPC protocol.
**Example:**
```python
# tools/base/bioimage_mcp_base/entrypoint.py
for line in sys.stdin:
    request = json.loads(line)
    result = dispatch(request)
    print(json.dumps(result))
```

### Pattern 2: Artifact References
**What:** Never pass data. Pass pointers (`BioImageRef`, `TableRef`).
**Why:** Microscopy images are huge (GBs). JSON is for control, not data.

## Anti-Patterns to Avoid

### Anti-Pattern 1: "Shelling Out" for Every Call
**What:** Running `conda run -n env python script.py` for every single function call.
**Why bad:** Conda/Python startup takes 3-10 seconds. User experience destroys flow.
**Instead:** Use persistent worker processes with an event loop.

### Anti-Pattern 2: Implicit Dependencies
**What:** Assuming the Core env has `numpy` or `torch`.
**Why bad:** Core must remain lightweight.
**Instead:** All heavy deps go into `envs/*.yaml`.

## Scalability Considerations

| Concern | Mitigation |
|---------|------------|
| **Memory Leaks** | Workers are session-scoped. `shutdown` command clears memory. |
| **Concurrent Requests** | Core is async. Workers are single-threaded (busy/ready state). Multiple sessions = multiple workers. |
| **Large Data** | `bioio` lazy loading (Dask). `mem://` references avoid disk I/O. |
