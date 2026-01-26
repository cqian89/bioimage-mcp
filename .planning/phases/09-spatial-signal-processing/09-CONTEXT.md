# Phase 9: Spatial & Signal Processing - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Support advanced spatial metrics and spectral signal analysis via `scipy.spatial` and `scipy.signal`.
Key deliverables:
- Distance matrix computation (pdist, cdist)
- KDTree spatial indexing and querying (stateful)
- Spectral analysis (Welch, Periodogram)
- Signal processing basics (Convolution, Filtering)

</domain>

<decisions>
## Implementation Decisions

### KDTree Persistence
- **Stateful Pattern:** Agent builds tree -> gets ID -> queries ID (not functional pass-through).
- **Storage:** In-Memory Session Store (ephemeral, lost on server restart).
- **Lifecycle:** Auto-clear on session exit. No explicit `free()` required from agent.
- **Addressing:** Use standard `ref_id` pattern for tree references.

### Distance Matrix Output
- **Format:** Always return NumPy (`.npy`) artifacts, regardless of size.
- **Shape:** Follow native Scipy behavior (pdist=condensed 1D, cdist=square 2D).
- **Input:** Strict Coordinate Arrays only. Do NOT accept Label Images directly (agent must extract centroids first).

### Signal Input Handling
- **N-D Support:** Follow native Scipy behavior. Expose `axis` parameter for N-D inputs.
- **Complex Results:** Return as `.npy` artifacts (which support complex types natively).
- **Physical Units:** Require manual `fs` (sampling frequency) parameter. Do not auto-extract from OME-XML.
- **Parameters:** Expose ALL parameters (window, overlap, etc.) rather than a curated subset.

### Spectral Output Format
- **Structure:** Dictionary of Artifacts (e.g., `{"f": "ref_1", "Pxx": "ref_2"}`).
- **Keys:** Use native Scipy variable names (e.g., `f`, `Pxx`) for the dictionary keys.
- **Visualization:** Data only. Do not auto-generate plots.

</decisions>

<specifics>
## Specific Ideas

- "What is scipy's native behaviour? This is a rule - stick to it."
- Use `ref_id` for consistent referencing across the system.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-spatial-signal-processing*
*Context gathered: 2026-01-26*
