# Implementation Plan: MCP Interface Redesign (Clean Surface)

**Branch**: `016-mcp-interface-redesign` | **Date**: 2026-01-05 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/016-mcp-interface-redesign/spec.md`  
**Proposal**: [Proposal_MCP_Interface_Redesign.md](../../docs/plan/Proposal_MCP_Interface_Redesign.md)

## Summary

Redesign BioImage-MCP's MCP tool surface from 13 inconsistent tools to 8 clean, consistent tools with unified naming, proper separation of artifact ports from params, structured error handling, and workflow replay support. This is a breaking change aligned with the Early Development Policy (Pre-1.0).

### Primary Requirements (from spec)
1. **LLM-friendly discovery**: `list`, `describe`, `search` with child counts and I/O summaries
2. **Unified execution**: Single `run` tool replacing `run_function`/`run_workflow`
3. **Session replay**: `session_export` and `session_replay` for reproducibility on new data
4. **Structured errors**: JSON Pointer paths with actionable hints

### Technical Approach
- Define new Pydantic models for the 8 tools in `src/bioimage_mcp/api/schemas.py`
- Implement handlers in `src/bioimage_mcp/api/server.py` (FastMCP)
- Remove deprecated tools (`describe_tool`, `activate_functions`, `deactivate_functions`, `run_workflow`, `export_artifact`, `resume_session`)
- Fix schema generation to separate artifact ports from params_schema
- Add contract tests for all 8 tools
- Ship migration notes + semver bump rationale for the breaking MCP surface change

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `fastmcp`  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Testing**: `pytest`, `pytest-asyncio` (add contract tests for all 8 tools)  
**Target Platform**: Local/on-prem; Linux-first (macOS/Windows best-effort)  
**Project Type**: Python MCP server + CLI  
**Performance Goals**: Bounded MCP payload sizes; paginated discovery; child counts for navigation  
**Constraints**: No large binary payloads in MCP; artifact references only; single identifier per catalog node  
**Scale/Scope**: Tool catalog can grow; discovery remains paginated with child counts

### Current State → Target State

| Current (13 tools) | Target (8 tools) | Change Type |
|-------------------|------------------|-------------|
| `list_tools` | `list` | Rename + add child counts |
| `describe_function` | `describe` | Rename + extend to all node types |
| `describe_tool` | _(removed)_ | Remove (broken/redundant) |
| `search_functions` | `search` | Rename + add I/O summaries |
| `run_function` | `run` | Rename + consolidate |
| `run_workflow` | _(removed)_ | Remove (use `run` + sessions) |
| `get_run_status` | `status` | Rename |
| `get_artifact` | `artifact_info` | Rename + add text preview |
| `export_artifact` | _(removed)_ | Remove (artifacts accessible via URI in `artifact_info`) |
| `export_session` | `session_export` | Rename + add external_inputs tracking |
| _(new)_ | `session_replay` | Add workflow replay on new data |
| `activate_functions` | _(removed)_ | Remove (complexity without benefit) |
| `deactivate_functions` | _(removed)_ | Remove (complexity without benefit) |
| `resume_session` | _(merged)_ | Merge into session handling |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Stable MCP surface**: Reduces from 13 to 8 tools. All tools align with Constitution Section I naming. Breaking change justified by Early Development Policy (VII).
- [x] **Versioning + migration notes**: Plan/tasks include semver bump rationale and migration notes for breaking MCP surface changes.
- [x] **Summary-first responses**: `list` includes child counts; full schemas via `describe(id)` only.
- [x] **Tool execution isolated**: No changes to tool isolation; functions still run in subprocess environments.
- [x] **Artifact references only**: All I/O via typed refs (BioImageRef, etc.) with bounded metadata (dims, dtype, shape, size_bytes). No binary payloads.
- [x] **Reproducibility**: `session_export` captures `external_inputs` vs step-derived. `session_replay` enables replay on new data. Provenance recorded.
- [x] **Safety + debuggability**: Structured error model with JSON Pointer paths and hints. Contract tests for all 8 tools.
- [x] **TDD**: All tool implementations require failing tests first (per Constitution VI).

**Violations**: None. This feature implements Constitution I directly.

## Project Structure

### Documentation (this feature)

```text
specs/016-mcp-interface-redesign/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI schemas)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/bioimage_mcp/
├── api/
│   ├── server.py            # FastMCP tool registration (8 tools)
│   ├── schemas.py           # Pydantic models for API I/O
│   ├── discovery.py         # list, describe, search handlers
│   ├── execution.py         # run, status handlers
│   ├── artifacts.py         # artifact_info handler
│   └── sessions.py          # session_export, session_replay handlers (NEW)
├── artifacts/
│   └── models.py            # ArtifactRef, checksums, metadata
├── registry/
│   └── manifest_schema.py   # ToolManifest, Function definitions
└── sessions/                # Session state and workflow records (NEW or expand)

tests/
├── contract/
│   ├── test_list.py         # Contract tests for list tool
│   ├── test_describe.py     # Contract tests for describe tool
│   ├── test_search.py       # Contract tests for search tool
│   ├── test_run.py          # Contract tests for run tool
│   ├── test_status.py       # Contract tests for status tool
│   ├── test_artifact_info.py
│   ├── test_session_export.py
│   └── test_session_replay.py
├── integration/
│   └── test_end_to_end.py   # Full discover→describe→run→export→replay flows
└── unit/
    └── api/                 # Unit tests for individual handlers
```

**Structure Decision**: Single Python project with `src/` layout. Tests split by category (contract/integration/unit) per existing project conventions.

## Complexity Tracking

No violations to justify. This feature reduces complexity (13→8 tools) and aligns with Constitution.
