# Usage Guide

## Core Concepts

*   **Artifacts**: Bioimage-MCP does not pass raw image data through the API. Instead, it uses **Artifact References** (URI + metadata). You "import" a file to get a reference, pass that reference to tools, and "export" the result back to a file.
*   **Tools**: Functions are grouped into "Tool Packs" (e.g., `tools.base`, `tools.cellpose`).
*   **Workflows**: A sequence of tool executions. Workflows are recorded and can be replayed.

## CLI Commands

The `bioimage-mcp` CLI is the primary entry point for administration.

### Managing Artifacts

Import an image (creates a reference in the store):
```bash
bioimage-mcp artifacts import /path/to/image.tif --type BioImageRef --format OME-TIFF
```

Export an artifact (writes the file to a destination):
```bash
bioimage-mcp artifacts export <ref_id> /path/to/destination/output.tif
```

### Server Management

Start the MCP server (stdio mode):
```bash
python -m bioimage_mcp serve --stdio
```

For instructions on configuring AI clients (OpenCode, Claude, Cursor) to connect to this server, see the [MCP Client Setup Guide](tutorials/mcp-client-setup.md).


## Python API

You can also use the Python API to run workflows programmatically.

```python
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

# Load configuration
config = Config.from_file()

with ExecutionService(config) as svc:
    # 1. Define the workflow step
    # This corresponds to calling the 'run' tool in the MCP interface
    step = {
        "fn_id": "base.gaussian",
        "inputs": {
            "image": {"ref_id": "your-artifact-id"}
        },
        "params": {
            "sigma": 2.0
        }
    }
    
    # 2. Run the workflow
    result = svc.run_workflow({"steps": [step]})
    
    print(f"Run ID: {result['run_id']}")
    print(f"Outputs: {result['outputs']}")
```

## MCP Tools

The following tools are available via the MCP interface:

*   **`list`**: Browse the tool catalog.
*   **`describe`**: Get full details for a specific function.
*   **`search`**: Search for functions by query or I/O types.
*   **`run`**: Execute a function.
*   **`status`**: Poll for the status of a run.
*   **`artifact_info`**: Get metadata and previews for artifacts.
*   **`session_export`**: Export a session as a reproducible workflow.
*   **`session_replay`**: Replay an exported workflow on new data.
