# Implementation Plan: Artifact Store Retention & Quota Management

**Branch**: `019-artifact-management` | **Date**: 2026-01-09 | **Spec**: `specs/019-artifact-management/spec.md`

## Summary
Implement artifact store retention and quota management for bioimage-mcp. This feature adds session-level lifecycle tracking, configurable storage quotas, CLI management commands, and automated cleanup of expired sessions and orphaned files to prevent unbounded disk growth.

## Technical Context
- **Language/Version**: Python 3.13 (core server)
- **Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic>=2.0`, `sqlite3`, `argparse`
- **Storage**: Local filesystem artifact store + SQLite index
- **Testing**: `pytest` with unit, contract, and integration tests
- **Target Platform**: Linux-first, macOS/Windows supported
- **Project Type**: Python service + CLI
- **Performance Goals**: Storage status in <1s, quota checks with no perceptible delay, prune of 100 sessions in <30s
- **Constraints**: No new MCP tools (CLI only), backwards-compatible schema migration, quota enforcement integrated in core server (`src/bioimage_mcp/api/execution.py`) with structured errors.

## Constitution Check (All Passing)

### I. Stable MCP Surface
- [x] **PASS**: No new MCP tools added. Management operations are CLI-only.
- No changes to the 8-tool surface (list, describe, search, run, status, artifact_info, session_export, session_replay)

### II. Isolated Tool Execution  
- [x] **PASS**: No changes to tool isolation. Storage quota enforcement is in core server (`ExecutionService.run_workflow` in `src/bioimage_mcp/api/execution.py`), not tool environments, and quota failures return structured errors (`code`/`message`/`details`).

### III. Artifact References Only
- [x] **PASS**: No changes to artifact reference model. This feature manages physical lifecycle and metadata, not I/O patterns.

### IV. Reproducibility & Provenance
- [x] **PASS**: Pinned sessions are protected to ensure important reproducible workflows remain available. Pruning of old sessions is a documented tradeoff for system stability.

### V. Safety & Observability
- [x] **PASS**: 
  - Destructive operations require confirmation or --force flag
  - --dry-run available for previewing changes
  - All deletions logged with session_id and bytes reclaimed
  - Tests required before implementation (TDD)

### VI. Test-Driven Development
- [x] **PASS**: All implementation work will follow TDD. Tests for session expiration, quota calculation, cleanup, and orphan detection will be written first.

### VII. Early Development Policy
- [x] **PASS**: Pre-1.0 allows schema changes. Migration strategy documented in data-model.md.

## Project Structure

### Documentation (this feature)
```text
specs/019-artifact-management/
├── spec.md              # Feature specification (input)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: Research findings and decisions
├── data-model.md        # Phase 1: Entity and schema definitions
├── quickstart.md        # Phase 1: User-facing usage guide
├── contracts/           # Phase 1: API contracts
│   ├── cli.md           # CLI command specifications
│   └── storage-service.md # Internal Python API contract
└── tasks.md             # Phase 2 output (to be created by /speckit.tasks)
```

### Source Code (implementation targets)
```text
src/bioimage_mcp/
├── storage/
│   ├── sqlite.py           # Schema migration (add columns)
│   └── service.py          # NEW: StorageService implementation
├── config/
│   └── schema.py           # Add StorageSettings model
├── sessions/
│   ├── models.py           # Extend Session model
│   └── store.py            # Add lifecycle methods
├── cli.py                  # Add storage subcommand

tests/
├── unit/
│   └── storage/
│       ├── test_service.py     # StorageService unit tests
│       └── test_quota.py       # Quota calculation tests
├── contract/
│   └── test_storage_schema.py  # Schema migration tests
└── integration/
    └── test_storage_cli.py     # CLI integration tests
```

**Structure Decision**: Single-project Python service with CLI extension. No new packages or major restructuring required.

## Complexity Tracking
No constitution violations requiring justification.
