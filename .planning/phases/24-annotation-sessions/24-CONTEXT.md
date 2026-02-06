# Phase 24: µSAM Session & Optimization - Context

**Gathered:** 2026-02-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve µSAM workflow latency by reusing compatible predictor state and standardizing embedding storage/reuse behavior. This phase defines session behavior and embedding lifecycle within existing µSAM headless and interactive capabilities; it does not add new product capabilities.

</domain>

<decisions>
## Implementation Decisions

### Session reuse policy
- Reuse predictor state by default for repeated calls in the same MCP session.
- Reuse is shared across supported µSAM entrypoints when model/image context is compatible.
- Interactive annotator launch should warm-start from existing state when compatible.
- Automatic reset should happen only on incompatibility, not on timeouts or workflow completion.

### Embedding storage contract
- Embedding reuse key is `image + model`.
- Standardized embeddings are session-scoped by default (no default cross-session persistence).
- If multiple valid embeddings exist for the same key, use the most recent one.
- Enforce strict format/version compatibility for reuse.

### Invalidation behavior
- Any model mismatch or image mismatch invalidates reuse.
- ROI/crop flows may reuse parent image embeddings when compatible.
- If cached state is corrupted/unreadable, emit warning metadata and recompute.
- Incompatible cache entries are purged immediately when detected.

### User-visible controls
- Default response feedback is minimal cache status (hit/miss/reset summary).
- Provide explicit per-run `force fresh` control to bypass reuse.
- Provide explicit action to clear session cache.
- Deliver fallback/corruption warnings as inline structured warning fields in run responses.

### Claude's Discretion
- Exact shape of minimal cache status payload, as long as hit/miss/reset is clear.
- Exact wording/structure of compatibility reason codes and warning messages.

</decisions>

<specifics>
## Specific Ideas

No specific product references were requested; prioritize predictable, low-friction defaults with explicit override controls.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 24-annotation-sessions*
*Context gathered: 2026-02-06*
