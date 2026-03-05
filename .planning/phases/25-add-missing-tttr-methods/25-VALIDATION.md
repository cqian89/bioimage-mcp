---
phase: 25
slug: add-missing-tttr-methods
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-05
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/contract/test_tttrlib_manifest.py tests/contract/test_tttrlib_schema_alignment.py -q` |
| **Full suite command** | `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/contract/test_tttrlib_manifest.py tests/contract/test_tttrlib_schema_alignment.py -q`
- **After every plan wave:** Run `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | TTTR-01 | contract | `pytest tests/contract/test_tttrlib_manifest.py tests/contract/test_tttrlib_schema_alignment.py -q` | ✅ | ⬜ pending |
| 25-01-02 | 01 | 1 | TTTR-04 | unit | `pytest tests/unit/tools/test_tttrlib_entrypoint.py -q` | ✅ | ⬜ pending |
| 25-02-01 | 02 | 2 | TTTR-02 | contract | `pytest tests/contract/test_tttrlib_manifest.py tests/contract/test_tttrlib_schema_alignment.py -q` | ✅ | ⬜ pending |
| 25-02-02 | 02 | 2 | TTTR-03 | smoke | `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q` | ✅ | ⬜ pending |
| 25-03-01 | 03 | 3 | TTTR-02 | contract | `pytest tests/contract/test_tttrlib_manifest.py tests/contract/test_tttrlib_schema_alignment.py -q` | ✅ | ⬜ pending |
| 25-03-02 | 03 | 3 | TTTR-05 | smoke | `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
