# Implementation Plan: 001-cellpose-pipeline (v0.1 First Real Pipeline)

**Branch**: `001-cellpose-pipeline` | **Date**: 2025-12-18 | **Spec**: `/mnt/c/Users/meqia/bioimage-mcp/specs/001-cellpose-pipeline/spec.md`
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.codex/prompts/speckit.plan.md` for the execution workflow.

## Summary

Deliver an end-to-end, linear, single-image Cellpose segmentation workflow that takes an input `BioImageRef` and produces (1) an instance `LabelImageRef`, (2) a run `LogRef`, and (3) a workflow record artifact (JSON) suitable for later replay. All tool I/O is file-backed by artifact references; workflow steps are compatibility-validated before execution; filesystem access is enforced by allowlists.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp`), `pydantic` v2, `bioio` (+ `bioio-ome-tiff`)  
**Tool Runtime**: Separate local subprocess for Cellpose tool pack in its own dedicated conda/micromamba environment (`bioimage-mcp-*`)  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Artifact Formats**: Default **OME-TIFF** for interoperability; OME-Zarr deferred in v0.1 (attempting OME-Zarr should fail fast with a clear error message; explicit v0.1 exception to the constitution’s default preference).  
**Workflow Records**: JSON document stored as file-backed artifact reference (type: `NativeOutputRef`, format: `workflow-record-json`). Note: `NativeOutputRef` is a tool-agnostic type; `format` values are open and tool-dependent (see `research.md` Section 10).  
**Testing**: `pytest`; include contract tests for protocol/payload shape and unit tests for allowlists/artifact schema.  
**Target Platform**: Local/on-prem; core server supports Linux/macOS/Windows; tool environment installs are best-effort but MUST document platform-specific constraints and workarounds where needed.  
**Performance Goals**: Bounded MCP payload sizes (summary-first), avoid pixel arrays in messages, stable paginated discovery, subprocess isolation for heavy deps.  
**Constraints**: Artifact references only; enforce filesystem allowlists for all reads/writes; tool subprocess boundaries are for crash isolation, not a security sandbox.

**Project Type**: Python service + CLI (plus per-tool shims/envs)

**Scale/Scope**: Linear single-image workflow in v0.1; no batch scheduling/parallel execution.

### Needs Clarification (to resolve in Phase 0)

- Canonical artifact reference schema: `src/bioimage_mcp/artifacts/models.py` → `ArtifactRef` (plus `ArtifactChecksum`).
- Artifact store on-disk layout: `artifact_store_root/objects/<ref_id>` for immutable stored artifacts, with transient tool work under `artifact_store_root/work/`.
- Filesystem allowlists mechanism: `src/bioimage_mcp/config/fs_policy.py` → `assert_path_allowed(op, path, config)` enforced in `ArtifactStore.import_*()` and `ArtifactStore.export()`.
- Tool registry/manifest loading: `src/bioimage_mcp/registry/loader.py` loads YAML manifests from `config.tool_manifest_roots` and `src/bioimage_mcp/api/execution.py` resolves `fn_id` to an entrypoint.
- Cellpose env packaging: store an env definition under `envs/` and reference it by `env_id` from the tool manifest; tool runs as a subprocess (see `src/bioimage_mcp/runtimes/executor.py`).
- Lockfile strategy: generate per-tool lockfiles via conda-lock under `envs/` and record lockfile hashes in workflow provenance for reproducibility.
- **Dynamic parameter schemas**: Tool packs expose `meta.describe` for runtime schema introspection (see `research.md` Section 11 and `meta-describe-protocol.md`). `list_tools` remains summary-only; full `params_schema` is fetched on-demand via `describe_function` (and cached server-side).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: new capability is additive via tool manifest + `fn_id` execution; discovery remains paginated (`DiscoveryService.list_tools` / cursor-based).
- [x] Summary-first responses: discovery returns summaries; full function/tool details (including dynamic `params_schema` via `meta.describe`) are fetched on demand via `describe_function` / `describe_tool`.
- [x] Tool execution isolated: Cellpose runs as a subprocess in its own `bioimage-mcp-*` environment via manifest `env_id`.
- [x] Artifact references only: `ArtifactRef` is file-backed; tools return paths and core imports artifacts, never embedding pixel arrays.
- [x] Reproducibility: workflow spec is persisted in `runs`; v0.1 adds a workflow record artifact (JSON) for replay (see `specs/001-cellpose-pipeline/contracts/openapi.yaml`).
- [x] Safety + debuggability: filesystem allowlists enforced via `assert_path_allowed`; every run writes a `LogRef`; Phase 2 will add automated tests per TDD.

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
```text
src/
tests/
tools/
envs/
datasets/
specs/
```

**Structure Decision**: Single Python project under `src/` with tests under `tests/`. Tool packs live under `tools/` with isolated env definitions under `envs/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
