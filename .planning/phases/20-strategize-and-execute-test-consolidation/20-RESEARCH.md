# Phase 20: Strategize and execute test consolidation - Research

**Researched:** 2026-02-04
**Domain:** Testing strategy, CI/CD, and test suite optimization
**Confidence:** HIGH

## Summary

This phase focuses on consolidating the test suite into a coherent, hierarchical structure that balances speed and coverage. The current suite has evolved many markers and tiers (unit, contract, integration, smoke) which need standardization. Key findings indicate that while the directory structure is sound, the enforcement of markers and the definition of the PR-gating suite need refinement to prevent CI bloat while maintaining confidence in core toolpacks (Cellpose, Trackpy).

**Primary recommendation:** Rename `smoke_full` to `smoke_extended` and introduce a `smoke_pr` marker for the PR-required gate that specifically includes representative toolpacks and core image filter equivalence tests.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x+ | Test runner | Ecosystem standard, flexible marker system |
| anyio | 4.x+ | Async test support | Used for MCP client/server interaction tests |
| pydantic | 2.x+ | Contract validation | Used for strict IPC/schema validation in contract tests |
| numpy | 1.24+ | Data comparison | Baseline for array equivalence checks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bioio | 1.1+ | Image I/O | Verifying artifact contents in smoke tests |
| pandas | 2.x+ | Table comparison | Verifying table artifacts |
| jsonschema | 4.x+ | Schema validation | Validating artifact metadata against JSON Schema |

**Installation:**
```bash
pip install pytest anyio pydantic numpy bioio pandas jsonschema
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── unit/            # Fast logic tests, no external dependencies or server startup
├── contract/        # Schema and IPC boundary tests, uses Pydantic/JSON Schema
├── integration/     # Feature-level tests, server interaction, no toolpacks
└── smoke/           # End-to-end equivalence and live toolpack tests
    ├── utils/       # Helpers (DataEquivalence, NativeExecutor)
    └── reference_scripts/ # Baselines for equivalence
```

### Pattern 1: Tiered Marker System
**What:** Use markers to select test subsets for different environments (local, CI-PR, CI-Nightly).
**When to use:** All tests.
**Example:**
```python
@pytest.mark.smoke_pr
@pytest.mark.requires_env("bioimage-mcp-cellpose")
async def test_cellpose_equivalence(...):
    ...
```

### Anti-Patterns to Avoid
- **Bit-for-bit float comparison:** Fails across platforms or library versions. Use `np.allclose` or `DataEquivalenceHelper`.
- **Hard-coded set equality for keys:** Blocks additive evolution of API responses. Use `issubset` for required keys only.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Array Equivalence | Custom loops | `numpy.testing` | Handles NaNs, tolerances, and shapes correctly |
| Label Matching | Exact label ID check | IoU matching | Label IDs can vary between runs but boundaries should match |
| Schema Validation | Manual dict checks | Pydantic/jsonschema | Robust validation, clear error messages |

**Key insight:** Use the existing `DataEquivalenceHelper` for all smoke/equivalence tests to ensure consistent tolerance and IoU logic.

## Common Pitfalls

### Pitfall 1: Overly Strict Contract Assertions
**What goes wrong:** Adding a new field to a discovery response (e.g., `tool_version`) breaks all contract tests.
**Why it happens:** Tests use `assert set(resp.keys()) == allowed_keys` or similar.
**How to avoid:** Use `required_keys.issubset(resp.keys())` to allow for additive compatibility.

### Pitfall 2: Silent Skips
**What goes wrong:** CI passes but 50% of tests skipped because an environment wasn't installed correctly.
**Why it happens:** `pytest.skip` is used silently.
**How to avoid:** Use a standard `check_required_env` fixture that warns loudly (e.g., `warnings.warn`) when skipping optional environments in certain modes.

## Code Examples

Verified patterns from official sources:

### Additive-Compatible Key Check
```python
def test_describe_function_contract(described):
    required_keys = {"id", "params_schema", "inputs", "outputs"}
    # GOOD: Allows extra fields
    assert required_keys.issubset(described.keys())
    # BAD: Fails if new fields added
    # assert set(described.keys()) == required_keys
```

### Tolerance in Table Comparison
```python
import pandas as pd
def test_table_equivalence(actual_df, expected_df):
    # Use rtol for float columns
    pd.testing.assert_frame_equal(actual_df, expected_df, rtol=1e-5)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `smoke_full` | `smoke_pr` vs `smoke_extended` | Phase 20 | Faster PR feedback, better nightly coverage |
| Exact label check | IoU/Hungarian matching | Phase 18 | Reliable segmentation verification |
| Silent skips | Warn-on-skip | Phase 20 | Better visibility into test coverage |

**Deprecated/outdated:**
- `requires_cellpose`, `requires_stardist`: Replace with `@pytest.mark.requires_env("bioimage-mcp-...")`.

## Open Questions

Things that couldn't be fully resolved:

1. **PR-Gating Base Image Filter:**
   - Recommendation: Use `skimage.filters.gaussian` as the primary representative for the base environment image-filter theme.
2. **Warn-on-skip Implementation:**
   - What we know: `pytest.skip` stops execution immediately.
   - What's unclear: Best way to trigger a warning *and* skip in a single hook.
   - Recommendation: Issue `warnings.warn` before calling `pytest.skip` in the `check_required_env` fixture.

## Sources

### Primary (HIGH confidence)
- `tests/contract/*.py` - Reviewed existing strictness issues.
- `tests/smoke/conftest.py` - Analyzed marker and skip logic.
- `tests/smoke/utils/data_equivalence.py` - Verified tolerance support.

### Secondary (MEDIUM confidence)
- `20-CONTEXT.md` - Captured implementation decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Pytest and standard data libs are stable.
- Architecture: HIGH - Tiers are well-defined in context.
- Pitfalls: HIGH - Known issues from previous phases.

**Research date:** 2026-02-04
**Valid until:** 2026-03-04
