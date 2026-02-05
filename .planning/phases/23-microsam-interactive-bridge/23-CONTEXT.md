# Phase 23: µSAM Interactive Bridge - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable launching `micro_sam` napari annotators from MCP with pre-loaded image artifacts and embeddings.

This phase defines the interactive bridge behavior only. It does not add new annotation capabilities beyond what upstream `micro_sam.sam_annotator` already supports.

</domain>

<decisions>
## Implementation Decisions

### Annotator entry flow
- Expose all available upstream annotator modes (no curated subset).
- Callers select annotator by calling the respective API function directly (for example, `micro_sam.sam_annotator.annotator_2d`) rather than through a separate mode switch.
- Initial UI behavior is owned by upstream `micro_sam` annotator functions; Phase 23 does not add custom startup UX layers.
- Per-launch image/session cardinality follows each upstream annotator function's native support.

### Startup data contract
- Required launch inputs are mode/function dependent; no single global required-input rule is imposed.
- Missing-embedding behavior is mode/function dependent and follows upstream behavior.
- Dimension/channel normalization is not added at this layer; inputs are passed through and behavior defers to `micro_sam`.
- Optional startup hints (prompts, labels, init masks) are exposed via each annotator function's native parameter surface.

### Session outputs
- Immediate `run()` return should follow function-native return semantics.
- Primary output artifact is segmentation labels.
- Persist outputs at both checkpoints: explicit save actions and final save-on-close (when available).
- If the session closes with no annotation changes, return completion/no-change status and do not create an output artifact.

### Failure UX
- Non-GUI launch attempts (no display) must fail with clear, actionable remediation guidance.
- Invalid or missing artifact refs should produce precise, field-level validation errors with expected artifact type details.
- Missing mode-specific inputs follow function-native behavior.
- Recoverable conditions (for example, embedding recompute needed) should be surfaced as structured warnings.

### Claude's Discretion
- Exact structure and naming of structured warnings, as long as warnings remain machine-readable.
- Concrete wording style for actionable errors, while preserving the required detail level.

</decisions>

<specifics>
## Specific Ideas

- Keep MCP invocation aligned with upstream annotator function names so callers can target specific entrypoints directly.
- Keep bridge behavior thin: pass through to upstream `micro_sam` annotator expectations unless explicit phase decisions override.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 23-microsam-interactive-bridge*
*Context gathered: 2026-02-05*
