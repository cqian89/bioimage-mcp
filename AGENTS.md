# bioimage-mcp Agent Guidelines

This repository implements a Model Context Protocol (MCP) server for bioimage analysis.
Design goals: stable LLM-facing API, artifact-based I/O, isolated tool execution, and reproducible workflows.

## Architecture Principles

- **Artifact Boundary:** Tools communicate with the core server via artifacts (ObjectRef, BioImageRef), never raw memory arrays.
- **Dependency Isolation:** Heavy dependencies (torch, cellpose, etc.) belong in tool-specific conda environments.
- **Unified Introspection:** New tools MUST use the `Introspector` engine for dynamic discovery when possible.
- **Native Dims:** Preserve and emit native axes/dimensionality (e.g., YX, CYX) end-to-end. Avoid TCZYX padding.

## Repo Layout

```text
src/bioimage_mcp/          # Core server (Python 3.13)
  api/                     # MCP handlers: list/search/describe/run/status
  artifacts/               # Artifact models + S3/File/Memory backends
  bootstrap/               # CLI entrypoints (configure, doctor, serve)
  registry/                # Tool discovery and introspection engine
  runtimes/                # Conda-isolated subprocess execution

tools/                     # Tool packs (each has its own conda env + manifest)
  base/
  cellpose/
  tttrlib/

tests/                     # unit/contract/integration/smoke
envs/                      # Conda environment definitions (*.lock.yml)
.planning/                 # Current specifications and implementation documentation from gsd
specs/                     # Legacy feature specifications and implementation plans from spec-kit
```

## Tool Implementation (Introspection Engine)

Future tool implementations should prioritize dynamic discovery using the unified introspection engine:
1.  **Define Adapter:** Implement or reuse an adapter in `bioimage_mcp.registry.dynamic.adapters`.
2.  **Manifest Configuration:** Add `dynamic_sources` to `manifest.yaml` specifying modules and patterns.
3.  **Schema Extraction:** Use `bioimage_mcp.registry.dynamic.introspection.Introspector` to automatically generate `params_schema` from function signatures and NumPy-style docstrings.
4.  **Isolation:** Ensure the tool's isolated environment contains all required dependencies, including `docstring-parser` for rich schema extraction.

## Build & Run

```bash
# Install core server in editable mode with dev dependencies
python -m pip install -e ".[dev]"

# Configure local workspace and run diagnostics
bioimage-mcp configure
bioimage-mcp doctor

# Install tool environments (e.g., cellpose)
bioimage-mcp install --profile cpu

# Start the MCP server (stdio mode for LLM integration)
bioimage-mcp serve --stdio
```

## Testing (pytest)

Use `pytest` for all tests. Configuration is in `pytest.ini`.

```bash
# Run all tests
pytest

# Run a specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/smoke/

# Run a single test file
pytest tests/unit/api/test_artifacts.py

# Run a single test by name (with verbose output)
pytest tests/unit/api/test_artifacts.py::test_artifact_creation -v

# Filter by keyword
pytest -k "segmentation" -v

# Run environment-gated tests (requires specific conda env)
conda run -n bioimage-mcp-cellpose pytest -m requires_cellpose -v
```

**Common Markers:** `slow`, `integration`, `smoke_minimal`, `requires_env`, `mock_execution`.

## Lint & Format (ruff)

Ruff is used for both linting and formatting. Config is in `ruff.toml`.

```bash
# Check for lint errors and apply safe fixes
ruff check --fix .

# Format code according to project style
ruff format .
```

## Code Style Guidelines

### Imports
- Modules MUST start with `from __future__ import annotations`.
- Grouping: Standard library, third-party, first-party (`bioimage_mcp`).
- Let `ruff` handle ordering and formatting.

### Types & Naming
- **Type Hints:** Required for all public APIs and non-trivial helpers. Use modern syntax: `str | None`.
- **Naming:** `PascalCase` for classes, `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants.
- **Pydantic:** Use Pydantic v2 for all models. Prefer `Field(default_factory=...)` for collections.

### Error Handling
- Use structured errors from `bioimage_mcp.errors`.
- Raise `BioimageMcpError` subclasses with stable error codes for user-facing issues.
- Avoid swallowing exceptions; let unexpected bugs bubble up to the global handler.

## MCP API Nuances
- **Omit Empty Params:** When calling `run` on a function with no parameters, OMIT the `params` field entirely. Passing `params={}` may fail schema validation.
- **Describe Protocol:** Tools must support `meta.describe` to return their dynamic `params_schema`.
