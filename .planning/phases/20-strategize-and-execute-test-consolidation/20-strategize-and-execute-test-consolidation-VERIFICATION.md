---
phase: 20-strategize-and-execute-test-consolidation
verified: 2026-02-04T12:20:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 20: Strategize and execute test consolidation Verification Report

**Phase Goal:** Coherent, marker-driven test suite tiers (unit/contract/integration/smoke) with predictable local runs and a small PR-gating smoke set.
**Verified:** 2026-02-04T12:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Smoke tiers are selectable via markers (smoke_minimal/smoke_pr/smoke_extended). | ✓ VERIFIED | `pytest.ini` defines markers; `tests/smoke/conftest.py` interprets `--smoke-pr`/`--smoke-extended` flags and sets `SmokeMode`. |
| 2 | Running smoke tests by directory defaults to a small suite unless expanded. | ✓ VERIFIED | `tests/smoke/conftest.py` defaults `SmokeMode.MINIMAL` and skips `smoke_pr`/`smoke_extended` tests unless `--smoke-pr`/`--smoke-extended` is set. |
| 3 | Env-gated tests skip with actionable warning when env missing. | ✓ VERIFIED | `tests/conftest.py` `check_required_env` warns with `bioimage-mcp install <tool>` message and skips when `requires_env` env is unavailable. |
| 4 | Discovery contract tests are additive-compatible and meta.describe descriptions are best-effort. | ✓ VERIFIED | `tests/contract/test_discovery_contract.py` uses subset checks on list/search/describe keys; `tests/contract/test_meta_describe_contract.py` allows missing property descriptions. |
| 5 | PR smoke tier covers base + representative optional tools; extended contains remaining equivalence tests with tolerance comparisons. | ✓ VERIFIED | `tests/smoke/test_equivalence_skimage.py` (smoke_pr), `test_equivalence_cellpose.py` (smoke_pr), `test_equivalence_trackpy.py` (smoke_pr) with other `test_equivalence_*` marked `smoke_extended`; `tests/smoke/utils/data_equivalence.py` uses `assert_allclose` tolerances and scipy/trackpy tests use `rtol`/`approx`. |
| 6 | PR gate commands and marker semantics are documented in one place. | ✓ VERIFIED | `AGENTS.md` includes PR gate commands and marker semantics; `.planning/codebase/TESTING.md` mirrors commands and marker tier descriptions. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `pytest.ini` | Marker definitions for tiers and env gating | ✓ VERIFIED | Includes `smoke_minimal`, `smoke_pr`, `smoke_extended`, `requires_env`. |
| `tests/conftest.py` | Global env gating with actionable warnings | ✓ VERIFIED | `check_required_env` warns and skips on missing `requires_env`. |
| `tests/smoke/conftest.py` | Smoke tier selection and default minimal mode | ✓ VERIFIED | Default `SmokeMode.MINIMAL`, skip logic for PR/extended tiers. |
| `tests/smoke/test_smoke_markers.py` | Enforces marker rules on equivalence tests | ✓ VERIFIED | AST-based enforcement: exactly one of `smoke_pr`/`smoke_extended`, requires env + dataset marker. |
| `tests/contract/test_discovery_contract.py` | Additive-compatible discovery contract | ✓ VERIFIED | Subset checks on response keys. |
| `tests/contract/test_meta_describe_contract.py` | Best-effort param description handling | ✓ VERIFIED | Missing descriptions allowed; validates if present. |
| `src/bioimage_mcp/registry/loader.py` + `tests/unit/registry/test_manifest_discovery.py` | Manifest-only discovery logic + test | ✓ VERIFIED | `discover_manifest_paths` only scans `manifest.yaml`/`manifest.yml`. |
| `tests/smoke/test_equivalence_*.py` | Correct tier markers for equivalence tests | ✓ VERIFIED | PR tier includes skimage/cellpose/trackpy; remaining equivalence tests are `smoke_extended`. |
| `tests/smoke/utils/data_equivalence.py` | Tolerance-based equivalence helper | ✓ VERIFIED | `assert_arrays_equivalent` uses `assert_allclose` with tolerances. |
| `AGENTS.md` + `.planning/codebase/TESTING.md` | Documented PR gate commands + markers | ✓ VERIFIED | Commands and marker semantics documented. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `pytest.ini` | Marker usage | pytest marker discovery | ✓ WIRED | Tests reference markers defined in config. |
| `tests/conftest.py` | Env-gated tests | `requires_env` marker | ✓ WIRED | Autouse fixture inspects marker and skips with warning. |
| `tests/smoke/conftest.py` | Smoke tests | `_is_smoke_item` + `SmokeMode` | ✓ WIRED | Default minimal mode skips PR/extended tests without flags. |
| `tests/smoke/test_smoke_markers.py` | `tests/smoke/test_equivalence_*.py` | AST marker enforcement | ✓ WIRED | Enforces one tier marker + env/dataset markers. |
| `discover_manifest_paths` | Manifest discovery tests | `tests/unit/registry/test_manifest_discovery.py` | ✓ WIRED | Test validates only manifest filenames are discovered. |
| `DataEquivalenceHelper` | Equivalence tests | `assert_allclose` tolerances | ✓ WIRED | Used across equivalence tests for float comparisons. |

### Requirements Coverage

No requirements mapped to Phase 20 in `.planning/REQUIREMENTS.md`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `tests/smoke/test_equivalence_phasorpy.py` | 19-22 | “expected to fail initially” docstring | ⚠️ Warning | Indicates a known-failing extended smoke test; does not block PR-tier goal but should be tracked. |

### Human Verification Required

None.

### Gaps Summary

All must-haves verified. Phase goal achieved.

---

_Verified: 2026-02-04T12:20:00Z_
_Verifier: Claude (gsd-verifier)_
