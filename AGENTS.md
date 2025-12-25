# bioimage-mcp Agent Guidelines

MCP server for AI-driven bioimage analysis with isolated tool environments, artifact-based I/O, and reproducible workflows.

## Project Structure

```text
src/bioimage_mcp/          # Core server code
  api/                     # MCP API handlers (tools, artifacts, discovery)
  artifacts/               # Artifact reference models and storage
  bootstrap/               # Install, doctor, environment checks
  config/                  # Layered YAML configuration
  registry/                # Tool manifest discovery and validation
  runs/                    # Workflow run records and logs
  runtimes/                # Subprocess executor for isolated tools
  storage/                 # Local filesystem + SQLite index

tools/                     # Tool packs (each with isolated environment)
  base/                    # Base image ops (scikit-image): I/O, transforms, preprocessing
  builtin/                 # Built-in ops: Gaussian blur, format conversion
  cellpose/                # Cell segmentation (Cellpose)

tests/
  unit/                    # Fast, isolated unit tests
  contract/                # Schema and API contract tests
  integration/             # End-to-end and live workflow tests

specs/                     # Feature specifications (per-milestone)
  000-v0-bootstrap/        # v0.0: Install, discovery, basic execution
  001-cellpose-pipeline/   # v0.1: Cellpose segmentation, workflow replay
  002-base-tool-schema/    # v0.2: Base toolkit expansion, schema enrichment
  003-base-tool-schema/    # v0.3: FLIM phasor analysis

datasets/                  # Sample data for validation
envs/                      # Conda environment definitions + lockfiles
```

## Development Commands

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/contract/
pytest tests/integration/

# Run a single test file
pytest tests/unit/api/test_artifacts.py

# Lint and format check
ruff check .
ruff format --check .

# Fix linting issues
ruff check --fix .
ruff format .

# Start the MCP server
python -m bioimage_mcp serve

# Run doctor/readiness checks
python -m bioimage_mcp doctor

# Validate pipeline (sample workflow)
python scripts/validate_pipeline.py
```

## Code Style

- **Python 3.13** for core server; tool envs may pin different versions
- **ruff** for linting and formatting (see `ruff.toml`)
- **pydantic v2** for all data models and validation
- Type hints required on all public functions
- Docstrings: Google style, required for public API

## Architecture Constraints

These are non-negotiable project rules from `.specify/memory/constitution.md`:

### 1. Stable MCP Surface (Anti-Context-Bloat)
- Discovery responses MUST be paginated and default to summaries
- Full schemas fetched only via `describe_function(fn_id)`
- Tool calls return IDs and artifact references, NOT large payloads

### 2. Isolated Tool Execution
- Each tool runs in its own `bioimage-mcp-*` conda/micromamba environment
- Tool processes are subprocesses; crashes don't affect the core server
- Heavy stacks (PyTorch, TensorFlow, Java/Fiji) MUST NOT be in core server env

### 3. Artifact References Only
- All I/O via typed, file-backed artifact references (URI + metadata)
- Image artifacts use OME-TIFF (v0.1+); OME-Zarr for intermediate storage
- Never embed large arrays/binaries in MCP messages

### 4. Reproducibility & Provenance
- Environments pinned via `conda-lock` lockfiles
- Workflow runs record: steps, params, tool versions, lockfile hashes, timestamps
- Support `replay_workflow` for recorded workflows

### 5. Safety & Observability
- Subprocess boundaries for fault isolation (not security sandboxing)
- File/network access via explicit allowlists
- Structured logs persisted as artifacts
- All core changes require automated tests

### 6. Test-Driven Development
- **Red**: Write failing test BEFORE implementation
- **Green**: Minimum code to pass
- **Refactor**: Improve while keeping tests green
- PRs without tests-first MUST be rejected

## Testing Guidelines

```bash
# Contract tests verify API schemas and MCP protocol compliance
pytest tests/contract/

# Integration tests require tool environments to be installed
pytest tests/integration/ -v

# Skip slow/live tests
pytest -m "not slow"
```

Key test patterns:
- Use `conftest.py` fixtures for sample data and temporary artifact stores
- Contract tests validate manifest schemas match tool definitions
- Integration tests use `datasets/FLUTE_FLIM_data_tif/` for real image data

## Tool Pack Development

Each tool pack in `tools/<name>/` must have:

1. **`manifest.yaml`**: Tool identity, functions, environment requirements
2. **`bioimage_mcp_<name>/`**: Python package with function implementations
3. **Function schema**: Pydantic models for inputs/outputs/params

Example manifest structure:
```yaml
tool_pack:
  id: bioimage-mcp-cellpose
  version: "0.1.0"
  environment:
    name: bioimage-mcp-cellpose
    lockfile: envs/bioimage-mcp-cellpose.lock.yml

functions:
  - id: cellpose.segment
    summary: Cell segmentation using Cellpose
    inputs: [BioImageRef]
    outputs: [LabelImageRef]
    params_schema: ...
```

## Configuration

Layered YAML config (lower overrides higher):
1. Global: `~/.bioimage-mcp/config.yaml`
2. Local: `.bioimage-mcp/config.yaml`

Key settings:
- `artifact_store.root`: Where artifacts are stored
- `filesystem.allowed_read`: Allowlisted read paths
- `filesystem.allowed_write`: Allowlisted write paths

## Artifact Types

- **BioImageRef**: Input/intermediate microscopy images
- **LabelImageRef**: Segmentation label images (0=background, 1..N=instances)
- **TableRef**: Measurement/feature tables
- **LogRef**: Run logs
- **NativeOutputRef**: Workflow records (format: `workflow-record-json`)

## PR Guidelines

Every PR MUST include:
1. **Constitution Check**: Which principles apply and how they're satisfied
2. **Tests**: Written first (TDD), covering new functionality
3. **Migration notes**: If changing public contracts (MCP API, artifact schemas)

## Key Dependencies

Core server:
- `mcp` (MCP Python SDK)
- `pydantic` v2
- `bioio`, `bioio-ome-tiff`
- `sqlite3` (stdlib)

Base toolkit:
- `scikit-image`
- `numpy`, `scipy`

Cellpose environment:
- `cellpose`
- `torch` (optional, for GPU)

## Common Tasks

### Adding a new function to base toolkit
1. Add function implementation in `tools/base/bioimage_mcp_base/ops/`
2. Add function definition to `tools/base/manifest.yaml`
3. Write contract test in `tests/contract/`
4. Write unit test (TDD: write failing test first)

### Running a workflow end-to-end
```bash
# Ensure environments are installed
python -m bioimage_mcp doctor

# Run validation pipeline
python scripts/validate_pipeline.py
```

### Debugging tool execution failures
1. Check run logs in artifact store
2. Verify tool environment with `conda activate bioimage-mcp-<tool>`
3. Run tool directly in isolation to reproduce

## Troubleshooting

- **Missing micromamba**: Install from https://mamba.readthedocs.io/
- **Environment creation fails**: Check `envs/*.lock.yml` matches platform
- **Tool not found**: Run `python -m bioimage_mcp doctor` for diagnostics
- **Artifact not accessible**: Verify path is in `filesystem.allowed_read`

## Resources

- Specs: `specs/<milestone>/spec.md` for feature requirements
- Constitution: `.specify/memory/constitution.md` for non-negotiable rules
- PRD: `initial_planning/Bioimage-MCP_PRD.md` for product vision

## Active Technologies
- Python 3.13 (core server; tool envs may differ) (004-interactive-tool-calling)
- Python 3.13 (core server; tool envs may differ) + MCP Python SDK (`mcp`), `pydantic`, `bioio`, `ngff-zarr` (005-dynamic-function-registry)
- Local filesystem artifact store + SQLite index (MVP) (005-dynamic-function-registry)

## Recent Changes
- 004-interactive-tool-calling: Added Python 3.13 (core server; tool envs may differ)
