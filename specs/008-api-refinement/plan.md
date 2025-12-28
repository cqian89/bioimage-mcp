# Implementation Plan: API Refinement & Permission System

**Branch**: `008-api-refinement` | **Date**: 2025-12-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-api-refinement/spec.md`

## Summary

This plan addresses several critical improvements to the Bioimage-MCP API and security model:

1. **Dynamic Permissions (P0)**: Implementing `inherit` mode to leverage MCP Roots for zero-config file access, plus Elicitation-based overwrite protection.
2. **Canonical Naming Scheme (P0)**: Migrating to `env.package.module.function` (e.g., `base.skimage.filters.gaussian`) and consolidating `builtin` into `base`.
3. **Hierarchical Discovery (P1)**: Refining `list_tools` to support tree navigation (envs -> packages -> modules -> functions) with batch support.
4. **Enhanced Search (P1)**: Implementing multi-keyword search with weighted ranking (Name=3, Desc=2, Tags=1).
5. **Batch Describe (P2)**: Adding `describe_function(fn_ids=[...])` to reduce round-trips for agents.
6. **API Consolidation (P2)**: Renaming `call_tool` to `run_function` (canonical) and adding workflow guidance hints.

## Technical Context

**Language/Version**: Python 3.13 (core server); Python 3.13 (base tool env)  
**Primary Dependencies**: MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `numpy`, `pytest`, `pyyaml`  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Testing**: `pytest` (contract, integration, unit)  
**Target Platform**: Linux-first (macOS/Windows best-effort)  
**Constraints**: Stable MCP surface; subprocess isolation; artifact references only; TDD required  
**Scale/Scope**: Refinement of 4 existing MCP tools + 1 new canonical tool (`run_function`) + new permission service.

### Key Technical Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Canonical Naming | `env.package.module.function` | Standardizes discovery; prevents collisions; maps clearly to Python hierarchy. |
| Tool Consolidation | Remove `builtin`, move to `base` | Eliminates cross-environment I/O errors and dependency conflicts. |
| Hierarchical Logic | Dot-notated `path` parameter | Intuitive navigation; allows agents to browse specific sub-trees efficiently. |
| Search Ranking | Multi-keyword weighted score | Improves relevance; keyword count is primary sort, total weight is secondary. |
| Permission Mode | Default to `inherit` | Zero-config "it just works" experience for users within their agent workspace. |
| Overwrite Policy | MCP Elicitation (`ask`) | Best-in-class interactive safety; fall back to `deny` for non-supporting clients. |

### Research Questions (Resolved)

1. **Alias handling**: Legacy names (e.g., `base.gaussian`) are supported as deprecated aliases in the registry but hidden from `list_tools`.
2. **Environment mapping**: `env` in the fn_id corresponds to the short name (`base`, `cellpose`), not the full `env_id` (`bioimage-mcp-base`).
3. **Permission logging**: Inherited roots and every allow/deny decision are logged to `server.log` for auditability.
4. **Hierarchy depth**: Hierarchy is dynamic based on registered functions; can be any depth, but typically 3-4 levels.

## Constitution Check

- [x] **Stable MCP Surface**: New parameters are additive; pagination is preserved. `run_function` is an alias for `call_tool`.
- [x] **Summary-first responses**: `list_tools` and `search_functions` return summaries; full schemas stay in `describe_function`.
- [x] **Tool execution isolated**: Consolidation reduces environment sprawl but maintains subprocess boundaries.
- [x] **Artifact references only**: No changes to the artifact model; all I/O via typed references.
- [x] **Reproducibility**: Permission decisions and inherited roots recorded in logs; tool params recorded in run records.
- [x] **Safety + debuggability**: `inherit` mode + Elicitation improves safety. All decisions are auditable via logs.
- [x] **TDD**: Contract tests for refined discovery and permissions will be written before implementation.

## Project Structure

### Documentation

```text
specs/008-api-refinement/
├── plan.md              # This file
├── research.md          # Phase 0 output - technical research findings
├── data-model.md        # Phase 1 output - entity models
├── quickstart.md        # Phase 1 output - validation commands
└── contracts/           
    └── openapi.yaml     # Refined tool schemas & permission entities
```

### Source Code

```text
src/bioimage_mcp/
├── api/
│   ├── server.py            # MCP tool registrations and high-level routing
│   ├── discovery.py         # Refined list_tools, search_functions, describe_function
│   ├── execution.py         # Add run_function logic, handle call_tool deprecation
│   └── permissions.py       # NEW: Root inheritance and decision logic
├── registry/
│   ├── index.py             # Hierarchical index support, alias mapping
│   └── search.py            # Weighted multi-keyword ranking
├── config/
│   ├── loader.py            # Auto-discovers tool manifests under tools/
│   ├── schema.py            # permissions, fs_allowlist_*, agent_guidance settings
│   └── fs_policy.py         # Modified to use dynamic permission service
tools/
├── base/
│   ├── manifest.yaml        # Updated naming, aliases, consolidated builtins
└── builtin/                 # REMOVED (migration notes in research.md)
```

## Migration & Compatibility

1. **API Mapping**: `call_tool` is accepted as a deprecated alias for `run_function`. Clients are encouraged to migrate. Deprecation warnings are logged but not returned in the JSON response.
2. **Discovery**: `list_tools` response remains under the `tools` key for MCP compliance, but the items now represent hierarchical nodes (envs/packages/modules) rather than a flat list of all functions.
3. **Environment Consolidation**: `tools/builtin/` is removed; all its functions (like OME-Zarr conversion) are moved to the `base` environment to reduce I/O overhead.

## Complexity Tracking

No constitution violations identified. The transition to `inherit` mode is explicitly supported by the latest constitution version (v0.5.0).

## Constitution Check (Post-Design Re-evaluation)

*Re-check after Phase 1 design to confirm no new violations.*

All principles remain satisfied:
1. **Stable surface**: `list_tools(path=...)` is a clean extension of the existing tool.
2. **Isolated execution**: Single `base` environment improves reliability of image processing pipelines.
3. **Artifacts**: No array embedding; metadata remains minimal in listings.
4. **Safety**: Elicitation provides a robust mechanism for "human-in-the-loop" safety for destructive operations.

**No new violations introduced during design phase.**
