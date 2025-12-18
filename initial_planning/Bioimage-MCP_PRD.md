# Bioimage-MCP PRD

## 1. Overview
Bioimage-MCP is an MCP server for **bioimage analysis** that exposes a **stable, compact LLM-facing interface** while orchestrating a growing set of analysis tools installed in **isolated conda environments** (e.g., Cellpose, StarDist, PhasorPy, pyimagej/Fiji). The server supports **tool discovery**, **workflow construction**, **workflow execution**, and **artifact/provenance management** without requiring the LLM to ingest the entire tool catalog (avoiding context bloat).

## 2. Goals
- Provide a **constant MCP interface** while the toolset scales (discoverable on demand via `list/search/describe`).
- Run tools in **separate conda envs** for dependency isolation (ML stacks, Java/Fiji).
- Support **workflow planning and execution** as a **linear plan** with typed I/O and validation.
- Make the toolset **extendable by user config** (new env + manifest).
- Standardize I/O via **file-backed artifact references** (OME-TIFF preferred; OME-Zarr (OME-NGFF) is a future goal).

## 3. Non-goals (v1)
- Building a full interactive GUI (napari is integrated as an optional viewer tool instead).
- Replacing napari's plugin ecosystem.
- Providing a hosted multi-tenant SaaS (v1 is local/on-prem).
- Building a formal DAG execution engine (MVP uses LLM-driven sequential calling).

## 4. Primary Users
- Bioimage analysts and microscopy researchers who want LLM-assisted pipelines.
- Tool developers who want to expose their algorithms via MCP with minimal glue code.
- Platform engineers who want reproducible, versioned analysis runs.

## 5. Key Use Cases
1) **Tool discovery**
- "What segmentation tools are available?" → list tools/functions with minimal summaries.
- "What are Cellpose input/output formats?" → describe a specific function schema.

2) **Workflow authoring**
- Compose: load → preprocess → segment → measure → export.
- Validate I/O compatibility before execution.

3) **Workflow execution**
- Execute linear plan steps in the correct env; persist intermediates as artifacts.
- Provide run status, logs, and output handles.

4) **Extensibility**
- User adds a new tool by dropping:
  - conda env spec + lockfile
  - tool manifest
- Server registers it without changing the LLM-facing API.

## 6. Functional Requirements

### 6.1 MCP interface (stable)
- `list_tools(filter?, page_token?)`
- `search_functions(query, tags?, io_in?, io_out?, page_token?)`
- `describe_tool(tool_id)`
- `describe_function(fn_id)` (full schema: inputs/outputs/resources/upstream/downstream)
- `create_workflow(spec) -> workflow_id`
- `validate_workflow(workflow_id)`
- `run_workflow(workflow_id, inputs, run_opts?) -> run_id`
- `get_run_status(run_id)`
- `get_artifact(ref_id)` — returns metadata ref, never binary payload
- `export_artifact(ref_id, target_uri)` — v0.1 supports `file://` only
- `replay_workflow(artifact_path) -> run_id` — re-execute a recorded workflow

Implementation should use the **official MCP Python SDK** for server scaffolding and transports (stdio/SSE/HTTP), keeping protocol maintenance off the critical path.

### 6.2 Tool packaging & discovery

**Discovery mechanism (file-first):**
- Primary: manifests on disk at `tools/{tool}/tool.yaml`, indexed by core server
- Optional: Python entry points for in-core tools installed in the core env

**Shim interface:**
Each tool env provides a small shim that implements:
- `describe()` → tool/function JSON schemas
- `run(fn_id, inputs, params)` → writes outputs as artifacts and returns refs

**Shim execution model (MVP):**
- **Subprocess per call**: core server spawns a Python subprocess in the tool's conda env
- **Logs**: written to artifact store as `LogRef`
- **Timeout/cancellation**: SIGTERM after configurable timeout, SIGKILL after grace period
- **GPU selection**: inherits `CUDA_VISIBLE_DEVICES` from parent, or tool manifest can override
- **Roadmap**: persistent workers for heavy runtimes (Cellpose, StarDist) in post-MVP

**Tool manifest fields:**
- `tool_id`, `env_id`, `version`, `entrypoint`
- `python_version` (required Python version for this tool)
- `platforms_supported` (e.g., `[linux-64, osx-arm64, win-64]`)
- typed inputs/outputs (image/label/table/model refs)
- resource hints (CPU/GPU, memory)
- upstream/downstream associations for planning/auto-suggestions

### 6.3 Workflow execution (MVP: LLM-driven linear plan)
- **MVP approach**: LLM plans and calls tools sequentially via MCP; no formal DAG engine.
- Workflows are **linear plans**: an ordered list of steps with typed I/O validation between consecutive steps.
- Workflows are saved as **JSON/Markdown artifacts** for reproducibility, containing:
  - Tool calls with parameters (in execution order)
  - Input/output artifact references
  - Timestamps, tool versions, and environment lockfile hashes
- `replay_workflow(artifact_path)` is exposed as an MCP function for reproducibility.

**Post-MVP (v0.2+)**: Consider integrating a DAG engine (e.g., **Pydra**) if/when:
  - Complex parallel pipelines emerge (batch processing hundreds of images)
  - Formal caching by parameter/input hash becomes essential
  - Users request automated retries with exponential backoff

### 6.4 Artifact storage (I/O)
- Default artifact store: local filesystem + SQLite index (upgrade path to S3/MinIO).
- Preferred intermediate format: **OME-TIFF** for single-file portability and broad downstream tool support.
- Future goal: **OME-Zarr (OME-NGFF)** for chunked, scalable, cloud-optimized storage when workflows actually need it.
- Use established libraries:
  - **bioio** + plugins (`bioio-ome-tiff`, optional `bioio-ome-zarr`) for reading diverse microscopy formats.
  - **bioio-ome-tiff** (and/or `tifffile`) for writing OME-TIFF outputs.
  - Future: **ngff-zarr** for OME-Zarr writing/conversion if/when enabled.

**Artifact reference contract:**
All artifacts are passed by reference, never by embedding large payloads in MCP messages:
```yaml
ref:
  uri: "file:///path/to/output.ome.tiff"  # v0.1: file:// only; S3 in upgrade path
  mime_type: "image/tiff"
  format: "OME-TIFF"
  size: 1048576
  checksums: {sha256: "abc123..."}
  metadata: {axes: "TCZYX", channels: ["DAPI", "GFP"], ...}
```

### 6.5 Extensibility & user configuration
- **File-first discovery**: tool manifests at `tools/{tool}/tool.yaml` indexed by core server
- **Optional entry points**: for in-core tools installed in the core env
- **Optional pluggy hooks**: for advanced extensions (`validate_manifest`, `post_run`, etc.)

**User config directory** (`~/.bioimage-mcp/`):
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

### 6.6 Installer & bootstrap CLI
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

## 7. Non-Functional Requirements
- **Reproducibility**: pinned envs + recorded tool versions + parameterized workflow specs.
- **Performance**:
  - Prefer **conda-lock** to pre-solve and produce reproducible lockfiles (faster installs; no solver at install time).
  - Prefer **micromamba/libmamba** for fast environment creation (especially CI) and lockfile installation.
  - Ensure conda uses the **libmamba solver** (default on newer conda) when solving is required.
- **Robustness**: crash isolation across envs (subprocess boundaries), resumable runs.
- **Portability**: Linux-first; define support expectations for macOS/Windows where Java/Fiji and ML wheels may differ.

## 8. Differentiation vs napari-mcp
napari-mcp primarily provides MCP-based **remote control of the napari viewer** (interactive exploration/UI operations).

Bioimage-MCP differentiates by being:
- **workflow/orchestration-first** (headless pipelines, reproducible linear plan runs)
- **multi-environment compute plane** (Cellpose/StarDist/Fiji/etc. isolated)
- **typed artifact/provenance system** (OME-TIFF intermediates by default; OME-Zarr is a future goal)

napari remains a complementary tool: Bioimage-MCP can optionally expose napari as a viewer endpoint for visualization/QA.

## 9. Success Metrics
- Time-to-add a new tool pack (env + manifest) < 1 day.
- Median workflow run reproducibility: same inputs + same lockfiles → identical outputs (within numeric tolerance).
- LLM prompt size stays bounded: discovery is paginated; schemas fetched only on demand.

## 10. Milestones

### v0.0 (Bootstrap)
- Install/doctor CLI working
- Core server skeleton + artifact store (local filesystem + SQLite)
- Manifest indexing + `list_tools/search_functions/describe_function` working
- One trivial built-in function (e.g., Gaussian blur or format conversion)
- Base environment (`bioimage-mcp-base`) with Python 3.13, bioio (+ `bioio-ome-tiff`), and a small scientific stack for OME-TIFF I/O (e.g., `tifffile`), PhasorPy

### v0.1 (First Real Pipeline)
- Cellpose tool-pack running through artifact refs (read input → segment → write label ref)
- Workflow recording + `replay_workflow` via MCP
- Minimal integration tests on 1–2 small sample datasets
- TDD setup with Git LFS-managed test data

**Success criterion**: A user can install bioimage-mcp and run Cellpose on a sample image through the MCP interface.

### v0.2
- StarDist integration with tool-specific Python/TensorFlow constraints
- Caching by `(fn_id, params, input_hash)`
- Evaluate Pydra if parallel workflows needed

### v0.3
- pyimagej/Fiji integration
- Optional persistent workers for heavy runtimes

## 11. Development Toolkit
- **MCP**: `mcp` (official Python SDK for MCP servers)
- **Reference Implementation**: `MicroscopyLM` (prototype in `../MicroscopyLM/`)
  - **Registry**: `miclm.tools.registry` (Layered loading)
  - **Environment**: `miclm.env.manager` (Conda/Lock/Doctor)
  - **Execution**: `miclm.executors.python_subproc` (Isolated subprocesses)
- **Python**: 3.13 for core server (highest compatible with base env deps)
  - Tool envs may pin Python independently per project requirements
- **Linting**: `ruff` (fast Python linter and formatter)
- **Testing**: `pytest`, `pytest-cov` (coverage targets: 80%+)
- **Environment**: `conda-lock`, `micromamba` (fast reproducible envs)
- **Data versioning**: Git LFS for test datasets
- **Type checking**: `pyright`
- **Documentation**: `mkdocs` with `mkdocs-material`
