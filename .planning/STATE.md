# Project State: Bioimage-MCP

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-27)

**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current focus:** v0.4.0 Unified Introspection Engine

## Current Position

Phase: 13 of 14 (Dynamic Introspection Cache Reuse)
**Next Phase:** 14 (OME-Zarr Standardization)
Plan: 4 of 4 in current phase
Status: Phase complete (verified)
Last activity: 2026-01-28 — Completed 13-04-PLAN.md

Progress: █████████░ 87%

## Accumulated Context

### Decisions Made
| Phase | Decision | Rationale |
|-------|----------|-----------|
| 10 | Use 'datasets/smoke_tmp' for test CSVs | Ensure live server read access within allowed paths. |
| 10 | Map mean_table to tmean | scipy.stats lacks a bare mean function. |
| 10 | Standardize on NativeOutputRef for stats JSON | Allows flexible structured output for distribution/summary stats. |
| 10 | Automatic Float32 Promotion | Ensures precision parity for filters/transforms on uint16 inputs. |
| 10 | Stable JSON Contract | Facilitates strict comparison of statistical test outputs. |
| 11 | Audit Gap Cleanup | Address descriptions and schema types identified in v0.3.0 audit. |
| 12 | Used griffe for zero-import static inspection | Avoids heavy tool-pack dependencies in core server. |
| 12 | sha256 source fingerprinting | Enables stable tracking of callable changes across runs. |
| 12 | Deterministic JSON Schema normalization | Ensures consistent schema emission for caching and comparison. |
| 12 | TypeAdapter-based schema generation | Leverages Pydantic v2 for high-fidelity type-to-schema mapping. |
| 12 | Automated artifact omission | Prevents I/O artifacts from polluting the parameters schema. |
| 12 | Unified Discovery Orchestrator | Centralizes AST + runtime fallback logic in DiscoveryEngine. |
| 12 | Parameter-level overlays | Added support for rename/omit in overlays without tool code changes. |
| 12 | Multi-key cache invalidation | Ensures cache safety by tracking version, env, and source changes. |
| 12 | Move metadata to adjacent block | Moved tool_version and introspection_source to meta block in describe to keep params_schema pure. |
| 12 | Persistent Registry Cache | Wired API to DB-backed schema cache, eliminating separate schema_cache.json file. |
| 12 | Extended ManifestDiagnostic | Include engine_events for unified reporting of fallback, overlays, and missing docs. |
| 12 | diagnostic_level config | Allow filtering of discovery events (minimal/standard/full) in doctor output. |
| 12 | tool_environments check | Detect missing conda environments referenced by manifests with actionable remediation. |
| 12 | Gated runtime fallback | DiscoveryEngine only calls runtime fallback if AST-derived schema is incomplete (empty properties after filtering). |
| 12 | target_fn request param | Aligned DiscoveryEngine runtime describe call with tool entrypoint and API schema. |
| 12 | Enforce required/properties consistency | Stripping required fields that don't match emitted properties (e.g. omitted artifacts). |
| 12 | Omit empty 'required' key | Produces cleaner, more deterministic schema output. |
| 12 | Description merging precedence | curated > docstring > TypeAdapter > fallback. |
| 12 | In-place metadata synchronization | Updating functions table during describe enrichment ensures tools/list and tools/describe stay consistent. |
| 13 | User-home based dynamic cache | Store dynamic cache under ~/.bioimage-mcp/cache/dynamic/<tool_id> for stability across runs. |
| 13 | Lockfile hash invalidation | Use env/<env_id>.lock.yml hash as the primary invalidation key for dynamic introspection caching. |
| 13 | Reuse Unified IntrospectionCache for trackpy | Avoid bespoke cache implementations in tool packs to ensure consistent invalidation logic. |
| 13 | Robust project_root detection | Support env var and CWD-based project root detection for caching in installed tool envs. |

### Roadmap Evolution
- Phase 12 added: Core Engine + AST-First
- Phase 13 added: Dynamic Introspection Cache Reuse (incl. trackpy)
- Phase 14 added: OME-Zarr Standardization

### Blockers/Concerns Carried Forward
- trackpy schema descriptions missing (contract test failure).
- base.phasorpy schema type mismatch (contract test failure).
- contract tests need to skip non-manifest YAMLs.
- Existing failures in bootstrap/test_install.py need investigation.

### Session Continuity
Last session: 2026-01-28T23:14:42Z
Stopped at: Completed 13-04-PLAN.md
Resume file: None

## Next Steps
1. Release v0.4.0 Unified Introspection Engine.
