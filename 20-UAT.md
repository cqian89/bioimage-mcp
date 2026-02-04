# Phase 20 UAT: Strategize and execute test consolidation

## Testable Deliverables

| ID | Goal | Expected Behavior | Result |
|----|------|-------------------|--------|
| T1 | Smoke Tiers Visibility | `pytest --markers` shows `smoke_minimal`, `smoke_pr`, and `smoke_extended`. | PASS |
| T2 | Global Env Gating | Running a test requiring a missing environment (e.g. `pytest -m requires_env('non-existent')`) skips with an actionable warning. | PASS |
| T3 | Additive Discovery Contract | `pytest tests/contract/test_discovery_contract.py` passes even if extra keys are present in discovery responses. | PASS |
| T4 | Best-Effort Descriptions | `pytest tests/contract/test_meta_describe_contract.py` passes for tools with missing parameter descriptions. | PASS |
| T5 | Manifest-Only Discovery | `pytest tests/unit/registry/test_manifest_discovery.py` confirms only `manifest.yaml` files are processed. | PASS |
| T6 | Core Server Lightness | `pytest tests/contract/test_no_bioio_in_core.py` passes (no top-level `bioio` import). | PASS |
| T7 | PR-Gating Tier | `pytest tests/smoke -m smoke_pr` executes the representative set (skimage gaussian, cellpose, trackpy). | PASS |
| T8 | Numeric Tolerance | `pytest tests/smoke/test_equivalence_scipy.py` (or similar) uses tolerances for numeric comparison. | PASS |
| T9 | Documentation Accuracy | `AGENTS.md` correctly lists the new smoke tiers and PR gate commands. | PASS |

## Execution Log

- [x] T1: Smoke Tiers Visibility
- [x] T2: Global Env Gating
- [x] T3: Additive Discovery Contract
- [x] T4: Best-Effort Descriptions
- [x] T5: Manifest-Only Discovery
- [x] T6: Core Server Lightness
- [x] T7: PR-Gating Tier
- [x] T8: Numeric Tolerance
- [x] T9: Documentation Accuracy

**All tests passed. Phase 20 verified.**
