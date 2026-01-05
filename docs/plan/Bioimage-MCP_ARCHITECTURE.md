# Bioimage-MCP Architecture

## 1. Architectural Goals
- Keep the **LLM-facing API constant** while tools grow (no context bloat).
- Isolate heavy/fragile dependencies by running each tool in its **own conda env**.
- Standardize I/O using **artifact references** (file-backed, metadata-rich).
- Prefer existing SDKs/engines to minimize bespoke code.

## 2. Component Diagram (high level)

**Control plane (core server)**
- MCP server implementation (tools/resources/pagination) using MCP Python SDK.
- Tool registry + schema index (SQLite/Postgres).
- Workflow recorder (linear execution log).
- Replay executor (re-runs recorded workflows).
- Artifact store + provenance store.

**Data plane (per-tool execution)**
- Environments use `bioimage-mcp-*` naming convention to avoid conflicts with user envs.
- Base env (`bioimage-mcp-base`): Python 3.13, bioio (+ `bioio-ome-tiff`), `tifffile`/core scientific stack, PhasorPy, core utilities.
- Isolated envs: `bioimage-mcp-cellpose` (PyTorch), `bioimage-mcp-stardist` (TensorFlow), `bioimage-mcp-fiji` (Java).
- Each env includes a small **shim** that implements:
  - `describe()`
  - `run(fn_id, inputs, params)`
  - **Reference**: `MicroscopyLM/src/miclm/executors/python_subproc.py` implements the subprocess isolation pattern.

**Note**: napari is excluded (use existing napari-mcp for viewer integration if needed).

## 3. Environment Management (conda, but fast/reproducible)

### 3.1 Lockfiles
- Maintain `environment.yml` (human-edited intent) + `conda-lock.yml` (generated, pinned).
- Generate locks per target platform using **conda-lock**.
- **bioio requirement**: `bioio` and relevant format plugins are required dependencies for ALL tool environments to ensure consistent artifact interchange.

### 3.2 Fast installs
- Use **micromamba** to create envs quickly and to install from lockfiles.
- Ensure the **libmamba solver** is used when solving is needed.
- **Reference**: `MicroscopyLM/src/miclm/env/manager.py` contains logic for `doctor` checks and environment bootstrapping.

## 4. Artifact Model (the glue between envs)

### 4.1 Cross-Environment I/O Standard: bioio
All tool environments use the **bioio** Python library as the standard image artifact layer. This provides:
- **Lazy loading**: Efficient access to large datasets via dask.
- **Normalization**: BioImage normalizes all inputs to 5D TCZYX (Time, Channel, Z, Y, X) arrays automatically.
- **StandardMetadata**: Consistent access to pixel sizes, channel names, and acquisition info across different formats.
- **Format Abstraction**: Capability to read 150+ microscopy formats via plugins.
- **Simplified Tooling**: No custom image wrapper is needed; tools use `BioImage(path).data` directly for numpy/dask/xarray access.

### 4.2 Interchange Formats
Each environment declares its preferred interchange format in its manifest (`interchange_format`).
- **OME-TIFF**: Default for most tool environments. Offers single-file portability, metadata-rich headers, and broad tool support.
- **OME-Zarr**: Used for environments handling extremely large datasets or requiring cloud-native chunked storage.
- Format conversion happens at import/export time using bioio plugins, removing the need for a separate format broker.

### 4.3 Artifact References
All tool inputs/outputs are passed by reference using a typed schema. Bioio handles the actual loading and data access from these references.

Core types:
- `BioImageRef`: Primary microscopy images (OME-TIFF or OME-Zarr).
- `LabelImageRef`: Segmentation masks or classification maps.
- `TableRef`: Measurement/feature tables (parquet/csv).
- `ModelRef`: Saved model weights or configurations.
- `LogRef`: Run logs and stdout/stderr captures.

**Artifact reference contract:**
```yaml
ref:
  uri: "file:///path/to/output.ome.tiff"
  mime_type: "image/tiff"
  format: "OME-TIFF"
  size: 1048576
  checksums: {sha256: "abc123..."}
  metadata: {axes: "TCZYX", channels: ["DAPI", "GFP"], ...} # Derived from BioImage.standard_metadata
```

### 4.4 Environment Plugin Matrix
To support the interchange standards, each environment must include specific bioio plugins:

| Environment | Python | Interchange | Plugins Required |
|-------------|--------|-------------|------------------|
| bioimage-mcp-base | 3.13 | OME-TIFF | bioio, bioio-ome-tiff, bioio-bioformats |
| bioimage-mcp-cellpose | 3.10 | OME-TIFF | bioio, bioio-ome-tiff |
| bioimage-mcp-stardist | 3.10 | OME-TIFF | bioio, bioio-ome-tiff |

### 4.5 In-Memory Session Cache (Performance Optimization)
To reduce I/O latency in iterative workflows, artifacts may be cached in memory:
- **SessionArtifactCache**: LRU cache holding `numpy` arrays extracted from `BioImage` objects for active session artifacts.
- **Spilling**: Large arrays spill to memory-mapped OME-Zarr temp files when memory limits are reached.
- **Transparency**: Tools interact with `ArtifactRef`s; the cache transparently serves data from memory or disk.

## 5. Tool, Function & Dynamic Registry
Each tool provides a manifest (YAML) containing:
- Tool identity: `tool_id`, `env_id`, version, entrypoint
- `python_version` (required Python for this tool)
- `platforms_supported` (e.g., `[linux-64, osx-arm64, win-64]`)
- `interchange_format` (preferred format: `OME-TIFF` or `OME-Zarr`)
- Functions:
  - `fn_id` (stable), description, tags
  - `inputs` and `outputs` (typed ports)
  - resource hints (GPU/CPU/memory)
  - **upstream/downstream** associations for planning and UI suggestions

The core server indexes these manifests for fast `search(...)`.
- **Reference**: `MicroscopyLM/src/miclm/tools/registry.py` implements the layered registry (builtin/user/project).

### 5.1 Dynamic Function Registry (Auto-Discovery)
To expose comprehensive library capabilities (e.g., `skimage`, `scipy`, `phasorpy`) without manual wrapper maintenance:
- **Library Adapters**: Protocol-based adapters introspect Python modules to discover functions.
- **Signature Parsing**: `griffe` and `docstring_parser` extract schemas and descriptions from code/docstrings.
- **Allow-lists**: `manifest.yaml` defines allowed modules/patterns to prevent accidental exposure of internal or unsafe functions.
- **Lazy Loading**: Modules are imported only when their functions are called.

### 5.2 Shim Execution Model (MVP)
- **Subprocess per call**: core server spawns a Python subprocess in the tool's conda env
- **Logs**: written to artifact store as `LogRef`
- **Timeout/cancellation**: SIGTERM after configurable timeout, SIGKILL after grace period
- **GPU selection**: inherits `CUDA_VISIBLE_DEVICES` from parent, or tool manifest can override
- **Roadmap**: persistent workers for heavy runtimes (Cellpose, StarDist) in post-MVP

## 6. Workflow Execution (Session-Based)

### 6.1 Execution Model
- Multi-step workflows are built via repeated `run` calls under a shared `session_id`.
- Each `run` call is recorded with inputs, params, outputs, and provenance.
- Workflows are **linear sequences**: ordered steps with typed I/O validation.

### 6.2 Workflow Record Format
Exported via `session_export`, the workflow record captures:
- **external_inputs**: Artifacts provided by the caller (starting data) with `first_seen` info.
- **steps**: Array of executed calls with input sources marked as `external` or `step` references.
- **provenance**: tool_pack, tool_version, lock_hash for each step.

```json
{
  "schema_version": "2026-01",
  "session_id": "session_...",
  "external_inputs": {
    "raw_image": {"type": "BioImageRef", "first_seen": {"step_index": 0, "port": "image"}}
  },
  "steps": [
    {
      "index": 0,
      "id": "base.skimage.filters.gaussian",
      "inputs": {"image": {"source": "external", "key": "raw_image"}},
      "params": {"sigma": 1.0},
      "outputs": {"output": {"ref_id": "...", "type": "BioImageRef"}},
      "status": "success",
      "provenance": {"tool_pack": "bioimage-mcp-base", "tool_version": "...", "lock_hash": "..."}
    }
  ]
}
```

### 6.3 Workflow Replay
`session_replay` enables deterministic reuse:
- Rebind `external_inputs` to new artifact references.
- Apply `params_overrides` by function id or `step_overrides` by step index.
- Validate all bindings before execution begins.
- Dry-run mode returns validation status without executing.

### 6.4 Post-MVP: DAG Engine Integration
Consider integrating **Pydra** if/when:
- Complex parallel pipelines emerge (batch processing hundreds of images)
- Formal caching by parameter/input hash becomes essential
- Users request automated retries with exponential backoff

## 7. Extensibility Architecture

### 7.1 Discovery mechanism (file-first)
- **Primary**: manifests on disk at `tools/{tool}/tool.yaml`, indexed by core server
- **Optional**: Python entry points for in-core tools installed in the core env
- **Optional hooks**: pluggy-based hooks for `validate_manifest`, `post_run`, etc.

### 7.2 User tool configuration
Users can override built-in tools or add custom tools via `~/.bioimage-mcp/tools/`:
```
~/.bioimage-mcp/
├── tools/
│   └── {toolname}/
│       ├── tool.yaml        # Tool manifest (env, functions, I/O types)
│       ├── resources/       # Optional: model weights, configs
│       └── scripts/         # Optional: shim scripts
├── envs/                     # User-added env specs + lockfiles
└── config.yaml               # Global user preferences
```

### 7.3 Bootstrapper / Env Manager
A dedicated component that:
- Reads tool-pack definitions from `tools/` directory
- Resolves platform-specific lockfile
- Creates envs with micromamba
- Registers manifests into the core registry
- Manages both built-in and user-added tool packs

## 8. Installer & Bootstrap CLI
First-class installer for easy onboarding:

**Commands:**
- `bioimage-mcp install [--profile cpu|gpu]` — creates/updates conda envs from lockfiles
- `bioimage-mcp doctor` — verifies micromamba, lockfiles, disk space, GPU, Java (for Fiji)
- `bioimage-mcp configure <host>` — writes MCP config for Claude Desktop, Cursor, VS Code, etc.
- `bioimage-mcp list-envs` / `bioimage-mcp list-tools` — show installed environments and tools

**Install flow:**
```bash
# 1) Install core server package (lightweight)
pip install bioimage-mcp

# 2) Bootstrap environments + resources
bioimage-mcp install --profile cpu   # or --profile gpu

# 3) Configure host app (optional convenience)
bioimage-mcp configure claude-desktop

# 4) Run (stdio for MCP)
bioimage-mcp serve --stdio
```

## 9. Clean MCP Surface (8 Tools)
The MCP surface is intentionally small and consistent to prevent context bloat.

### 9.1 Tool Surface
| Tool | Purpose |
|------|---------|
| `list` | Browse catalog (environments, packages, modules, functions) with pagination and child counts |
| `describe` | Get full details for any catalog node (functions include `inputs`, `outputs`, `params_schema`) |
| `search` | Find functions by query, tags, or I/O types with ranked results |
| `run` | Execute a single function with separate `inputs` and `params` fields |
| `status` | Poll running executions with progress information |
| `artifact_info` | Retrieve artifact metadata and optional text preview |
| `session_export` | Export reproducible workflow records with `external_inputs` and step provenance |
| `session_replay` | Re-run workflows on new external inputs with optional param overrides |

### 9.2 Discovery Principles
- `list` returns child counts (`total` and `by_type`) for every non-leaf node.
- `list` includes lightweight I/O summaries for function nodes to reduce follow-up calls.
- `describe` for functions returns correct JSON Schema types (numbers as numbers, booleans as booleans).
- Artifact ports (`inputs`/`outputs`) are always separate from `params_schema`.

### 9.3 LLM Guidance Hints
To guide the LLM through complex workflows:
- **Input Schemas**: `describe` returns semantic input requirements (e.g., `expected_axes: ["Y", "X"]`).
- **Next-Step Hints**: `describe` includes `next_steps` with suggested follow-up functions and reasons.
- **Error Hints**: Failures provide structured errors with JSON Pointer paths and actionable hints.
- **Examples**: `describe` includes example `inputs` and `params` for common use cases.

## 10. napari-mcp Integration
- napari-mcp focuses on controlling napari interactively through MCP.
- Bioimage-MCP treats napari as an optional "viewer plane":
  - push artifacts as layers for inspection
  - pull edited labels back into the artifact store
  - keep headless workflows as the default mode

## 11. Security & Safety (local-first)
- Subprocess + env isolation is a security boundary, but not a sandbox; document that tool code runs with user privileges.
- Add allowlists for:
  - filesystem roots that workflows may read/write
  - network access (off by default if desired)
- Record provenance (inputs, parameters, tool versions, env lock hashes).

## 12. Suggested Repo Layout
```
bioimage_mcp/           # Core server
├── registry/           # Tool index, manifests, plugins
├── workflows/          # Workflow spec, replay logic
├── artifacts/          # Store + serializers
├── bootstrap/          # Installer, doctor, env manager
└── shims/              # Base env tool wrappers
envs/                   # Conda env YAML + lockfiles
tools/                  # Per-tool shims and manifests
tests/                  # Unit + integration tests
datasets/               # Git LFS-tracked test data
```

## 13. Development Toolkit
- **MCP**: `mcp` (official Python SDK for MCP servers)
- **Python**: 3.13 for core server (highest compatible with base env deps)
  - Tool envs may pin Python independently per project requirements
- **Linting**: `ruff` (fast Python linter and formatter)
- **Testing**: `pytest`, `pytest-cov` (coverage targets: 80%+)
  - **Workflow Test Harness**: Specialized harness (`MCPTestClient`) for end-to-end simulation of LLM tool interactions.
- **Environment**: `conda-lock`, `micromamba` (fast reproducible envs)
- **Data versioning**: Git LFS for test datasets
- **Type checking**: `pyright`
- **Documentation**: `mkdocs` with `mkdocs-material`

## 14. Structured Error Model
All MCP tools return structured errors for actionable LLM self-correction.

### 14.1 Error Response Shape
```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Missing required input 'image'",
    "details": [
      {
        "path": "/inputs/image",
        "expected": "BioImageRef",
        "actual": "missing",
        "hint": "Provide a BioImageRef from a prior tool output"
      }
    ]
  }
}
```

### 14.2 Error Codes
| Code | Meaning |
|------|---------|
| `VALIDATION_FAILED` | Input/param validation failed |
| `NOT_FOUND` | Catalog node or artifact not found |
| `EXECUTION_FAILED` | Tool execution crashed or timed out |
| `PERMISSION_DENIED` | Path outside allowed roots |
| `REPLAY_FAILED` | Workflow replay validation or execution failed |

### 14.3 Error Details
- `path`: JSON Pointer to the problematic field (e.g., `/inputs/image`, `/params/sigma`)
- `expected`: What was expected (type, value range, etc.)
- `actual`: What was received
- `hint`: Actionable guidance for automated retry or user correction

