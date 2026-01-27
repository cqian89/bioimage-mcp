---
phase: 12-core-engine-ast-first
verified: 2026-01-27T15:09:00Z
status: passed
score: 11/11 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 7/11
  gaps_closed:
    - "Dynamic function discovery is AST-first and does not import tool code in the core server."
    - "Schema cache persists across server restarts and is invalidated on tool_version/env lock/source hash changes."
    - "meta.describe-derived params_schema reflects type hints + docstrings, with correct required fields."
    - "tools/list and tools/describe reflect a single unified introspection source (consistent schema + metadata)."
  gaps_remaining: []
  regressions: []
---

# Phase 12: Core Engine + AST-First Verification Report

**Phase Goal:** Unified introspection engine that is AST-first with isolated runtime fallback, deterministic schema emission, and consistent metadata across list/describe.
**Verified:** 2026-01-27T15:09:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Core server can parse tool-pack Python modules without importing them. | ✓ VERIFIED | `inspect_module` uses griffe loader; static inspector avoids imports. |
| 2 | Static inspection output (signature/docstrings/fingerprint) is deterministic across runs. | ✓ VERIFIED | `callable_fingerprint` + `normalize_json_schema` provide stable ordering. |
| 3 | meta.describe-derived params_schema reflects type hints + docstrings, with correct required fields. | ✓ VERIFIED | `introspect_python_api` preserves required list from signature and merges TypeAdapter schema while keeping curated/docstring descriptions. |
| 4 | Artifact ports are excluded from params_schema emission. | ✓ VERIFIED | `introspect_python_api` uses `is_artifact_param`; API describe filters artifact ports. |
| 5 | Schema output is deterministic across runs. | ✓ VERIFIED | Schema properties and required lists are sorted in `introspect_python_api`. |
| 6 | Dynamic function discovery is AST-first and does not import tool code in the core server. | ✓ VERIFIED | `DiscoveryEngine` only invokes runtime fallback when AST schema is incomplete. |
| 7 | If AST inspection is incomplete or mismatched, the engine falls back to isolated runtime meta.describe. | ✓ VERIFIED | `_process_callable` calls `execute_tool` only when AST properties missing. |
| 8 | Functions skipped due to introspection failure do not appear in list/describe. | ✓ VERIFIED | `_process_callable` returns None when AST empty and runtime fails; skip event recorded. |
| 9 | Schema cache persists across server restarts and is invalidated on tool_version/env lock/source hash changes. | ✓ VERIFIED | `describe_function` computes env/source hashes and passes them to cache get/upsert. |
| 10 | callable_fingerprint is recorded and available for cache/diagnostics. | ✓ VERIFIED | Schema cache stores callable_fingerprint; describe meta returns it. |
| 11 | tools/list and tools/describe reflect a single unified introspection source (consistent schema + metadata). | ✓ VERIFIED | `describe_function` syncs updated schema/introspection_source back to functions table used by list. |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/bioimage_mcp/registry/static/inspector.py` | AST-first module inspection | ✓ VERIFIED | Uses `griffe.GriffeLoader`. |
| `src/bioimage_mcp/registry/static/fingerprint.py` | Stable callable_fingerprint | ✓ VERIFIED | SHA256 implementation with tests. |
| `src/bioimage_mcp/registry/static/schema_normalize.py` | Deterministic schema normalization | ✓ VERIFIED | Key sorting + required ordering. |
| `src/bioimage_mcp/runtimes/introspect.py` | TypeAdapter schema emission + docstrings + artifact omission | ✓ VERIFIED | Required list preserved; docstring descriptions retained; deterministic sorting applied. |
| `src/bioimage_mcp/registry/engine.py` | Unified DiscoveryEngine with AST-first + runtime fallback | ✓ VERIFIED | Runtime fallback only when AST schema incomplete. |
| `src/bioimage_mcp/registry/loader.py` | Loader uses DiscoveryEngine | ✓ VERIFIED | `DiscoveryEngine` invoked in `load_manifest_file`. |
| `src/bioimage_mcp/registry/index.py` | Schema cache with invalidation keys | ✓ VERIFIED | Cache getters validate env/source hashes when provided. |
| `src/bioimage_mcp/storage/sqlite.py` | DB schema includes cache keys | ✓ VERIFIED | `schema_cache` includes env_lock_hash/callable_fingerprint/source_hash columns. |
| `src/bioimage_mcp/api/discovery.py` | Describe uses unified engine + DB cache + meta block | ✓ VERIFIED | Cache lookups include env/source hashes; enriched schema synced to functions table. |
| `src/bioimage_mcp/bootstrap/doctor.py` | Readiness diagnostics | ✓ VERIFIED | Uses `run_all_checks` and emits registry summary + remediation. |
| `src/bioimage_mcp/registry/diagnostics.py` | Engine diagnostics events | ✓ VERIFIED | EngineEvent types include fallback, overlays, missing docs, skipped. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `registry/static/inspector.py` | `griffe` | `GriffeLoader.load` | ✓ WIRED | `loader = griffe.GriffeLoader(...); loader.load(...)`. |
| `registry/loader.py` | `registry/engine.py` | `DiscoveryEngine(...)` | ✓ WIRED | Loader instantiates and calls `engine.discover`. |
| `registry/engine.py` | `execute_tool` | runtime fallback | ✓ WIRED | Fallback only on AST-incomplete schema. |
| `api/discovery.py` | `registry/index.py` | cache get/upsert | ✓ WIRED | Cache lookups/upserts include env_lock_hash/source_hash. |
| `api/discovery.py` | `registry/index.py` | functions sync | ✓ WIRED | Updated schema/introspection_source written back to functions table. |
| `bootstrap/doctor.py` | `bootstrap/checks.py` | `run_all_checks()` | ✓ WIRED | `run_checks` delegates to `run_all_checks`. |

### Requirements Coverage

No requirements mapping file found (`.planning/REQUIREMENTS.md`). Requirements coverage not assessed.

### Anti-Patterns Found

No phase-specific blocker anti-patterns detected in inspected files.

### Human Verification Required

None identified (structural verification performed).

### Gaps Summary

No gaps found. AST-first discovery is isolated with conditional runtime fallback, schema cache invalidation uses env/source hashes, runtime schema emission preserves required fields and descriptions, and list/describe metadata is synchronized via functions table updates.

---

_Verified: 2026-01-27T15:09:00Z_
_Verifier: Claude (gsd-verifier)_
