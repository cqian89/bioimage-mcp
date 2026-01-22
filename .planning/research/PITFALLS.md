# Domain Pitfalls

**Domain:** Bioimage-MCP
**Researched:** 2026-01-22

## Critical Pitfalls

Mistakes that cause system instability or data loss.

### Pitfall 1: Zombie Processes
**What goes wrong:** Worker processes remain alive after the Core server shuts down (or crashes).
**Why it happens:** Subprocesses don't automatically die when parent dies (unless explicitly managed).
**Consequences:** Memory exhaustion, locked files, GPU resource hogging.
**Prevention:**
1.  Use `atexit` handlers in Core to kill workers.
2.  Workers should poll `stdin` and exit on EOF (pipe broken).
3.  Implement a heartbeat (optional but robust).

### Pitfall 2: The "Memory://` Illusion
**What goes wrong:** Core assumes it can access `mem://` data from a different worker.
**Why it happens:** `mem://` URIs look global but are local to the *specific worker process*.
**Consequences:** `FileNotFoundError` or confusing "Artifact not found" errors.
**Prevention:**
1.  Core tracks which worker owns which artifact.
2.  Auto-materialize (convert to file) when data must cross boundaries.

### Pitfall 3: Serialization Overhead
**What goes wrong:** Passing large lists/arrays in JSON parameters.
**Consequences:** Slow performance, broken pipes (buffer limits).
**Prevention:** Strict separation: Metadata/Control in JSON, Data in Artifacts.

## Moderate Pitfalls

### Pitfall 1: CUDA Version Mismatch
**What goes wrong:** Host driver is newer/older than Conda env's CUDA toolkit.
**Prevention:** Use `conda-lock` to pin compatible versions. Documentation for users on driver requirements.

### Pitfall 2: Path Handling on Windows
**What goes wrong:** Backslashes, spaces in paths break CLI arguments.
**Prevention:** Always use `pathlib.Path` and proper quoting in subprocess calls. Use `to_uri()`/`from_uri()` methods.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **IPC Implementation** | Deadlocks on Stdin/Stdout buffer filling | Use separate threads for reading/writing or async I/O. |
| **Dynamic Registry** | Importing modules triggers heavy initialization (slow startup) | Use lazy imports or AST inspection where possible. |
