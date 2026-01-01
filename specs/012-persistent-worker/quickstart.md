# Persistent Worker Quickstart Guide

This guide provides developers with the information needed to test and utilize the persistent worker architecture in Bioimage-MCP. Persistent workers improve performance by keeping tool environments active and supporting in-memory data exchange.

## 1. Overview

Persistent workers provide three primary benefits:

- **Elimination of Startup Overhead**: Tool environments (Conda/micromamba) are activated once and kept alive, eliminating the ~2-5s overhead for sequential calls.
- **True In-Memory Artifacts**: Data can be passed between functions in the same environment using `mem://` URIs, avoiding expensive disk I/O.
- **Cross-Environment Data Handoff**: The core server automatically manages delegated materialization when an in-memory artifact needs to move between different tool environments.

## 2. Prerequisites

- **Python 3.13+**: Required for the core MCP server.
- **Conda/micromamba**: Installed and available in the system path.
- **bioimage-mcp-base**: The base environment must be created (run `python -m bioimage_mcp doctor`).

## 3. Configuration

Configure worker behavior in your `.bioimage-mcp/config.yaml` file:

```yaml
# Persistent Worker Settings
worker_timeout_seconds: 600    # Keep workers alive for 10 minutes of inactivity
max_workers: 8                 # Maximum number of concurrent worker processes
session_timeout_seconds: 1800  # Session state persistence duration
```

## 4. Quick Test

You can verify worker reuse using the `PersistentWorkerManager`. If configured correctly, subsequent requests for the same session and environment will return the same process ID.

```python
# tests/integration/test_persistent_quick.py
import pytest
from bioimage_mcp.runtimes.persistent import PersistentWorkerManager

def test_worker_reuse():
    manager = PersistentWorkerManager()
    
    # First call spawns worker
    worker1 = manager.get_worker("session1", "bioimage-mcp-base")
    pid1 = worker1.process_id
    
    # Second call reuses worker
    worker2 = manager.get_worker("session1", "bioimage-mcp-base")
    pid2 = worker2.process_id
    
    assert pid1 == pid2, "Worker should be reused"
    assert pid1 != 0, "Real subprocess should be spawned"
```

## 5. Memory Artifact Usage

Use `output_mode="memory"` to keep results in the worker's RAM. This produces a `mem://` artifact reference that can be passed to subsequent functions in the same environment.

```python
# Request output to memory
response = run_function(
    fn_id="base.bioio.export",
    inputs={"input": input_ref},
    params={"format": "OME-Zarr"},
    output_mode="memory"  # Creates mem:// artifact
)

# Use in next call without disk I/O
response2 = run_function(
    fn_id="base.skimage.filters.gaussian",
    inputs={"input": response.outputs["output"]},  # mem:// ref
    params={"sigma": 1.0}
)
```

## 6. Cross-Environment Handoff

When a `mem://` artifact is passed to a function in a *different* environment, the core server automatically triggers "delegated materialization." The original worker writes the data to a temporary disk location (Materialization), and the new worker reads it.

```python
# Load image in base env (creates mem:// artifact)
img_ref = run_function(
    fn_id="base.bioio.export",
    inputs={"path": "/data/image.czi"},
    output_mode="memory"
)

# Use in cellpose env - automatic materialization
# The core server detects cellpose env needs the data from base env's memory
seg_ref = run_function(
    fn_id="cellpose.segment",
    inputs={"image": img_ref},  # Core requests materialization
    params={"diameter": 30}
)
```

## 7. Debugging

Use these internal methods to inspect worker state during development:

- **Check worker status**: `manager.is_worker_alive(session_id, env_id)` returns Boolean status.
- **View worker logs**: Run logs are still captured and persisted to the artifact store; check the `LogRef` for the specific run.
- **Force restart**: If a worker becomes unresponsive, use `manager.handle_worker_crash(session_id, env_id)` to clean up and allow a fresh start.

## 8. Known Limitations

- **Volatility**: `mem://` artifacts are lost if the worker process crashes or the timeout is reached.
- **Concurrency**: Each worker processes requests sequentially. If you make concurrent calls to the same session/environment, they will be queued or rejected depending on configuration.
- **Capacity**: By default, the server limits total concurrent workers to 8 to prevent system memory exhaustion.
