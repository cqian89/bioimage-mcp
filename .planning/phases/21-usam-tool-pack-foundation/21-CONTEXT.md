# Phase 21: µSAM Tool Pack Foundation - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the isolated environment and prerequisite models for µSAM so the µSAM tool pack is installed and ready for local inference.

</domain>

<decisions>
## Implementation Decisions

### Install command behavior
- `bioimage-mcp install microsam` defaults to `--profile cpu`.
- Supported profiles are `cpu` and `gpu` only.
- `--profile gpu` semantics:
  - Linux: installs GPU-capable stack (CUDA where available).
  - macOS (Apple Silicon): installs MPS-capable stack.
  - macOS (Intel): warn and fall back to `--profile cpu`.
- Install runs in repair mode by default (re-run steps even if already installed) to ensure correctness.
- On success, print a single-line confirmation that includes the stable conda env name (`bioimage-mcp-microsam`) and the resolved model cache location.
- Keep Phase 21 CLI surface minimal (no new advanced flags beyond `--profile` and existing global flags).

### Model download + cache
- Required model sets are present after a successful install: LM, EM, and Generalist.
- Store models in the micro-sam default cache directory (do not introduce a separate bioimage-mcp cache for these).
- Model download policy is pinned/consistent: re-download only if missing or corrupt; do not auto-update opportunistically.
- If required models cannot be ensured (network/403/checksum/etc.), `bioimage-mcp install microsam ...` exits non-zero and prints an actionable error including cache path + next steps.

### Device selection + overrides
- Default automatic selection order is `cuda` > `mps` > `cpu`.
- Device override is via bioimage-mcp config file (not per-tool params).
- Config key: `microsam.device` with allowed values `auto|cuda|mps|cpu`.
- If a forced device is unavailable, error (no fallback).
- Selected device is only reported in debug/verbose logs (not normal tool output).

### Platform support + verification
- Phase 21 support target (roadmap-gated): Linux and macOS.
- Windows behavior in Phase 21: best-effort attempt is allowed, but it is not supported/gated; failures should recommend WSL2/Linux/macOS.
- Verification surface:
  - `bioimage-mcp doctor` verifies µSAM env presence + required model presence (no deep import/device checks).
  - `bioimage-mcp install microsam ...` runs a quick sanity check (imports + required model presence) before printing success.
- Failure UX: actionable CLI errors with paths + 2-3 concrete fixes; include env name and model cache path.

### Claude's Discretion
- Exact wording/formatting of install/doctor output.
- Exact mechanism for enabling debug/verbose logs.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

- Minimal install mode that downloads only the Generalist model set.
- Offline/airgapped-friendly install mode that allows env install without model downloads (likely behind an explicit flag).
- Official native Windows support + CI validation (beyond best-effort behavior).

</deferred>

---

*Phase: 21-usam-tool-pack-foundation*
*Context gathered: 2026-02-04*
