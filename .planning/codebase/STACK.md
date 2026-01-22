# Technology Stack

**Analysis Date:** 2026-01-22

## Languages

**Primary:**
- Python 3.13 - Core server implementation and tool packs.

**Secondary:**
- SQL (SQLite) - Metadata storage for artifacts, tools, and sessions.
- YAML - Configuration and environment definitions.

## Runtime

**Environment:**
- Python 3.13
- Conda / Micromamba - Used for isolated tool execution environments.

**Package Manager:**
- pip - Core server dependency management.
- micromamba/conda - Tool-pack dependency isolation (e.g., `envs/bioimage-mcp-cellpose.yaml`).
- Lockfile: `envs/conda-lock.yml`, `envs/bioimage-mcp-base.lock.yml` present.

## Frameworks

**Core:**
- Model Context Protocol (MCP) - Standard for AI-driven tool execution.
- Pydantic v2 - Data validation and settings management (`src/bioimage_mcp/config/schema.py`).
- PyYAML - Configuration loading and tool manifests.

**Testing:**
- pytest 8.x - Test runner.
- pytest-asyncio - For asynchronous testing.

**Build/Dev:**
- ruff - Linting and formatting.
- setuptools - Build backend and entry point definition.

## Key Dependencies

**Critical:**
- `mcp` - Core MCP server library.
- `bioio`, `bioio-ome-zarr`, `bioio-ome-tiff` - Scientific image I/O library for OME-TIFF and OME-Zarr.
- `ngff-zarr` - Zarr implementation for next-generation file formats.

**Infrastructure:**
- `pydantic` - Schema definition and validation.
- `PyYAML` - Parsing tool manifests and configuration.

## Configuration

**Environment:**
- Configured via `.bioimage-mcp/config.yaml` or user-defined paths.
- Key configs include `artifact_store_root`, `tool_manifest_roots`, and worker process settings.

**Build:**
- `pyproject.toml` - Project metadata, dependencies, and entry points.

## Platform Requirements

**Development:**
- Python 3.13+
- Micromamba or Conda for environment management.

**Production:**
- Local execution environment with access to filesystem for artifact storage.

---

*Stack analysis: 2026-01-22*
