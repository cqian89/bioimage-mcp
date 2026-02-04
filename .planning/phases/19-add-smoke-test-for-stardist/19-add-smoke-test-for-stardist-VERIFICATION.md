---
phase: 19-add-smoke-test-for-stardist
verified: 2026-02-04T00:00:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 19: Add smoke test for stardist Verification Report

**Phase Goal:** Add smoke test for stardist
**Verified:** 2026-02-04T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | StarDist smoke test can be run via pytest in smoke-full mode | ✓ VERIFIED | `tests/smoke/test_equivalence_stardist.py` is marked `@pytest.mark.smoke_full` and defines `test_stardist_equivalence`. |
| 2 | StarDist smoke test is safely skipped when bioimage-mcp-stardist env is missing | ✓ VERIFIED | `tests/smoke/conftest.py` maps `requires_stardist` → `bioimage-mcp-stardist` and skips when unavailable; test is marked `@pytest.mark.requires_stardist`. |
| 3 | MCP StarDist inference outputs (labels + details) are structurally valid and label-equivalent to a native baseline | ✓ VERIFIED | Test asserts LabelImageRef + NativeOutputRef structure, validates details keys, and compares labels via `assert_labels_equivalent(iou_threshold=0.95)` against baseline output. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tests/smoke/test_equivalence_stardist.py` | End-to-end smoke test comparing MCP vs native StarDist | ✓ VERIFIED | Exists, substantive (158 lines), exports test `test_stardist_equivalence`, wired to live MCP calls + native baseline. |
| `tests/smoke/reference_scripts/stardist_baseline.py` | Native StarDist baseline runner (official example) emitting JSON contract | ✓ VERIFIED | Exists, substantive (107 lines), uses `StarDist2D.from_pretrained`, emits JSON on stdout. |
| `pytest.ini` | Pytest marker registration for requires_stardist | ✓ VERIFIED | Contains `requires_stardist` marker definition. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tests/smoke/test_equivalence_stardist.py` | `tools/stardist/manifest.yaml` | tools/run fn_id calls | ✓ VERIFIED | Contains `id` values `stardist.models.StarDist2D.from_pretrained` and `stardist.models.StarDist2D.predict_instances`. |
| `tests/smoke/test_equivalence_stardist.py` | `tests/smoke/reference_scripts/stardist_baseline.py` | NativeExecutor.run_script | ✓ VERIFIED | Calls `native_executor.run_script(...)` with `reference_scripts/stardist_baseline.py`. |
| `tests/smoke/test_equivalence_stardist.py` | `tests/smoke/utils/data_equivalence.py` | DataEquivalenceHelper.assert_labels_equivalent | ✓ VERIFIED | Calls `helper.assert_labels_equivalent(...)`. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| No mapped requirements for Phase 19 | N/A | Requirements not mapped to phases in REQUIREMENTS.md |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | - | - | - |

### Human Verification Required

No human-only checks required for goal verification. Runtime behavior (model download, inference) is exercised by the test itself when the env is available.

### Gaps Summary

All must-haves verified. Artifacts are present, substantive, and wired. Key links are in place.

---

_Verified: 2026-02-04T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
