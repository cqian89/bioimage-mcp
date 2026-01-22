# Phase 4: Reproducibility - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can record analysis sessions and replay them later. Session recording and export are already implemented (REPR-01 complete). This phase focuses on making replay production-ready with proper validation, error handling, and user feedback.

</domain>

<decisions>
## Implementation Decisions

### Replay validation
- Version mismatches: Warn about differences but allow replay to proceed
- Missing inputs: Prompt user interactively to provide replacement paths
- Missing environments: Offer to auto-install the missing environment
- Validation timing: Validate each step just before it runs (not all upfront)

### Replay error handling
- Step failure: Fail fast - stop immediately and report which step failed
- Partial outputs: Keep artifacts from successful steps for debugging
- Resume capability: Allow resuming from the failed step with a resume mechanism. Allow modifying parameters on resume attempt.
- Error reporting: Both formats - structured error report internally, human-readable summary shown to user

### Override behavior
- Override method: Via arguments to the `session_replay` MCP interface (not CLI flags or files)
- Override scope: Full parameter override - allow overriding any step's parameters, not just top-level inputs
- Recording: Record overrides - replays with overrides create a new session for reproducibility
- Override validation: Validate overrides against tool schemas before replay starts

### Replay output & feedback
- Progress: Step-by-step progress as each step completes
- Comparison: No comparison to original run outputs - just report success/failure
- Final response: Summary with artifact references
- Artifact references: New unique artifact refs (replay creates new outputs, not versioned refs)
- Timing: Not included in output
- Provenance: Include original workflow metadata in replay output
- Tool messages: Surface tool-level warnings/info messages from each step
- Dry-run: Support dry-run mode that validates workflow without executing

### OpenCode's Discretion
- Exact format of step progress messages
- Resume state persistence mechanism
- Structured error report schema
- Dry-run output format

</decisions>

<specifics>
## Specific Ideas

- Replay should feel like re-running a pipeline - predictable and debuggable
- Interactive prompts for missing inputs keep the workflow usable even when paths change
- The MCP interface (not CLI) is the primary replay surface - this is for AI agents

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 04-reproducibility*
*Context gathered: 2026-01-22*
