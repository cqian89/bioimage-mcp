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
| 1 | Calling tools.base meta.list twice reuses cached dynamic introspection when the env lockfile hash is unchanged. | ✓ VERIFIED | `tools/base/bioimage_mcp_base/entrypoint.py` passes `IntrospectionCache` + `project_root` to `discover_functions`; cache hit/miss behavior covered in `tests/unit/tools/test_base_dynamic_introspection_cache.py::test_handle_meta_list_cache_reuse`. Cache key includes lockfile hash + manifest checksum in `src/bioimage_mcp/registry/dynamic/discovery.py`. |
| 2 | If the env lockfile cannot be found, tools.base meta.list still works and uses a sentinel cache key rather than failing. | ✓ VERIFIED | `discover_functions` uses `env_component = "no-lockfile"` when lockfile is absent; cache read/write still occurs (`src/bioimage_mcp/registry/dynamic/discovery.py`). Base entrypoint does not require a lockfile for meta.list. |
| 3 | Dynamic introspection cache is written under ~/.bioimage-mcp/cache/dynamic/<tool_id> (not under the repo). | ✓ VERIFIED | Base and trackpy entrypoints build `cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id`; `IntrospectionCache` writes `introspection_cache.json` under that path (`tools/base/bioimage_mcp_base/entrypoint.py`, `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py`, `src/bioimage_mcp/registry/dynamic/cache.py`). |
| 4 | Calling tools.trackpy meta.list twice reuses cached dynamic introspection when the env lockfile hash is unchanged. | ✓ VERIFIED | Trackpy entrypoint wires `IntrospectionCache` + `project_root` into `discover_functions` and tests assert cache hit/miss (`tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_cache_reuse`). |
| 5 | Trackpy meta.list still returns the canonical meta.list result shape (ok/result/functions/tool_version/introspection_source). | ✓ VERIFIED | `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` returns `ok` + `result` with required keys; test asserts canonical shape (`tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_canonical_shape`). |
| 6 | Trackpy cache writes succeed when project_root is discoverable (env var or cwd), and meta.list still succeeds without project_root. | ✓ VERIFIED | Trackpy entrypoint checks env var → cwd → manifest path for project_root; cache reuse + no-crash behavior validated in `tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_project_root_heuristics`. |
| 7 | Second run of `bioimage-mcp list` avoids spawning tool subprocesses for dynamic meta.list when the env lockfile hash is unchanged. | ✓ VERIFIED | `DiscoveryEngine._runtime_list` uses `MetaListCache.get` before calling `execute_tool` (`src/bioimage_mcp/registry/engine.py`); tests assert execute_tool skipped on cache hit (`tests/unit/registry/test_engine_runtime_list_cache.py::test_runtime_list_cache_hit_miss`). |
| 8 | Core-side runtime meta.list cache persists under ~/.bioimage-mcp/cache/dynamic/ so repeated list invocations reuse cached results across processes. | ✓ VERIFIED | `MetaListCache` stores `meta_list_cache.json` under `Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id`; cross-instance reuse validated in `tests/unit/registry/test_engine_runtime_list_cache.py`. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tools/base/bioimage_mcp_base/entrypoint.py` | meta.list wires IntrospectionCache + project_root into discover_functions | ✓ VERIFIED | Exists; substantive; `handle_meta_list` constructs cache dir and calls `discover_functions(..., cache=..., project_root=...)`. |
| `tests/unit/tools/test_base_dynamic_introspection_cache.py` | unit coverage for cache wiring + hit/miss behavior | ✓ VERIFIED | Exists; substantive; includes wiring, lockfile invalidation, and manifest checksum invalidation. |
| `tools/trackpy/bioimage_mcp_trackpy/dynamic_discovery.py` | Trackpy discovery adapter that emits FunctionMetadata | ✓ VERIFIED | Exists; substantive; `TrackpyAdapter.discover` maps introspected dicts to `FunctionMetadata`. |
| `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` | meta.list uses discover_functions + IntrospectionCache + robust project_root detection | ✓ VERIFIED | Exists; substantive; project_root from env var/cwd/manifest; cache dir under ~/.bioimage-mcp/cache/dynamic/<tool_id>. |
| `tests/unit/tools/test_trackpy_dynamic_introspection_cache.py` | unit coverage for trackpy cache reuse + project_root detection | ✓ VERIFIED | Exists; substantive; tests cache reuse, heuristics, and canonical shape. |
| `src/bioimage_mcp/registry/dynamic/meta_list_cache.py` | Persistent cache for parsed meta.list results | ✓ VERIFIED | Exists; substantive; `MetaListCache.get/put` read/write JSON keyed by lockfile hash + manifest checksum. |
| `src/bioimage_mcp/registry/engine.py` | DiscoveryEngine._runtime_list uses MetaListCache and skips execute_tool on hit | ✓ VERIFIED | Exists; substantive; cache check before execute_tool with lockfile hash. |
| `tests/unit/registry/test_engine_runtime_list_cache.py` | unit coverage for core runtime list cache hit/miss + invalidation | ✓ VERIFIED | Exists; substantive; asserts cache hit avoids execute_tool, invalidation causes refresh, and no-cache path when lockfile missing. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tools/base/bioimage_mcp_base/entrypoint.py` | `bioimage_mcp.registry.dynamic.discovery.discover_functions` | `handle_meta_list(..., cache=..., project_root=...)` | ✓ WIRED | `discover_functions(manifest, ADAPTER_REGISTRY, cache=cache, project_root=project_root)` present. |
| `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` | `bioimage_mcp.registry.dynamic.discovery.discover_functions` | `handle_meta_list(..., cache=..., project_root=...)` | ✓ WIRED | `discover_functions(manifest, {"trackpy": TrackpyAdapter()}, cache=cache, project_root=project_root)` present. |
| `src/bioimage_mcp/registry/dynamic/discovery.py` | `IntrospectionCache` | `cache.get/put with composite key` | ✓ WIRED | Cache key includes lockfile hash (or `no-lockfile`) + manifest checksum. |
| `src/bioimage_mcp/registry/engine.py` | `MetaListCache` | `cache.get/put around execute_tool` | ✓ WIRED | `_runtime_list` checks cache, returns on hit, writes on miss. |
| `src/bioimage_mcp/registry/engine.py` | `bioimage_mcp.runtimes.executor.execute_tool` | `called only on cache miss` | ✓ WIRED | execute_tool invoked only after cache miss/disabled path in `_runtime_list`. |

### Requirements Coverage

No Phase 13 requirements were mapped in `.planning/REQUIREMENTS.md`.

### Anti-Patterns Found

None detected in the verified artifacts.

### Human Verification Required

None.

### Gaps Summary

All must-haves verified. Dynamic introspection caches are persisted under ~/.bioimage-mcp/cache/dynamic/ with lockfile-gated keys (plus manifest checksum) and are wired for tools.base, tools.trackpy, and core runtime meta.list reuse.

---

_Verified: 2026-01-29T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
