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
- Base env (`bioimage-mcp-base`): Python 3.13, bioio, ngff-zarr, PhasorPy, core utilities.
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

### 3.2 Fast installs
- Use **micromamba** to create envs quickly and to install from lockfiles.
- Ensure the **libmamba solver** is used when solving is needed.
- **Reference**: `MicroscopyLM/src/miclm/env/manager.py` contains logic for `doctor` checks and environment bootstrapping.

## 4. Artifact Model (the glue between envs)

### 4.1 Artifact references
All tool inputs/outputs are passed by reference, never by embedding large arrays in MCP messages.

Core types:
- `BioImageRef` (OME-Zarr/OME-TIFF; includes axes, physical pixel sizes, channel names)
- `LabelImageRef`
- `TableRef` (parquet/csv)
- `ModelRef`
- `LogRef`

**Artifact reference contract:**
```yaml
ref:
  uri: "file:///path/to/output.ome.zarr"  # v0.1: file:// only; S3 in upgrade path
  mime_type: "application/zarr+ome"
  format: "OME-Zarr"
  size: 1048576
  checksums: {sha256: "abc123..."}
  metadata: {axes: "TCZYX", channels: ["DAPI", "GFP"], ...}
```

### 4.2 Preferred storage
- OME-Zarr (OME-NGFF) as the default intermediate format for chunked, scalable datasets.
- Use proven libraries:
  - **bioio** + plugins (`bioio-ome-zarr`, `bioio-ome-tiff`) for reading diverse microscopy formats.
  - **ngff-zarr** imported as a Python library for OME-Zarr writing, conversion, and validation.

## 5. Tool & Function Metadata
Each tool provides a manifest (YAML) containing:
- Tool identity: `tool_id`, `env_id`, version, entrypoint
- `python_version` (required Python for this tool)
- `platforms_supported` (e.g., `[linux-64, osx-arm64, win-64]`)
- Functions:
  - `fn_id` (stable), description, tags
  - `inputs` and `outputs` (typed ports)
  - resource hints (GPU/CPU/memory)
  - **upstream/downstream** associations for planning and UI suggestions

The core server indexes these manifests for fast `search_functions(...)`.
- **Reference**: `MicroscopyLM/src/miclm/tools/registry.py` implements the layered registry (builtin/user/project).

### 5.1 Shim Execution Model (MVP)
- **Subprocess per call**: core server spawns a Python subprocess in the tool's conda env
- **Logs**: written to artifact store as `LogRef`
- **Timeout/cancellation**: SIGTERM after configurable timeout, SIGKILL after grace period
- **GPU selection**: inherits `CUDA_VISIBLE_DEVICES` from parent, or tool manifest can override
- **Roadmap**: persistent workers for heavy runtimes (Cellpose, StarDist) in post-MVP

## 6. Workflow Execution (MVP: LLM-driven linear plan)

### 6.1 MVP approach
- LLM plans and calls tools sequentially via MCP; no formal DAG engine required.
- Workflows are **linear plans**: ordered steps with typed I/O validation.
- Workflows are saved as **JSON/Markdown artifacts** for reproducibility.
- `replay_workflow(artifact_path)` is exposed as an MCP function for re-execution.

### 6.2 Post-MVP: DAG engine integration
Consider integrating **Pydra** if/when:
- Complex parallel pipelines emerge (batch processing hundreds of images)
- Formal caching by parameter/input hash becomes essential
- Users request automated retries with exponential backoff

Alternatives for "platform" features: **Prefect** or **Dagster**.

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

## 9. Constant LLM-facing API (anti–context-bloat)
- All discovery endpoints are **paginated**; default responses are summaries.
- The LLM fetches full schemas only via `describe_function(fn_id)` for the specific functions it needs.
- Workflow execution returns opaque IDs (`workflow_id`, `run_id`, `artifact_ref`) and lets the client fetch details on demand.

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
- **Environment**: `conda-lock`, `micromamba` (fast reproducible envs)
- **Data versioning**: Git LFS for test datasets
- **Type checking**: `pyright`
- **Documentation**: `mkdocs` with `mkdocs-material`
