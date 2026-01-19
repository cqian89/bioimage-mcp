# bioimage-mcp Agent Guidelines

This repo implements an MCP server for AI-driven bioimage analysis.
Design goals: stable LLM-facing API, artifact-based I/O, isolated tool execution, reproducible workflows.

## Repo Layout

```text
src/bioimage_mcp/          # Core server (Python 3.13)
  api/                     # MCP handlers: list/search/describe/run/status + artifacts
  artifacts/               # Artifact models + storage backends
  bootstrap/               # install/configure/doctor/serve entrypoints
  config/                  # YAML config loader + schema
  registry/                # Tool discovery/manifest/introspection
  runtimes/                # Subprocess execution + worker protocol
  sessions/                # Session store + models
  runs/                     # Workflow recording

tools/                     # Tool packs (each has its own conda env + manifest)
  base/
  cellpose/
  tttrlib/

tests/                     # unit/contract/integration/smoke
envs/                      # conda env definitions + lockfiles
specs/                     # feature specs
```

## Build / Run

```bash
# Editable install (core server)
python -m pip install -e .

# Dev deps (ruff/pytest/etc.)
python -m pip install -e ".[dev]"

# Create starter local config
bioimage-mcp configure

# Install tool environments (CPU profile installs base + cellpose envs)
bioimage-mcp install --profile cpu

# Readiness checks
bioimage-mcp doctor
bioimage-mcp doctor --json

# Start the MCP server
bioimage-mcp serve
bioimage-mcp serve --stdio
```

Notes:
- CLI entrypoint: `bioimage-mcp` (see `pyproject.toml` -> `bioimage_mcp.cli:main`).
- Env manager: micromamba preferred; conda/mamba supported.

## Tests (pytest)

`pytest.ini` sets `addopts = -q` (quiet) and extends `pythonpath` with `src` and `tools/*`.

```bash
# Run everything
pytest

# Run a directory
pytest tests/unit/
pytest tests/contract/
pytest tests/integration/
pytest tests/smoke/

# Run a single test file
pytest tests/unit/api/test_artifacts.py

# Run a single test by node id
pytest tests/unit/api/test_artifacts.py::test_artifact_creation -v

# Filter by keyword
pytest -k "artifact and not export" -v

# Filter by marker (see pytest.ini)
pytest -m "not slow" -v
pytest -m "smoke_minimal" -v
pytest -m "integration" -v

# Run env-gated tests inside the tool env
conda run -n bioimage-mcp-base pytest -m requires_base -v
conda run -n bioimage-mcp-cellpose pytest -m requires_cellpose -v
```

Common markers (subset): `slow`, `integration`, `smoke_minimal`, `smoke_full`,
`requires_base`, `requires_cellpose`, `requires_env`, `mock_execution`, `real_execution`.

## Lint / Format (ruff)

```bash
ruff check .
ruff format --check .

ruff check --fix .
ruff format .
```

## Code Style (Python)

### Imports

- Always start modules with `from __future__ import annotations`.
- Ordering: stdlib, third-party, first-party (`bioimage_mcp`).
- Don’t hand-format imports; rely on `ruff`.

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from bioimage_mcp.errors import BioimageMcpError
```

### Formatting

- `ruff format` is the source of truth.
- Line length is 100 (`ruff.toml`).

### Types

- Type-hint all public functions and non-trivial helpers.
- Prefer modern typing: `str | None`, `list[str]`, `dict[str, Any]`.
- Use `Literal[...]` for constrained strings.

### Naming

- Classes `PascalCase`, functions `snake_case`, constants `UPPER_SNAKE_CASE`.
- Private helpers/fields start with `_`.

### Pydantic (v2)

- All API/schema models use Pydantic v2.
- Use `Field(default_factory=...)` for mutable defaults.
- Prefer `field_validator` / `model_validator`; keep validators deterministic (no I/O).

### Error Handling

- User-facing errors: raise subclasses of `BioimageMcpError` with stable `code` and optional
  structured `details` (`src/bioimage_mcp/errors.py`).
- Unexpected bugs: `InternalBioimageMcpError` or let exceptions bubble to the global handler.

### MCP API Gotcha (important)

- For MCP `run` requests, when a function has no required parameters, OMIT `params` entirely.
  Passing `params={}` can fail schema validation.

## Architecture Constraints (non-negotiable)

- Artifact boundary: tool packs communicate with the core server via artifacts (not raw arrays).
- Image I/O: use `bioio` / `bioio-ome-tiff` / `bioio-ome-zarr` for artifact read/write.
  Avoid `tifffile` and `skimage.io` for artifact I/O.
- Dependency isolation: heavy deps (torch/cellpose/etc.) must NOT be added to the core server.
  They belong in tool-pack conda envs defined in `envs/` and run via `conda run -n ...`.
- Reproducibility: workflows should be recordable/replayable (steps/params/versions).

## Cursor / Copilot Rules

- No Cursor rules found (no `.cursor/rules/` and no `.cursorrules`).
- No GitHub Copilot instructions found (no `.github/copilot-instructions.md`).
