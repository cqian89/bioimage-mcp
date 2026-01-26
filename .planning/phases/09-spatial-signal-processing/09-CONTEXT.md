# Phase 9: Spatial & Signal Processing - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Support advanced spatial metrics and spectral signal analysis via `scipy.spatial` and `scipy.signal`.
This phase is about broad, dynamic function/class exposure with artifact-based I/O, plus stateful refs for spatial indexes.

Key deliverables:
- Broad discovery and execution for non-deprecated `scipy.spatial` + `scipy.signal` API (default-include; blacklist-based exclusion)
- Distance matrix computation (e.g., `pdist`, `cdist`)
- Stateful spatial indexing and querying (KDTree/cKDTree and other public classes as refs)
- Spectral analysis (e.g., Welch, Periodogram; multi-output)
- Signal processing basics (e.g., convolution/filtering)

</domain>

<decisions>
## Implementation Decisions

### Discovery scope + blacklist rules
- **Default include:** Non-deprecated public callables in `scipy.spatial` and `scipy.signal` MUST be included by default.
- **Coverage:** Traverse public submodules under both packages (not just top-level re-exports).
- **Callable types:** Expose public functions AND public classes by default.
- **Exclusion mechanism:** Exclusions MUST be done via a blacklist (not by narrow allowlists/curation).
- **Deprecated handling:** Deprecated callables are excluded by default.
- **Blacklist justification:** Blacklist entries should have an explicit reason; locked acceptable reason: “not meaningful for MCP”.

### KDTree Persistence
- **Stateful Pattern:** Agent builds tree -> gets ID -> queries ID (not functional pass-through).
- **Storage:** In-Memory Session Store (ephemeral, lost on server restart).
- **Lifecycle:** Refs live for the whole session and auto-clear on session exit. No explicit `free()` required.
- **Method exposure:** Public methods only (no `_`-prefixed, no dunder); one tool per method.
- **Addressing:** Use standard `ref_id` pattern for object references.

### Stateful objects + session persistence
- **Ref coverage:** Support stateful `ref_id` objects for public, non-deprecated classes from BOTH `scipy.spatial` and `scipy.signal` (unless blacklisted).
- **Storage:** In-memory per session only (no artifact-backed serialization).
- **Limits:** No hard limits (no arbitrary caps on object count/size beyond inherent runtime constraints).

### Distance Matrix Output
- **Format:** Return NumPy (`.npy`) artifacts.
- **Shape:** Follow native Scipy behavior (pdist=condensed 1D, cdist=square 2D).
- **Input:** Strict Coordinate Arrays only. Do NOT accept Label Images directly (agent must extract centroids first).

### I/O pattern expansion policy
- **Default array artifact:** Use `.npy` for array-like inputs/outputs (supports complex types).
- **Inline convenience:** Allow small inline numeric arrays/lists in addition to `.npy` artifacts.
- **Pattern growth:** When a signature doesn’t match existing patterns, add a NEW reusable I/O pattern (prefer general patterns over per-function special casing).
- **Validation posture:** Accept small inline arrays, but keep artifact-first ergonomics for real data.

### Signal/spatial output structure
- **Multi-output:** Default to dict-of-outputs for multi-output callables (e.g., `welch`, `periodogram`, `csd`, `stft`, `istft`).
- **Key names:** Use native SciPy output names (`f`, `Pxx`, `t`, `Zxx`, etc.).
- **Non-array outputs:** Return non-array/small structured results as JSON artifacts.
- **Defaults:** Match SciPy defaults for `axis` and `fs` (do not require explicit `fs`; do not auto-extract from OME metadata).

### Claude's Discretion
- Exact threshold for “small inline arrays” vs requiring artifacts.
- Additional blacklist reasons if discovered during research (should remain exceptional and documented).

</decisions>

<specifics>
## Specific Ideas

- "What is scipy's native behaviour? This is a rule - stick to it."
- Use `ref_id` for consistent referencing across the system.
- Dynamic discovery must be broad and not rigid; expand I/O patterns when needed.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-spatial-signal-processing*
*Context gathered: 2026-01-26*
