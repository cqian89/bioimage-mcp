# Phase 1: Core Runtime - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

System reliably spawns and manages persistent worker processes in isolated Conda environments. Covers process lifecycle, IPC protocol, and GPU detection. This is infrastructure that enables tool execution — not user-facing features.

</domain>

<decisions>
## Implementation Decisions

### MPS Detection Behavior
- Probe for GPU availability at server startup (not lazy)
- Use system commands (e.g., `system_profiler`, `sysctl`) to detect Apple Silicon — avoid PyTorch dependency in core server
- Display MPS alongside CUDA in a unified "GPU" section in `doctor` output
- Surface detailed hardware info to MCP clients: GPU model, driver version, memory where detectable

### GPU Unavailable Handling
- When tool requests GPU but none available: warn and fallback to CPU (not hard fail)
- Surface fallback warning both in logs (stderr) AND in run result metadata
- Per-tool manifest declares GPU requirement level: "required" (fail without) vs "preferred" (fallback OK)
- Run result status is normal success when fallback occurs — warning is separate, not a "degraded" status

### Worker Restart Policy
- Auto-restart workers on crash
- 3 restart attempts before reporting permanent failure
- Idle workers shut down after 30 minutes of inactivity
- Workers respawn on next tool request after idle shutdown

### Environment Validation Strictness
- Lenient: warn on validation issues, proceed with execution
- Only block on hard errors (missing environment, import failures)
- Validation runs once at server startup (not before each run)
- Allow bypass via `--force` flag or config for debugging scenarios
- Detailed diagnostics in failure messages: show specific broken packages/imports

### OpenCode's Discretion
- Exact system commands for MPS detection
- Backoff strategy between restart attempts
- How to detect "idle" (no pending requests vs no active execution)
- Specific error codes for validation failures

</decisions>

<specifics>
## Specific Ideas

- GPU section in doctor should feel unified — not "CUDA section" then "MPS section" but one "GPU" section showing what's available
- 30-minute idle timeout chosen to balance resource usage vs startup latency for infrequent tool use

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-core-runtime*
*Context gathered: 2026-01-22*
