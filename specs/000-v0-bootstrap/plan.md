# Implementation Plan: v0.0 Bootstrap

**Branch**: `[000-v0-bootstrap]` | **Date**: 2025-12-18 | **Spec**: `specs/000-v0-bootstrap/spec.md`
**Input**: Feature specification from `specs/000-v0-bootstrap/spec.md`

## Summary

Deliver the v0.0 "minimum usable core" for Bioimage-MCP: a documented install + readiness flow, a local MCP server that supports paginated discovery (list/search/describe), an artifact store + run records (including log artifacts), and two trivial built-in functions executed via artifact references: Gaussian blur and format conversion to OME-Zarr.

**Format strategy note**: The project is pivoting to OME-TIFF as the preferred default intermediate in v0.1.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may pin differently)

**Primary Dependencies**: Official MCP Python SDK (`mcp`), `pydantic` v2 (tool manifest validation), `bioio` (+ `bioio-ome-zarr`, `bioio-ome-tiff`), `ngff-zarr` (OME-NGFF/OME-Zarr writing), `sqlite` (via stdlib)

**Storage**: Local filesystem artifact store + SQLite index (MVP)

**Execution/Isolation**:
- Per-tool conda/micromamba envs with `bioimage-mcp-*` prefix.
- Built-in "trivial" functions are still executed as a tool pack via a shim (subprocess boundary), typically in `bioimage-mcp-base`.

**Tool Definition Format**: YAML tool manifest validated by Pydantic 2; invalid manifests are excluded from discovery and surfaced via diagnostics.

**Configuration**:
- Layered YAML: global `~/.bioimage-mcp/config.yaml` + local `.bioimage-mcp/config.yaml`.
- Local overrides global; config defines artifact store root, tool manifest roots, and filesystem read/write allowlists.

**Target Platform**:
- v0.0 support scope: Linux is the only platform explicitly supported/tested.
- Design constraint (constitution): avoid hard Linux assumptions where reasonable (path handling, process invocation); document platform-specific behavior.

**Performance Goals**:
- Bounded MCP payload sizes (summary-first + pagination by default).
- Discovery operations on catalogs up to ~500 functions return within ~2s on baseline hardware.

**Safety/Observability**:
- Tool code runs with user privileges (document clearly); subprocess boundaries are for crash isolation, not sandboxing.
- Each execution produces a Run record and persists structured + human-readable logs as a `LogRef` artifact.
- Filesystem access is restricted to configured allowlisted roots for reads (inputs) and writes (artifacts/exports).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: v0.0 defines a minimal set of discovery + execution operations; changes must be versioned and justified.
- [x] Summary-first responses: list/search return summaries; full schemas are fetched only via describe.
- [x] Tool execution isolated: functions execute in per-tool envs via subprocess boundary; heavy deps stay out of core env.
- [x] Artifact references only: inputs/outputs are typed, file-backed references; no large/binary payloads in MCP.
- [x] Reproducibility: runs record provenance (inputs, params, tool identity/version, timestamps, checksums); v0.0 replay is planned at least for single-step runs.
- [x] Safety + debuggability: per-run logs persisted as artifacts; access policies explicit; core execution and schema validation have tests.
- [x] TDD (red-green-refactor): tests written before implementation per Principle VI.

(Reference: `.specify/memory/constitution.md`)

## Gate Evaluation

Status: **PASS**

Rationale:
- The plan does not introduce non-paginated discovery or schema-inlined discovery responses.
- The plan keeps execution isolated and artifact-based, with explicit provenance and logs.
- Linux-only support in v0.0 is treated as "supported/tested" scope, while implementation avoids unnecessary platform coupling.

## Project Structure

### Documentation (this feature)

```text
specs/000-v0-bootstrap/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by this workflow)
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── api/                 # MCP surface (list/search/describe/execute/run/artifact)
├── artifacts/           # Artifact store + checksums + metadata extraction
├── bootstrap/           # install/doctor/configure CLI + env manager
├── config/              # layered YAML config schema + loader
├── registry/            # tool manifest discovery, validation, SQLite index
├── runtimes/            # subprocess execution boundary + shims
├── runs/                # run records, status lifecycle, log emission
└── storage/             # SQLite storage bootstrap and utilities

envs/                    # conda env YAML + lockfiles (base + tool packs)
tools/                   # built-in tool manifests + shim entrypoints

tests/
├── unit/
└── integration/
```

**Structure Decision**: Single Python package (`src/bioimage_mcp/`) plus `envs/` and `tools/` as data-plane inputs, matching the architecture document's suggested layout.

**MicroscopyLM Modules to Copy/Adapt**:
- `miclm.tools.registry` → `src/bioimage_mcp/registry/` (manifest discovery + validation patterns)
- `miclm.env.manager` → `src/bioimage_mcp/bootstrap/env_manager.py` (micromamba/conda detection)
- `miclm.executors.python_subproc` → `src/bioimage_mcp/runtimes/executor.py` (subprocess isolation)
- `miclm.config` → `src/bioimage_mcp/config/` (layered YAML patterns)

## Complexity Tracking

> No constitution violations are required for v0.0; complexity table intentionally left empty.

## Phase 0: Outline & Research (documentation-only)

Outputs:
- `specs/000-v0-bootstrap/research.md`

Research goals:
- Confirm the minimal v0.0 MCP surface and pagination patterns.
- Define artifact reference schema and run record/provenance shape.
- Confirm manifest schema approach (YAML + Pydantic 2) and invalid-manifest behavior.
- Decide how built-in functions are packaged/executed (tool pack + shim + base env).

## Phase 1: Design & Contracts (documentation-only)

Outputs:
- `specs/000-v0-bootstrap/data-model.md`
- `specs/000-v0-bootstrap/contracts/openapi.yaml`
- `specs/000-v0-bootstrap/quickstart.md`

Design goals:
- Identify core entities (ToolManifest/Tool/Function/ArtifactRef/Run/Config) with fields, relationships, and validation.
- Specify request/response contracts for discovery, execution, run inspection, and artifact export.
- Provide a quickstart that proves the end-to-end user stories without requiring protocol payloads to include binaries.

## Constitution Check (Post-Design)

Status: **PASS**

- Stable MCP surface: contracts define paginated summary-first list/search; full schemas only via describe.
- Summary-first responses: enforced in contract and quickstart usage pattern.
- Tool execution isolated: design keeps tool pack shim in per-tool env and runs built-ins via same boundary.
- Artifact references only: contracts and data model use ArtifactRef everywhere; no binary payload endpoints.
- Reproducibility: Run includes provenance, checksums, and run record lifecycle; OME-Zarr outputs are file-backed (v0.1 pivots to OME-TIFF as the preferred default).
- Safety + debuggability: allowlists/denylists in Config; run log artifacts are first-class; tests planned for core paths.
- TDD: All implementation phases follow red-green-refactor per constitution Principle VI.

## Phase 2: Implementation Planning (stop after planning)

Planned implementation work (high-level):
1. Create package skeleton (`src/bioimage_mcp/`) and CLI entrypoints (`install`, `doctor`, `configure`, `serve`).
2. Implement layered config loader and schema; wire filesystem allowlists into artifact and export operations.
3. Implement artifact store (filesystem layout + checksums + metadata) and SQLite index.
4. Implement YAML manifest schema (Pydantic 2) + registry loader with diagnostics and pagination-ready indexes.
5. Implement MCP server surface for list/search/describe + execute + run/artifact operations.
6. Implement runtime executor (subprocess-in-env boundary) and a built-in tool pack with:
   - Gaussian blur
   - Convert-to-OME-Zarr
7. Add tests for manifest validation, pagination, artifact ref encoding, and run/log persistence.
8. Document limitations (Linux-tested; subprocess isolation not sandboxing; local-first file:// artifacts).
