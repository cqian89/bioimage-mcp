---
phase: 13-dynamic-introspection-cache-reuse
verified: 2026-01-29T00:00:00Z
status: passed
score: 13/13 must-haves verified
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
| 1 | Calling tools.base meta.list twice reuses cached dynamic introspection when the env lockfile hash is unchanged. | ✓ VERIFIED | `tools/base/bioimage_mcp_base/entrypoint.py` wires `IntrospectionCache` + `project_root` into `discover_functions`; cache behavior validated in `tests/unit/tools/test_base_dynamic_introspection_cache.py::test_handle_meta_list_cache_reuse` (lockfile change increments discovery). |
| 2 | If the env lockfile cannot be found, tools.base meta.list still works and uses a sentinel cache key rather than failing. | ✓ VERIFIED | `discover_functions` uses `env_component = "no-lockfile"` when lockfile missing (`src/bioimage_mcp/registry/dynamic/discovery.py`), and `tests/unit/registry/test_dynamic_discovery.py::test_discover_functions_caches_without_lockfile` asserts caching with sentinel. |
| 3 | Dynamic introspection cache is written under ~/.bioimage-mcp/cache/dynamic/<tool_id> (not under the repo). | ✓ VERIFIED | Base + trackpy entrypoints build `cache_dir = Path.home() / ".bioimage-mcp" / "cache" / "dynamic" / manifest.tool_id`; `IntrospectionCache` writes `introspection_cache.json` there (`tools/base/.../entrypoint.py`, `tools/trackpy/.../entrypoint.py`, `src/bioimage_mcp/registry/dynamic/cache.py`). |
| 4 | Calling tools.trackpy meta.list twice reuses cached dynamic introspection when the env lockfile hash is unchanged. | ✓ VERIFIED | Trackpy entrypoint wires `IntrospectionCache` + `project_root` into `discover_functions` and tests assert cache hit/miss (`tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_cache_reuse`). |
| 5 | Trackpy meta.list still returns the canonical meta.list result shape (ok/result/functions/tool_version/introspection_source). | ✓ VERIFIED | Trackpy entrypoint returns `ok` + `result` with required keys; test asserts canonical shape (`tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_canonical_shape`). |
| 6 | Trackpy cache writes succeed when project_root is discoverable (env var or cwd), and meta.list still succeeds without project_root. | ✓ VERIFIED | Trackpy entrypoint uses env var → cwd → manifest fallback for project_root; tests assert cache file creation + cache reuse (`tests/unit/tools/test_trackpy_dynamic_introspection_cache.py::test_trackpy_handle_meta_list_project_root_heuristics`). |
| 7 | Second run of `bioimage-mcp list` avoids spawning tool subprocesses for dynamic meta.list when the env lockfile hash is unchanged. | ✓ VERIFIED | `DiscoveryEngine._runtime_list` checks `MetaListCache.get` before `execute_tool` (`src/bioimage_mcp/registry/engine.py`); tests assert `execute_tool` skipped on cache hit (`tests/unit/registry/test_engine_runtime_list_cache.py::test_runtime_list_cache_hit_miss`). |
| 8 | Core-side runtime meta.list cache persists under ~/.bioimage-mcp/cache/dynamic/ so repeated list invocations reuse cached results across processes. | ✓ VERIFIED | `MetaListCache` stores `meta_list_cache.json` under `~/.bioimage-mcp/cache/dynamic/<tool_id>` and test validates cross-instance reuse (`tests/unit/registry/test_engine_runtime_list_cache.py`). |
| 9 | If `introspection_cache.json` is deleted, a subsequent discovery run recreates it (no silent cache bypass). | ✓ VERIFIED | `discover_functions` always attempts cache read/write with composite key (`src/bioimage_mcp/registry/dynamic/discovery.py`); cache write is exercised by cache-miss paths in base/trackpy tests and `tests/unit/registry/test_dynamic_discovery.py::test_discover_stores_results_in_cache`. |
| 10 | Changing a tool `manifest.yaml` invalidates tool-pack dynamic introspection cache and forces a refresh. | ✓ VERIFIED | Cache key includes `manifest.manifest_checksum[:16]` (`src/bioimage_mcp/registry/dynamic/discovery.py`); tests cover manifest checksum invalidation (`tests/unit/tools/test_base_dynamic_introspection_cache.py::test_handle_meta_list_cache_reuse` and `tests/unit/registry/test_dynamic_discovery.py::test_discover_invalidates_on_manifest_change`). |
| 11 | Warm-cache list invalidates when tool manifests change or when the env manager/installed envs snapshot changes. | ✓ VERIFIED | CLI list cache fingerprint includes manifest stats + envs hash (`src/bioimage_mcp/bootstrap/list_cache.py`); `tests/unit/bootstrap/test_list_cache.py::test_list_tools_cache_hit_logic` asserts invalidation on manifest change and envs cache removal. |
| 12 | `bioimage-mcp list --tool <tool_id>` filters list output for both table and JSON forms. | ✓ VERIFIED | `src/bioimage_mcp/cli.py` adds `--tool`; `list_tools` filters by exact id or short name; `tests/unit/bootstrap/test_list_tool_filter.py` validates exact + short + no match behavior. |
| 13 | If a per-tool dynamic cache file is deleted, the next `bioimage-mcp list` regenerates it even when the CLI cache is a hit. | ✓ VERIFIED | CLI cache-hit path checks for `~/.bioimage-mcp/cache/dynamic/<tool_id>/introspection_cache.json` and falls through to `load_manifests` when missing (`src/bioimage_mcp/bootstrap/list.py`); regression test in `tests/unit/bootstrap/test_list_cache.py::test_list_tools_dynamic_cache_fallback`. |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tools/base/bioimage_mcp_base/entrypoint.py` | meta.list wires IntrospectionCache + project_root into discover_functions | ✓ VERIFIED | Exists; substantive; `handle_meta_list` builds cache dir under `~/.bioimage-mcp/cache/dynamic/<tool_id>` and passes `cache` + `project_root`. |
| `tests/unit/tools/test_base_dynamic_introspection_cache.py` | unit coverage for cache wiring + hit/miss behavior | ✓ VERIFIED | Exists; substantive; tests wiring, lockfile invalidation, and manifest checksum invalidation. |
| `tools/trackpy/bioimage_mcp_trackpy/dynamic_discovery.py` | Trackpy discovery adapter that emits FunctionMetadata | ✓ VERIFIED | Exists; substantive; `TrackpyAdapter.discover` maps introspected dicts to `FunctionMetadata`. |
| `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` | meta.list uses discover_functions + IntrospectionCache + robust project_root detection | ✓ VERIFIED | Exists; substantive; project_root from env var/cwd/manifest; cache dir under `~/.bioimage-mcp/cache/dynamic/<tool_id>`. |
| `tests/unit/tools/test_trackpy_dynamic_introspection_cache.py` | unit coverage for trackpy cache reuse + project_root detection | ✓ VERIFIED | Exists; substantive; tests cache reuse, heuristics, and canonical shape. |
| `src/bioimage_mcp/registry/dynamic/discovery.py` | Cache key includes manifest checksum and sentinel for no-lockfile | ✓ VERIFIED | Exists; substantive; composite key `env_component:manifest_checksum[:16]`. |
| `src/bioimage_mcp/registry/dynamic/cache.py` | IntrospectionCache persists `introspection_cache.json` under cache dir | ✓ VERIFIED | Exists; substantive; read/write JSON with nested key structure. |
| `src/bioimage_mcp/registry/dynamic/meta_list_cache.py` | Persistent cache for parsed meta.list results | ✓ VERIFIED | Exists; substantive; `MetaListCache.get/put` keyed by lockfile hash + manifest checksum. |
| `src/bioimage_mcp/registry/engine.py` | DiscoveryEngine._runtime_list uses MetaListCache and skips execute_tool on hit | ✓ VERIFIED | Exists; substantive; cache check before execute_tool with lockfile hash. |
| `tests/unit/registry/test_engine_runtime_list_cache.py` | unit coverage for core runtime list cache hit/miss + invalidation | ✓ VERIFIED | Exists; substantive; asserts cache hit avoids execute_tool and invalidation forces refresh. |
| `src/bioimage_mcp/bootstrap/list_cache.py` | Persistent CLI list cache for installed envs and tool summaries | ✓ VERIFIED | Exists; substantive; file-backed caches with fingerprinting + TTL. |
| `src/bioimage_mcp/bootstrap/list.py` | CLI list uses caches and falls back when dynamic cache missing | ✓ VERIFIED | Exists; substantive; checks dynamic cache files and invalidates cache hit when missing. |
| `src/bioimage_mcp/cli.py` | CLI `list` supports `--tool` filter | ✓ VERIFIED | Exists; substantive; `--tool` argument wired to `list_tools`. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tools/base/bioimage_mcp_base/entrypoint.py` | `bioimage_mcp.registry.dynamic.discovery.discover_functions` | `handle_meta_list(..., cache=..., project_root=...)` | ✓ WIRED | `discover_functions(manifest, ADAPTER_REGISTRY, cache=cache, project_root=project_root)` present. |
| `tools/trackpy/bioimage_mcp_trackpy/entrypoint.py` | `bioimage_mcp.registry.dynamic.discovery.discover_functions` | `handle_meta_list(..., cache=..., project_root=...)` | ✓ WIRED | `discover_functions(manifest, {"trackpy": TrackpyAdapter()}, cache=cache, project_root=project_root)` present. |
| `src/bioimage_mcp/registry/dynamic/discovery.py` | `IntrospectionCache` | `cache.get/put with composite key` | ✓ WIRED | Composite key includes lockfile hash or sentinel + manifest checksum. |
| `src/bioimage_mcp/registry/engine.py` | `MetaListCache` | `cache.get/put around execute_tool` | ✓ WIRED | `_runtime_list` checks cache, returns on hit, writes on miss. |
| `src/bioimage_mcp/bootstrap/list.py` | `src/bioimage_mcp/registry/loader.py` | `load_manifests` on cache-miss fallback | ✓ WIRED | On missing dynamic cache, falls through to manifest loading. |

### Requirements Coverage

No Phase 13 requirements were mapped in `.planning/REQUIREMENTS.md`.

### Anti-Patterns Found

None detected in the verified artifacts for this phase.

### Human Verification Required

None.

### Gaps Summary

All must-haves verified. Dynamic introspection caches are persisted under ~/.bioimage-mcp/cache/dynamic/ with lockfile-gated keys (plus manifest checksum), and are wired for tools.base, tools.trackpy, core runtime meta.list reuse, and CLI cache fallback when dynamic cache is missing.

---

_Verified: 2026-01-29T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
