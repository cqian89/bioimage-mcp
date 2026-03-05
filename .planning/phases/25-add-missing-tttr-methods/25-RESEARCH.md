# Phase 25: Add missing TTTR methods - Research

**Researched:** 2026-03-05
**Domain:** tttrlib API parity and MCP contract mapping
**Confidence:** HIGH

## Summary

Phase 25 should expand `tools.tttrlib` from a curated minimal surface (11 exposed callables) toward near-full parity with the installed runtime while preserving MCP guarantees (artifact boundary, stable IDs, deterministic errors, native dims).

Runtime introspection in `bioimage-mcp-tttrlib` shows substantial uncovered callable surface in core classes alone (`TTTR`, `CLSMImage`, `Correlator`). The safest implementation path is contract-first and staged:

1. Generate a reproducible runtime gap inventory.
2. Add parity in focused method families (read/selection/statistics/export first, then CLSM/correlation accessors/transforms).
3. Encode unsupported methods in explicit deny/defer metadata with stable remediation.
4. Keep manifest/schema/entrypoint/tests synchronized on every slice.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tttrlib` | runtime-installed (schema currently `0.25.0`) | Upstream TTTR/FLIM API | Source of truth for callable parity target. |
| `PyYAML` | existing | Manifest parsing in tests/tools | Existing contract tests already use it. |
| `pytest` | existing | Contract + smoke verification | Existing repo gate and tttrlib suites use pytest. |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `bioio-ome-zarr` | BioImageRef OME-Zarr outputs | Any image-like new method output. |
| `json`/`csv` stdlib + `numpy` | NativeOutputRef/TableRef materialization | Irregular/tabular outputs from method mapping. |

## Architecture Patterns

### Pattern 1: Contract Triad Synchronization
Every new callable must be added in lockstep across:
- `tools/tttrlib/manifest.yaml` (public discovery surface)
- `tools/tttrlib/schema/tttrlib_api.json` (schema alignment source)
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py` (`FUNCTION_HANDLERS` + implementation)

Mismatch in any leg should fail contract tests.

### Pattern 2: Explicit Method Mapping Table
For each candidate method, decide and document one of:
- **supported** (full mapping),
- **supported_subset** (partial with explicit limits),
- **deferred** (future),
- **denied** (not MCP-safe).

Keep strict upstream IDs (`tttrlib.Class.method`) and avoid aliases.

### Pattern 3: Output-Type Policy by Shape
- Dense image-like arrays -> `BioImageRef` (`OME-Zarr`, native axes/dims).
- Regular 2D metrics -> `TableRef`.
- Nested/irregular payloads -> `NativeOutputRef` (JSON).
- Reusable heavy objects -> `ObjectRef` (session-scoped).

### Pattern 4: File-Write Guardrails
For write/export callables, require explicit path parameters and bounded behavior:
- resolve relative paths under `work_dir`,
- reject unsafe target patterns,
- return stable error codes with remediation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Runtime parity source | Manual handwritten missing list | Runtime introspection script in tttrlib env | Prevents stale parity assumptions across tttrlib versions. |
| Output metadata | Ad-hoc dims heuristics per method | Existing native-dims metadata pattern from current tttr handlers | Preserves bioimage contract consistency. |
| Drift detection | Human-only reviews | Contract tests for manifest/schema/handler parity | Deterministic regression protection. |

## Common Pitfalls

### Pitfall 1: SWIG overload ambiguity
**What goes wrong:** Signatures are not fully introspectable; strict param schemas can over-constrain valid calls.
**How to avoid:** Use practical schema surfaces for overloaded methods, validate at runtime, and return stable error hints.

### Pitfall 2: Unsafe method exposure
**What goes wrong:** Methods that mutate internal state or require unsupported native pointers are exposed as if safe.
**How to avoid:** Denylist unsafe methods explicitly and test denied paths for stable error behavior.

### Pitfall 3: Large output explosion
**What goes wrong:** Large arrays are serialized as JSON/native blobs, breaking memory and response contracts.
**How to avoid:** Keep artifactized outputs for arrays and reserve `NativeOutputRef` for irregular payloads only.

## Validation Architecture

Use a two-tier validation strategy:

1. **Fast contract tier (per task):**
   - `pytest tests/contract/test_tttrlib_manifest.py -q`
   - `pytest tests/contract/test_tttrlib_schema_alignment.py -q`
   - Added parity-specific unit/contract checks for gap inventory + denylist completeness.

2. **Representative live tier (per wave):**
   - `pytest tests/smoke/test_tttrlib_live.py -m smoke_extended -q`
   - Target representative newly exposed method families (TTTR selection/statistics, CLSM transforms/correlation accessors, guarded write/export).

## Recommended Requirement IDs for Phase 25

- `TTTR-01`: Runtime parity inventory exists and tracks missing methods by status (supported/subset/deferred/denied).
- `TTTR-02`: TTTR + CLSMImage + Correlator method coverage is expanded with strict upstream IDs.
- `TTTR-03`: New callable outputs follow artifact policy (`BioImageRef`/`TableRef`/`NativeOutputRef`/`ObjectRef`) with native dims preserved for images.
- `TTTR-04`: Unsupported or unsafe methods are explicitly denylisted/deferred with stable error remediation.
- `TTTR-05`: Contract and representative smoke tests cover new method families and prevent manifest/schema/handler drift.

## Sources

### Primary (HIGH confidence)
- `tools/tttrlib/manifest.yaml`
- `tools/tttrlib/schema/tttrlib_api.json`
- `tools/tttrlib/bioimage_mcp_tttrlib/entrypoint.py`
- `tests/contract/test_tttrlib_manifest.py`
- `tests/contract/test_tttrlib_schema_alignment.py`
- `tests/smoke/test_tttrlib_live.py`
- Runtime introspection via `conda run -n bioimage-mcp-tttrlib python ...`

## Metadata

**Confidence breakdown:**
- Parity target and gaps: HIGH
- Mapping strategy and guardrails: HIGH
- Method-family prioritization: MEDIUM

**Research date:** 2026-03-05
**Valid until:** 2026-04-05
