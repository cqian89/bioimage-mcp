# Implementation Plan: Base Tool Schema Expansion

**Branch**: `002-base-tool-schema` | **Date**: 2025-12-19 | **Spec**: `specs/002-base-tool-schema/spec.md`
**Input**: Feature specification from `specs/002-base-tool-schema/spec.md`

## Summary

Expand the “base” tool surface so agentic IDE/CLI clients can reliably discover, inspect, and execute common image I/O + transforms + pre-processing functions without context bloat. Detailed parameter schemas are generated on-demand via `meta.describe` inside the owning tool environment and cached in a local JSON file to avoid repeated enrichment work. Add at least one automated, real end-to-end (“live”) workflow validation using `datasets/FLUTE_FLIM_data_tif`, with clear skip behavior when runtime prerequisites (tool envs) are unavailable.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic`, `bioio`, `ngff-zarr`, `numpy`, `scipy`, **`scikit-image`**  
**Storage**: Local filesystem artifact store; SQLite index for artifacts/runs; **local JSON file for enriched schema cache** (per FR-003)  
**Testing**: `pytest` (unit + contract + integration); add a live end-to-end workflow test that runs real tool subprocesses and real image I/O  
**Target Platform**: Local/on-prem; Linux-first (macOS/Windows best-effort)  
**Project Type**: Python service + CLI + tool packs executed via subprocess in isolated envs  
**Performance Goals**: Summary-first discovery payloads; on-demand schema enrichment; bounded tool output sizes; isolated per-run output directories  
**Constraints**:
- MCP discovery MUST remain “summary-first” (no schema blobs in list/search responses)
- Tool calls/workflows MUST pass artifacts by reference (file-backed), not inline arrays/binaries
- Schema enrichment MUST execute inside the owning tool env (base vs cellpose)
- Live workflow validation MUST be skipped (not failed) when prerequisites are missing, with an actionable reason

**Key Existing Components (current repo)**:
- Tool manifests + validation: `src/bioimage_mcp/registry/manifest_schema.py`
- Introspection utilities: `src/bioimage_mcp/runtimes/introspect.py`
- Discovery API (summary-first): `src/bioimage_mcp/api/discovery.py`
- Registry index + (currently unused) schema_cache helpers: `src/bioimage_mcp/registry/index.py`
- Tool packs: `tools/builtin/` (base env, small utilities), `tools/base/` (planned base toolkit), and `tools/cellpose/` (specialized env)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: changes are additive; discovery remains paginated; no breaking shape changes without version/migration note.
- [x] Summary-first responses: `list_tools` / `search_functions` stay schema-free; only `describe_function(fn_id)` returns detailed schema.
- [x] Tool execution isolated: schema enrichment uses `meta.describe` in the owning tool env (`bioimage-mcp-base` vs `bioimage-mcp-cellpose`).
- [x] Artifact references only: I/O continues to use typed, file-backed artifact refs (no large payloads in MCP).
- [x] Reproducibility: workflow runs record inputs/params/tool versions; schema cache is version-keyed and invalidates on tool pack version changes.
- [x] Safety + debuggability + TDD: errors are clear; logs are persisted as artifacts; tests written first for new behaviors; live test uses explicit skip when prerequisites missing.

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/002-base-tool-schema/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks) - NOT created by this workflow
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── api/                 # MCP-facing discovery/execution services
├── artifacts/           # Artifact refs, metadata, export
├── config/              # Config loading + fs policy
├── registry/            # Manifest loading, validation, search/index
├── runtimes/            # Tool subprocess execution + introspection helpers
├── storage/             # SQLite schema + persistence
├── __main__.py          # CLI entry
└── cli.py

tools/
├── base/                # Planned base toolkit (bioimage-mcp-base)
├── builtin/             # Base env utilities (bioimage-mcp-base)
└── cellpose/            # Specialized tool pack (bioimage-mcp-cellpose)

tests/
├── contract/            # Contract tests for stable interfaces
├── integration/         # E2E-ish tests (some currently mocked)
└── unit/

datasets/FLUTE_FLIM_data_tif/  # Current validation dataset (per FR-012)
```

**Structure Decision**: Single Python project with tool packs under `tools/` and core server under `src/bioimage_mcp/`.

## Phase 0: Outline & Research (output: `research.md`)

Research focuses on:
- How to wire server-side `describe_function(fn_id)` to on-demand `meta.describe` execution and caching.
- How to curate a base function set (≥20 functions) across I/O, transforms, and pre-processing using `scikit-image`.
- How to implement a truly live workflow validation test (no mocked tool execution) with clear skip reasons.

## Phase 1: Design & Contracts (outputs: `data-model.md`, `contracts/*`, `quickstart.md`)

Design outputs cover:
- Data model for schema cache entries, tool packs/functions, workflow run provenance, and artifact refs.
- Contracts for the on-demand schema enrichment behavior (`describe_function` + `meta.describe`) and tool protocol payload shapes.
- Quickstart for adding new base functions and ensuring schemas remain reliable.

## Phase 2: Implementation Plan (planned; ends this workflow)

Implementation is organized to satisfy TDD and minimize MCP surface changes:
- Implement `tools.base` and grow it to ≥20 curated functions (I/O, transforms, pre-processing), each with:
  - a stable `fn_id`, summary metadata, and artifact I/O contracts in its manifest
  - a `meta.describe` path that returns complete parameter schemas with curated descriptions
- Update server-side `describe_function(fn_id)` to:
  - return cached enriched schema when available
  - otherwise execute `meta.describe` inside the owning tool env and persist result in a local JSON cache (`${artifact_store_root}/state/schema_cache.json`) keyed by tool_id + tool_version + fn_id
  - invalidate cache automatically on tool pack version change
- Add automated tests:
  - contract tests for summary-first discovery and describe-on-demand enrichment
  - a live end-to-end workflow validation that runs real tool subprocesses and real image I/O, and skips with an actionable reason when prerequisites are missing
- Add/refresh documentation:
  - base function catalog document (FR-007)
  - quickstart updates for adding new base functions

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) |  |  |
