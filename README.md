# bioimage-mcp

Bioimage-MCP is an MCP server for bioimage analysis. It keeps a stable, compact
LLM-facing interface while orchestrating a customizable set of analysis tools in
isolated conda environments (e.g., Cellpose, StarDist, PhasorPy, Fiji).

Key ideas:
- Stable discovery-first MCP API (paginated `list/search/describe`; avoids context bloat)
- File-backed artifact references for I/O (OME-TIFF preferred; OME-Zarr is a future goal)
- Per-tool environment isolation and subprocess execution
- Workflow recording and replay for reproducibility

Project docs:
- `initial_planning/Bioimage-MCP_PRD.md`
- `initial_planning/Bioimage-MCP_ARCHITECTURE.md`
- `.specify/memory/constitution.md`

## Cellpose Pipeline Quickstart (v0.1)

Run a Cellpose segmentation pipeline on a microscopy image:

```bash
# 1. Install the Cellpose environment
bioimage-mcp install --env bioimage-mcp-cellpose

# 2. Import an image into the artifact store
bioimage-mcp artifacts import /path/to/image.tif --type BioImageRef --format OME-TIFF

# 3. Run segmentation via the API (example using Python)
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

with ExecutionService(Config.from_file()) as svc:
    result = svc.run_workflow({
        "steps": [{
            "fn_id": "segmentation.cellpose_segment",
            "params": {"model_type": "cyto3", "diameter": 30.0},
            "inputs": {"image": {"ref_id": "<your-image-ref-id>"}}
        }]
    })
    print(result)  # Contains run_id, status, workflow_record_ref_id
```

See [Cellpose Pipeline Quickstart](specs/001-cellpose-pipeline/quickstart.md) for the full guide.

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
- Missing `conda-lock`: install via pip or conda-forge.
