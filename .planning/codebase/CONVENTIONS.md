# Coding Conventions

**Analysis Date:** 2026-01-22

## Naming Patterns

**Files:**
- snake_case: `src/bioimage_mcp/api/artifacts.py`, `tests/unit/api/test_artifacts.py`

**Functions:**
- snake_case: `def list_tools(self, path: str | None = None, ...):` in `src/bioimage_mcp/api/discovery.py`

**Variables:**
- snake_case: `session_id`, `created_at` in `src/bioimage_mcp/sessions/models.py`
- Private variables/helpers: `_DEFAULT_FORMAT` in `src/bioimage_mcp/logging.py`

**Types:**
- PascalCase: `class ArtifactsService:`, `class Session(BaseModel):`

## Code Style

**Formatting:**
- Tool: `ruff`
- Line length: 100 (configured in `ruff.toml`)

**Linting:**
- Tool: `ruff`
- Key rules: `select = ["E", "F", "I", "UP", "B"]` (Error, Pyflakes, Isort, Pyupgrade, Bugbear)

## Import Organization

**Order:**
1. Future imports: `from __future__ import annotations`
2. Standard library
3. Third-party (e.g., `pydantic`, `pytest`)
4. First-party: `bioimage_mcp`

**Path Aliases:**
- Not detected.

## Error Handling

**Patterns:**
- Custom exception hierarchy in `src/bioimage_mcp/errors.py`:
  - `BioimageMcpError`: Base class for user-facing errors with a stable `code`.
  - `InternalBioimageMcpError`: Unexpected errors indicating a bug.
- API responses include structured error objects: `{"error": {"message": "...", "code": "..."}}`.

## Logging

**Framework:** Standard library `logging`

**Patterns:**
- Configured in `src/bioimage_mcp/logging.py`.
- Format: `%(asctime)s %(levelname)s %(name)s: %(message)s`
- Level controlled by `BIOIMAGE_MCP_LOG_LEVEL` env var.
- Use `get_logger(name)` to obtain a logger.

## Comments

**When to Comment:**
- Docstrings for public classes and functions.
- Inline comments for complex logic or test setup.

**JSDoc/TSDoc:**
- Use standard Python docstrings (`"""Docstring"""`).

## Function Design

**Size:** Generally focused and modular.

**Parameters:** Type-hinted. Prefer modern typing (e.g., `str | None`).

**Return Values:** Type-hinted.

## Module Design

**Exports:** Explicitly defined in `__init__.py` or via public classes/functions.

**Barrel Files:** `__init__.py` files used for package structure.

---

*Convention analysis: 2026-01-22*
