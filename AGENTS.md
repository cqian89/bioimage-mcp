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

# Run tool-specific integration tests (requires conda env)
conda run -n bioimage-mcp-cellpose pytest tests/integration/test_cellpose*.py -v

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

# Manage artifact storage and quotas
python -m bioimage_mcp storage status
python -m bioimage_mcp storage list --state expired
python -m bioimage_mcp storage prune --dry-run
python -m bioimage_mcp storage pin <session_id>

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
- Full schemas fetched only via `describe(id)`
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
- Support `session_replay` for recorded workflows

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

### Testing in Tool-Specific Environments

Tool packs like Cellpose have heavy dependencies (torch, cellpose) that are isolated in their own conda environments per Constitution Principle 2. This means:

- **Unit tests** (in `tests/unit/`) must mock tool-specific dependencies and run in the core environment
- **Integration tests** (in `tests/integration/`) should run in the tool's conda environment for real validation

#### Running Cellpose Integration Tests

```bash
# Run Cellpose-specific integration tests in the Cellpose environment
conda run -n bioimage-mcp-cellpose pytest tests/integration/test_cellpose*.py -v

# Run the full integration suite (requires all tool envs)
conda run -n bioimage-mcp-cellpose pytest tests/integration/ -v

# Run only tests that don't require special environments
pytest -m "not requires_cellpose" tests/integration/
```

#### Running Tests Without Heavy Dependencies

```bash
# Run only unit tests (no heavy deps required)
pytest tests/unit/ tests/contract/ -v

# Skip slow tests and tests requiring tool environments
pytest -m "not slow and not requires_cellpose"
```

#### Test Markers for Tool Dependencies

Use pytest markers to indicate environment requirements:

```python
import pytest

# Mark tests that require Cellpose environment
@pytest.mark.requires_cellpose
def test_cellpose_segmentation():
    ...

# Mark tests that require any specific tool env
@pytest.mark.requires_env("bioimage-mcp-cellpose")
def test_with_cellpose():
    ...

## Smoke Tests

The smoke test suite validates live server functionality against real MCP interactions.

### Running Smoke Tests

```bash
# Run minimal smoke tests (for CI)
pytest tests/smoke/ -m smoke_minimal -v

# Run full smoke tests (includes optional environments)
pytest tests/smoke/ -v

# Run with recording mode for debugging
pytest tests/smoke/ --smoke-record -v

# View interaction logs
ls .bioimage-mcp/smoke_logs/
```

### Test Markers

- `smoke_minimal`: Fast tests for CI (base environment only)
- `smoke_full`: Complete tests (may require optional tool environments)
- `requires_env("env-name")`: Tests requiring specific conda environments

### Smoke Test Structure

```text
tests/smoke/
├── conftest.py                     # Fixtures (live_server, sample_image, etc.)
├── test_smoke_basic.py             # Basic discovery and run tests
├── test_flim_phasor_live.py        # FLIM phasor workflow
├── test_cellpose_pipeline_live.py  # Cellpose segmentation pipeline
├── test_smoke_recording.py         # Recording mode tests
└── utils/
    ├── mcp_client.py               # TestMCPClient wrapper
    └── interaction_logger.py       # Interaction logging utilities
```

### Recording Mode

When `--smoke-record` is enabled, interaction logs are saved to `.bioimage-mcp/smoke_logs/`. Each log contains:
- Test metadata (name, timestamps, status)
- Full request/response sequence
- Server stderr (if captured)
- Error summary on failure

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
- **NativeOutputRef**: Tool-native output bundle (format is tool-dependent)
- **ObjectRef**: Serialized Python object (e.g., ML model) held in tool memory.
  - Fields: `ref_id`, `uri` (starting with `obj://`), `python_class` (fully qualified name), `storage_type` ("memory").
  - Example: `{"type": "ObjectRef", "uri": "obj://...", "python_class": "cellpose.models.CellposeModel"}`

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

## API Usage Notes

### Handling Functions with No Parameters
When calling a function via `run` that has no required parameters (or all parameters have defaults and you wish to use them), you **MUST omit the `params` field entirely**. Passing an empty dictionary or a placeholder will cause a validation error in the tool runtime.

- ✅ **Correct:** `run(fn_id="base.xarray.squeeze", inputs={"img": "..."})`
- ❌ **Incorrect:** `run(fn_id="base.xarray.squeeze", inputs={"img": "..."}, params={})`
- ❌ **Incorrect:** `run(fn_id="base.xarray.squeeze", inputs={"img": "..."}, params={"_placeholder": true})`

## Common Tasks

### Adding a new function to base toolkit
1. Add function implementation in `tools/base/bioimage_mcp_base/ops/`
   - **Important**: Use `bioio.BioImage` for all input reading to ensure consistent 5D TCZYX data access.
   ```python
   from bioio import BioImage
   img = BioImage(path)
   data = img.data # Always 5D TCZYX
   ```
2. Add function definition to `tools/base/manifest.yaml`
3. Write contract test in `tests/contract/`
4. Write unit test (TDD: write failing test first)

### Standard BioImage Loading Pattern
When implementing image processing functions, use `bioio.BioImage` for consistent data access:

**Native loading (preserves 2D, 3D, etc.)** - RECOMMENDED:
```python
from bioio import BioImage
img = BioImage(path)
data = img.reader.data  # Native dimensions
dims = img.reader.dims.order  # e.g., "ZYX"
```

**Legacy 5D loading** (when tools require TCZYX):
```python
from bioio import BioImage
img = BioImage(path)
data = img.data  # Always 5D TCZYX
pixel_sizes = img.physical_pixel_sizes  # (Z, Y, X) in microns
channels = img.channel_names  # List of channel names
```

This ensures:
- Consistent handling of all supported formats (OME-TIFF, CZI, LIF, etc.)
- Normalized 5D axis ordering (if using `.data`) or preserved native axes (if using `.reader.data`)
- Access to physical metadata for downstream processing

### Standard BioImage Writing Pattern
When writing image artifacts, use bioio writers directly:

**Writing OME-TIFF**:
```python
from bioio.writers import OmeTiffWriter
OmeTiffWriter.save(data, path, dim_order="TCZYX")
```

**Writing OME-Zarr**:
```python
from bioio_ome_zarr.writers import OMEZarrWriter
writer = OMEZarrWriter(store=path, level_shapes=[data.shape], dtype=data.dtype)
writer.write_full_volume(data)
```

**Anti-patterns to avoid**:
- ❌ Do NOT create custom I/O wrapper functions around BioImage
- ❌ Do NOT use raw `zarr.open_group()` for OME-Zarr output
- ❌ Do NOT use `tifffile` or `skimage.io` for artifact I/O

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
- Python 3.13 (core server); Python 3.13 (base tool env) + MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `phasorpy`, `bioio-bioformats` (006-phasor-usability-fixes)
- Python 3.13 (core server); Python 3.13 (base tool env) + MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `numpy`, `pytest`, `pytest-asyncio`, `pyyaml` (007-workflow-test-harness)
- Python 3.13 (core server); Python 3.13 (base tool env) + MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `numpy`, `pytest`, `pyyaml` (008-api-refinement)
- Python 3.13 (core server; tool envs may differ) + MCP Python SDK (`mcp`), `pydantic>=2.0`, `bioio`, `zarr`, `bioio-ome-zarr`, `bioio-ome-tiff` (014-native-artifact-types)
- Python 3.13 (core server; tool envs may differ) + MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `fastmcp` (016-mcp-interface-redesign)
- Python 3.13 (core server; tool envs may differ) + MCP Python SDK (`mcp`), `pydantic`, `bioio`, `torch`, `cellpose` (017-cellpose-api)
- Local filesystem artifact store (pickle for objects) + SQLite index (017-cellpose-api)
- Interaction logs stored as JSON artifacts in `tests/smoke/logs/` or `.bioimage-mcp/smoke_logs/` (018-live-server-smoke-tests)

## Recent Changes
- 004-interactive-tool-calling: Added Python 3.13 (core server; tool envs may differ)
