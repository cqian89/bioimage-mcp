# Codebase Structure

**Analysis Date:** 2026-01-22

## Directory Layout

```text
bioimage-mcp/
├── artifacts/              # Local storage for data and state
│   ├── objects/            # File-backed artifacts (hashed)
│   └── state/              # SQLite databases (registry, sessions)
├── docs/                   # User and developer documentation
├── envs/                   # Conda/Micromamba environment definitions
├── specs/                  # Feature specifications and design docs
├── src/
│   └── bioimage_mcp/       # Core MCP server implementation
│       ├── api/            # MCP tool handlers and services
│       ├── artifacts/      # Artifact models and storage logic
│       ├── bootstrap/      # CLI entrypoints (install, doctor, serve)
│       ├── config/         # YAML config schema
│       ├── registry/       # Tool discovery and search index
│       ├── runs/           # Workflow recording and persistence
│       ├── runtimes/       # Subprocess execution and IPC
│       └── sessions/       # Session management
├── tests/                  # Test suite
│   ├── unit/               # Isolated logic tests
│   ├── contract/           # API and schema compliance tests
│   ├── integration/        # Cross-module workflow tests
│   └── smoke/              # Live server end-to-end tests
├── tools/                  # Tool packs (external implementations)
│   ├── base/               # Standard IO and processing tools
│   ├── cellpose/           # Deep learning segmentation
│   └── tttrlib/            # Time-resolved fluorescence tools
└── pyproject.toml          # Build system and dependencies
```

## Directory Purposes

**src/bioimage_mcp/api/:**
- Purpose: The LLM-facing interface.
- Contains: `server.py` (FastMCP), `discovery.py` (search logic), `execution.py` (orchestration).
- Key files: `server.py`, `execution.py`.

**src/bioimage_mcp/artifacts/:**
- Purpose: Management of data pointers and I/O.
- Contains: Pydantic models for artifacts and the storage backend.
- Key files: `models.py`, `store.py`.

**src/bioimage_mcp/registry/:**
- Purpose: Catalog of all available tools and functions.
- Contains: SQLite indexing logic and manifest parsers.
- Key files: `index.py`, `loader.py`.

**src/bioimage_mcp/runtimes/:**
- Purpose: Isolated execution environment.
- Contains: Logic for spawning subprocesses and managing persistent workers.
- Key files: `executor.py`, `persistent.py`.

**tools/:**
- Purpose: Plugins that provide actual image analysis capabilities.
- Contains: Python modules and `manifest.yaml` files.
- Key files: `tools/base/manifest.yaml`, `tools/cellpose/manifest.yaml`.

## Key File Locations

**Entry Points:**
- `src/bioimage_mcp/cli.py`: Main CLI routing.
- `src/bioimage_mcp/api/server.py`: MCP tool definitions.

**Configuration:**
- `src/bioimage_mcp/config/schema.py`: Pydantic config model.
- `pyproject.toml`: Package metadata and dependencies.

**Core Logic:**
- `src/bioimage_mcp/api/execution.py`: Main execution orchestration.
- `src/bioimage_mcp/registry/index.py`: Tool discovery database.

**Testing:**
- `tests/contract/`: Critical for ensuring tool-server compatibility.
- `tests/integration/test_run_workflow_e2e.py`: Main end-to-end flow.

## Naming Conventions

**Files:**
- Core logic: `snake_case.py`
- Test files: `test_*.py`
- Manifests: `manifest.yaml`

**Directories:**
- Python packages: `snake_case`
- Tool packs: `tools/<pack_name>/`

**Functions/Classes:**
- Classes: `PascalCase`
- Functions/Methods: `snake_case`

## Where to Add New Code

**New Tool Function:**
1. Implementation: Add to appropriate tool pack in `tools/<pack_name>/bioimage_mcp_<pack_name>/`.
2. Declaration: Add to `tools/<pack_name>/manifest.yaml`.
3. Validation: Run `bioimage-mcp doctor` to check manifest.

**New Core Feature:**
1. Logic: `src/bioimage_mcp/<feature>/`.
2. Service: Add to `src/bioimage_mcp/api/` if exposed via MCP.
3. Configuration: Update `src/bioimage_mcp/config/schema.py` if needed.

**New Test:**
1. Unit tests: `tests/unit/<module>/`.
2. Integration tests: `tests/integration/`.

## Special Directories

**artifacts/objects/:**
- Purpose: Content-addressed or session-named artifact files.
- Generated: Yes.
- Committed: No (in `.gitignore`).

**artifacts/state/:**
- Purpose: SQLite databases for registry and sessions.
- Generated: Yes (via `bioimage-mcp install`).
- Committed: No.

**envs/:**
- Purpose: Lockfiles for tool environments.
- Generated: Yes.
- Committed: Yes (for reproducibility).

---

*Structure analysis: 2026-01-22*
