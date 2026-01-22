# External Integrations

**Analysis Date:** 2026-01-22

## APIs & External Services

**Model Context Protocol (MCP):**
- Local server implementation that provides an API for AI agents to discover and run bioimage tools.
- Communication via standard I/O (stdio).

**Tool Runtimes:**
- Integration with external tools (e.g., Cellpose, tttrlib) via isolated Conda environments.
- Execution via `subprocess` with JSON-based I/O over stdin/stdout (`src/bioimage_mcp/runtimes/executor.py`).

## Data Storage

**Databases:**
- SQLite3
  - Connection: `sqlite3.connect(db_path)`
  - Location: `[artifact_store_root]/state/bioimage_mcp.sqlite3`
  - Usage: Persistent state for tools, functions, artifacts, runs, and sessions (`src/bioimage_mcp/storage/sqlite.py`).

**File Storage:**
- Local filesystem
  - Artifact storage for scientific images, logs, and workflow records.
  - Root path defined in `artifact_store_root` configuration.

**Caching:**
- Local schema cache stored in SQLite (`schema_cache` table).

## Authentication & Identity

**Auth Provider:**
- Local-first model; no external auth provider detected.
- Permission system controls filesystem access based on allow/deny lists (`src/bioimage_mcp/api/permissions.py`).

## Monitoring & Observability

**Error Tracking:**
- Structured error logging with unique `ref_id` for artifacts.
- Errors recorded in SQLite `runs` and `session_steps` tables.

**Logs:**
- Log artifacts written to the filesystem as `.log` files and registered in the artifact store.

## CI/CD & Deployment

**Hosting:**
- Local execution (designed as a local-first MCP server).

**CI Pipeline:**
- Configured for `ruff` and `pytest`.

## Environment Configuration

**Required env vars:**
- `BIOIMAGE_MCP_FS_ALLOWLIST_READ` - Passed to worker processes.
- `BIOIMAGE_MCP_FS_ALLOWLIST_WRITE` - Passed to worker processes.

**Secrets location:**
- Not applicable (local-first, no external secrets).

## Webhooks & Callbacks

**Incoming:**
- None (Standard MCP interaction).

**Outgoing:**
- None.

---

*Integration audit: 2026-01-22*
