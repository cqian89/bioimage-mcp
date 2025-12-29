# bioimage-mcp

Bioimage-MCP is an MCP server for bioimage analysis. It keeps a stable, compact
LLM-facing interface while orchestrating a customizable set of analysis tools in
isolated conda environments (e.g., Cellpose, StarDist, PhasorPy, Fiji).

## Key Features

- **Stable Discovery API**: Paginated `list/search/describe` to avoid context bloat.
- **Dynamic Permissions**: Support for `inherit` mode (zero-config file access via MCP Roots) and interactive overwrite protection.
- **Artifact-Based I/O**: File-backed references (OME-TIFF/OME-Zarr) instead of large payloads.
- **Isolated Execution**: Tools run in dedicated environments to prevent dependency hell.
- **Reproducible Workflows**: Automatic recording and replay of analysis steps.

## Quickstart (Cellpose Segmentation)

Run a Cellpose segmentation pipeline on a microscopy image:

```bash
# 1. Install the CPU profile (installs base and cellpose environments)
bioimage-mcp install --profile cpu

# 2. Start the MCP server (for use with AI agents)
bioimage-mcp serve
```

### Python API Example

```python
from pathlib import Path
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.api.execution import ExecutionService

# Load configuration and initialize service
config = load_config()
with ExecutionService(config) as svc:
    # 1. Import an image into the artifact store
    image_ref = svc.artifact_store.import_file(
        Path("path/to/image.tif"), 
        artifact_type="BioImageRef", 
        format="OME-TIFF"
    )

    # 2. Run segmentation
    result = svc.run_workflow({
        "steps": [{
            "fn_id": "cellpose.segment",
            "params": {"model_type": "cyto3", "diameter": 30.0},
            "inputs": {"image": {"ref_id": image_ref.ref_id}}
        }]
    })
    print(result)  # Contains run_id, status, workflow_record_ref_id
```

See [Cellpose Pipeline Quickstart](specs/001-cellpose-pipeline/quickstart.md) for the full guide.

## v0.8 API & Permission Refinements

### Configuration
Update your `.bioimage-mcp/config.yaml` to leverage new permission modes:

```yaml
permissions:
  mode: inherit       # explicit | inherit | hybrid
  on_overwrite: ask   # allow | deny | ask
agent_guidance:
  warn_unactivated: true
```

### Migration Guide
The `builtin` tool pack has been removed. Use the hierarchical naming scheme in the `base` toolkit.

| Legacy Name | New Canonical Name |
|-------------|-------------------|
| `builtin.gaussian_blur` | `base.skimage.filters.gaussian` |
| `builtin.convert_to_ome_zarr` | `base.bioimage_mcp_base.io.convert_to_ome_zarr` |

### API Changes

- **Execution**: Use **`run_function`** instead of the removed `call_tool`.
- **Discovery**:
  - `list_tools`: Supports hierarchical navigation via `path` (e.g., `path="base.skimage"`) and `flatten=True`.
  - `search_functions`: Supports multi-keyword search with `keywords`.
  - `describe_function`: Supports batch retrieval with `fn_ids=[...]`.
- **Activation Workflow**: Use `activate_functions(fn_ids=[...])` to filter the tool list for a session and reduce noise.

## Project Docs
- `docs/index.md`: Full documentation
- `docs/reference/tools.md`: Tool & Function reference
- `specs/`: Detailed feature specifications

## Install (v0.0 bootstrap)

Editable install from repo root:

```bash
python -m pip install -e .
```

Create a starter local config:

```bash
bioimage-mcp configure
```

Install/update the base environment (built-ins run here):

```bash
bioimage-mcp install --profile cpu
```

## Doctor (readiness checks)

Run the readiness checks:

```bash
bioimage-mcp doctor
```

Machine-readable output:

```bash
bioimage-mcp doctor --json
```

### The 8 checks

1. **Python version** (requires 3.13+)
2. **Env manager** (micromamba preferred; conda/mamba supported)
3. **Disk** (free space on the artifact store volume)
4. **Permissions** (write access to `artifact_store_root`)
5. **Base env** (`bioimage-mcp-base` exists / can be created)
6. **GPU** (optional; reports availability but does not fail on CPU-only hosts)
7. **conda-lock** (for reproducible env locking)
8. **Network** (basic connectivity)

### Common remediation

- Missing env manager: install `micromamba` (preferred) or `conda`.
- Failing permissions: choose an `artifact_store_root` you can write to.
- Low disk: free space or point `artifact_store_root` to a larger volume.
- Missing `conda-lock`: install via pip (`pip install "conda-lock>=4.0.0"`) or conda-forge.
