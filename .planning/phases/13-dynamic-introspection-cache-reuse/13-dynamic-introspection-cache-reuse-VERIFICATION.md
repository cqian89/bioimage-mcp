---
phase: 13-dynamic-introspection-cache-reuse
verified: 2026-01-29T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 8/8
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 13: Dynamic Introspection Cache Reuse Verification Report

**Phase Goal:** Reuse dynamic introspection results across meta.list calls via a lockfile-gated cache stored under ~/.bioimage-mcp/cache/dynamic/, including trackpy.
**Verified:** 2026-01-29T00:00:00Z
**Status:** passed
**Re-verification:** Yes — prior verification existed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Calling tools.base meta.list twice reuses cached dynamic introspection when the env lockfile hash is unchanged. | ✓ VERIFIED | `tools/base/bioimage_mcp_base/entrypoint.py` passes `IntrospectionCache` + `project_root` to `discover_functions`; cache hit/miss behavior covered in `tests/unit/tools/test_base_dynamic_introspection_cache.py::test_handle_meta_list_cache_reuse`. Cache read/write is gated by lockfile hash in `src/bioimage_mcp/registry/dynamic/discovery.py`. |
| 2 | If the env lockfile cannot be found, tools.base meta.list still works and simply does not use the cache. | ✓ VERIFIED | `_calculate_lockfile_hash` returns empty string when lockfile missing; `discover_functions` only uses cache when `lockfile_hash` is truthy (`src/bioimage_mcp/registry/dynamic/discovery.py`). `handle_meta_list` does not require lockfile. |
| 3 | Dynamic introspection cache is written under ~/.bioimage-mcp/cache/dynamic/<tool_id> (not under the repo). | ✓ VERIFIED | Base entrypoint builds `cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id` (`tools/base/bioimage_mcp_base/entrypoint.py`). `IntrospectionCache` writes `introspection_cache.json` under that path (`src/bioimage_mcp/registry/dynamic/cache.py`). |
| 4 | Calling tools.trackpy meta.list twice reuses cached dynamic introspection when the env lockfile hash is unchanged. | ✓ VERIFIED | Trackpy entrypoint wires `IntrospectionCache` + `project_root` into `discover_functions` and tests assert cache hit/miss (`tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_cache_reuse`). |
| 5 | Trackpy meta.list still returns the canonical meta.list result shape (ok/result/functions/tool_version/introspection_source). | ✓ VERIFIED | `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` returns `ok` + `result` with required keys; test asserts canonical shape (`tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_canonical_shape`). |
| 6 | Trackpy dynamic cache is written under ~/.bioimage-mcp/cache/dynamic/tools.trackpy/. | ✓ VERIFIED | Trackpy entrypoint uses `Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id` and `IntrospectionCache` writes `introspection_cache.json` (`tools/trackpy/bioimage_mcp_trackpy/entrypoint.py`, `src/bioimage_mcp/registry/dynamic/cache.py`). |
| 7 | Second run of bioimage-mcp list avoids spawning tool subprocesses for dynamic meta.list when the env lockfile hash is unchanged. | ✓ VERIFIED | `DiscoveryEngine._runtime_list` checks lockfile hash and uses `MetaListCache.get` to return cached results before calling `execute_tool` (`src/bioimage_mcp/registry/engine.py`). Tests assert execute_tool skipped on cache hits (`tests/unit/registry/test_engine_runtime_list_cache.py::test_runtime_list_cache_hit_miss`). |
| 8 | Core-side runtime meta.list cache persists under ~/.bioimage-mcp/cache/ so repeated bioimage-mcp list invocations reuse cached results across processes. | ✓ VERIFIED | `MetaListCache` stores `meta_list_cache.json` under `Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id` and is read on subsequent engine instances (cross-instance reuse asserted in `test_engine_runtime_list_cache.py`). |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tools/base/bioimage_mcp_base/entrypoint.py` | meta.list wires IntrospectionCache + project_root into discover_functions | ✓ VERIFIED | Exists; substantive; `handle_meta_list` constructs cache dir and calls `discover_functions(..., cache=..., project_root=...)`. |
| `tests/unit/tools/test_base_dynamic_introspection_cache.py` | unit coverage for cache wiring + hit/miss behavior | ✓ VERIFIED | Exists; substantive; includes wiring and reuse/invalidation tests. |
| `tools/trackpy/bioimage_mcp_trackpy/dynamic_discovery.py` | Trackpy discovery adapter that emits FunctionMetadata | ✓ VERIFIED | Exists; substantive; `TrackpyAdapter.discover` maps introspected dicts to `FunctionMetadata`. |
| `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` | meta.list uses discover_functions + IntrospectionCache + robust project_root detection | ✓ VERIFIED | Exists; substantive; `handle_meta_list` builds cache dir and calls `discover_functions` with cache/project_root derived from env var/cwd/manifest. |
| `tests/unit/tools/test_trackpy_dynamic_introspection_cache.py` | unit coverage for trackpy cache reuse + project_root detection | ✓ VERIFIED | Exists; substantive; tests cache reuse and CWD/env var root detection + canonical shape. |
| `src/bioimage_mcp/registry/dynamic/meta_list_cache.py` | Persistent cache for parsed meta.list results | ✓ VERIFIED | Exists; substantive; `MetaListCache.get/put` read/write JSON keyed by lockfile hash + manifest checksum. |
| `src/bioimage_mcp/registry/engine.py` | DiscoveryEngine._runtime_list uses MetaListCache and skips execute_tool on hit | ✓ VERIFIED | Exists; substantive; cache check before execute_tool with lockfile hash. |
| `tests/unit/registry/test_engine_runtime_list_cache.py` | unit coverage for core runtime list cache hit/miss + invalidation | ✓ VERIFIED | Exists; substantive; asserts cache hit avoids execute_tool, invalidation causes refresh, and no-cache path when lockfile missing. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tools/base/bioimage_mcp_base/entrypoint.py` | `bioimage_mcp.registry.dynamic.discovery.discover_functions` | `handle_meta_list(..., cache=..., project_root=...)` | ✓ WIRED | `discover_functions(manifest, ADAPTER_REGISTRY, cache=cache, project_root=project_root)` present. |
| `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` | `bioimage_mcp.registry.dynamic.discovery.discover_functions` | `handle_meta_list(..., cache=..., project_root=...)` | ✓ WIRED | `discover_functions(manifest, {"trackpy": TrackpyAdapter()}, cache=cache, project_root=project_root)` present. |
| `src/bioimage_mcp/registry/engine.py` | `MetaListCache` | `cache.get/put around execute_tool` | ✓ WIRED | `_runtime_list` checks cache, returns on hit, writes on miss. |
| `src/bioimage_mcp/registry/engine.py` | `bioimage_mcp.runtimes.executor.execute_tool` | `called only on cache miss` | ✓ WIRED | execute_tool invoked only after cache miss/disabled path in `_runtime_list`. |

### Requirements Coverage

No Phase 13 requirements were mapped in `.planning/REQUIREMENTS.md`.

### Anti-Patterns Found

None detected in the verified artifacts.

### Human Verification Required

None.

### Gaps Summary

All must-haves verified. Cache reuse is wired for tools.base and tools.trackpy with lockfile gating and canonical output shape, and core-side `DiscoveryEngine._runtime_list` persists meta.list results under ~/.bioimage-mcp/cache/dynamic/ to avoid repeated subprocesses.

---

_Verified: 2026-01-29T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
