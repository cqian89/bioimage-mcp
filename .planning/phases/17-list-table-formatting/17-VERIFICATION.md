---
phase: 17-list-table-formatting
verified: 2026-02-02T00:00:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 17: List Table Formatting Verification Report

**Phase Goal:** Update `bioimage-mcp list` CLI output to show hierarchical tool/package structure with actual library versions (lockfile-first) instead of a flat tool-pack list with manifest versions.
**Verified:** 2026-02-02T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `bioimage-mcp list` shows a tool-pack list with nested package breakdown (not a flat tool-only list). | ✓ VERIFIED | `list.py` renders tool rows plus indented package rows (tree prefixes `├──/└──`) and builds `packages` from function IDs (`_render_list` lines ~47-72; package grouping lines ~58-87). |
| 2 | `bioimage-mcp list --json` returns a stable hierarchical schema with per-tool `packages` and `function_count`. | ✓ VERIFIED | JSON output includes `tools` with `id`, `tool_version`, `library_version`, `status`, `function_count`, and `packages` (lines ~25-40). Tests assert packages and counts (`test_list_tools_json_output`). |
| 3 | `bioimage-mcp list --tool <id>` filtering works with both short IDs and legacy IDs. | ✓ VERIFIED | `_filter_tools` matches `id == filter` or `tools.<id> == filter` (lines ~81-86). |
| 4 | `bioimage-mcp list` shows real library versions (lockfile-first) for primary libraries. | ✓ VERIFIED | `_resolve_version` parses `envs/<env_id>.lock.yml` and maps package IDs to conda names via `PACKAGE_TO_CONDA` (lines ~23-76). Tool and package library versions set from this resolution (lines ~69-86). Tests verify lockfile-derived versions (`test_list_tools_lockfile_version`). |
| 5 | Missing lockfile falls back to live conda query (if env manager exists), otherwise to manifest tool_version. | ✓ VERIFIED | `_resolve_version` runs `<manager> list ... --json` when lockfile not found (lines ~79-95) and returns `None` otherwise; rendering uses `library_version or tool_version` (line ~62). |
| 6 | CLI list cache invalidates when relevant lockfiles change. | ✓ VERIFIED | `ListToolsCache.get_fingerprint` includes lockfile stats (lines ~103-109) and `list.py` passes lockfile paths into fingerprint (lines ~198-207, ~303-305). Test covers cache invalidation on lockfile change. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/bioimage_mcp/bootstrap/list.py` | Hierarchical CLI list transformation + text/JSON rendering with lockfile-first versions | ✓ VERIFIED | Exists (~309 lines), substantive implementation, wired to cache + lockfiles. |
| `src/bioimage_mcp/bootstrap/list_cache.py` | Cache invalidation bump/fingerprint includes lockfiles | ✓ VERIFIED | Exists (~152 lines), substantive, wired via `get_fingerprint` calls. |
| `tests/unit/bootstrap/test_list_output.py` | Unit coverage for new table + JSON output + lockfile version resolution | ✓ VERIFIED | Exists (~250 lines), tests cover tree output, JSON schema, lockfile versions, cache invalidation. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `list.py` | `list_cache.py` | `ListToolsCache.get_fingerprint(...)` | ✓ WIRED | Calls pass manifest paths, env hash, lockfile paths (lines ~198-207, ~303-305). |
| `list.py` | `envs/<env_id>.lock.yml` | YAML parse (`_resolve_version`) | ✓ WIRED | Resolves lockfile at `envs/{env_id}.lock.yml`, parses `package` entries (lines ~56-76). |
| `list_cache.py` | `envs/*.lock.yml` | Fingerprint `stat()` | ✓ WIRED | Lockfile stats included in fingerprint (lines ~103-109). |
| `tests/unit/bootstrap/test_list_output.py` | `list.py` | `list_mod.list_tools(...)` | ✓ WIRED | Tests call `list_tools` and assert output/schema/versions. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| None mapped for Phase 17 in REQUIREMENTS.md | N/A | N/A |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | - | - | - |

### Gaps Summary

All must-haves are present, substantive, and wired. The CLI list now renders a hierarchical tool→package view and resolves library versions from lockfiles with appropriate fallback behavior; cache fingerprinting updates on lockfile changes.

---

_Verified: 2026-02-02T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
