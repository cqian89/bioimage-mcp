# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** Phase 5 - Trackpy Integration

## Overall Progress (100% complete)

- **Phase 1: Core Runtime** (100% complete) - **PHASE COMPLETE**
  - ✅ Conda isolation (`persistent.py`, `executor.py`)
  - ✅ NDJSON IPC (`worker_ipc.py`)
  - ✅ Process lifecycle (`PersistentWorkerManager`)
  - ✅ Unified GPU detection (NVIDIA CUDA + Apple Silicon MPS)

- **Phase 2: Tool Management** (100% complete) - **PHASE COMPLETE**
  - ✅ `doctor` command complete
  - ✅ `install` command refactored and extensible
  - ✅ `list` command implemented
  - ✅ `remove` CLI implemented

- **Phase 3: Data & Artifacts** (100% complete) - **PHASE COMPLETE**
  - ✅ File artifacts fully operational
  - ✅ `mem://` protocol implemented

- **Phase 4: Reproducibility** (100% complete) - **PHASE COMPLETE**
  - ✅ Session recording complete with provenance
  - ✅ `session_export` works
  - ✅ `session_replay` implemented with validation, resume, and error handling

- **Phase 5: Trackpy Integration** (100% complete) - **PHASE COMPLETE**
  - ✅ Environment determination (base vs. separate) (05-01)
  - ✅ Dynamic introspection for function signatures (05-02)
  - ✅ Full API coverage from trackpy v0.7 (05-02)
  - ✅ Test data from trackpy repo/docs (05-03)
  - ✅ Live smoke test matching reference output (05-03)
  - ✅ End-to-end E2E smoke tests (05-06)
  - ✅ Optional readiness checks in `doctor` (05-07)
  - ✅ Fix Trackpy meta.describe schema enrichment (05-08)

## Current Position

Phase: 5 of 5 (Trackpy Integration)
Plan: 8 of 8 in current phase
Status: Phase complete
Last activity: 2026-01-24 - Completed 05-08-PLAN.md (Describe Enrichment)

Progress: ██████████ 100%

**Next:** Milestone transition or archive

## Context & Memory

### Key Decisions
- **Hub-and-Spoke Architecture**: Core server manages persistent worker processes for each tool environment.
- **NDJSON IPC**: Using NDJSON over stdio for reliable, language-agnostic communication.
- **Artifact-based I/O**: Core server handles metadata; tool packs read/write actual data via artifacts. No raw arrays in core.
- **SQLite Registry**: Using SQLite for tool registry and session persistence.
- **Dynamic Tool Discovery**: (Phase 2-02) Tools are discovered from `envs/bioimage-mcp-*.yaml` files, enabling easy addition of new tool packs.
- **Installation Profiles**: (Phase 2-02) Support for `cpu`, `gpu`, and `minimal` profiles to simplify environment setup.
- **Active Worker Safety**: (Phase 2-03) Tool removal is blocked if an active worker process is detected, preventing disruption of running sessions.
- **Base Environment Protection**: (Phase 2-03) The 'base' environment is protected from removal as it contains core server components.
- **Filesystem-over-Database Priority**: (Phase 2-04) The `list` command was refactored to read manifests directly from disk, ensuring consistency with `doctor` and avoiding reliance on a potentially stale SQLite registry.
- **Unified GPU Detection**: (Phase 1-01) Single 'gpu' check reports both CUDA and MPS status using dependency-free system probing.
- **Pre-execution Replay Validation**: (Phase 4-01) Validate parameter overrides against tool schemas before starting replay to fail fast on invalid inputs.
- **Environment & Version Pre-flight**: (Phase 4-02) Verify environment installation and warn about tool version mismatches before session replay, offering auto-install hints.
- **Replay Progress History**: (Phase 4-03) Include a complete step-by-step progress log in the final replay response to provide retrospective observability for AI agents.
- **Dry-run Workflow Preview**: (Phase 4-03) Support dry-run mode that validates all overrides and inputs, returning a 'pending' progress list to show the intended execution plan.
- **Ordinal-based Resume**: (Phase 4-04) Support resuming replays from a specific step, skipping already successful steps and restoring intermediate outputs.
- **Structured Missing Input Hints**: (Phase 4-04) Return structured error details with JSON Pointers for missing external inputs during replay.
- **Human-readable Error Summaries**: (Phase 4-04) Generate formatted error summaries in replay responses to make failures actionable for users and agents.
- **Out-of-process discovery**: (Phase 5-01) Decided to use a specialized `meta.list` command in the worker entrypoint to discover functions, as trackpy cannot be safely imported in the server's Python 3.13 process.
- **Dual-mode Worker Entrypoint**: (Phase 5-01) Entrypoint supports both legacy single-request JSON and persistent-worker NDJSON protocols for backward compatibility and performance.
- **Subprocess Discovery Fallback**: (Phase 5-02) The registry loader now automatically falls back to out-of-process discovery via the tool's entrypoint if the required adapter is missing or if in-process import fails.
- **TableRef for DataFrames**: (Phase 5-02) Trackpy results (features, trajectories) are serialized as CSV files and returned as `TableRef` artifacts to ensure cross-environment portability.
- **Input Name Mapping**: (Phase 5-03) Mapped generic `image` and `table` inputs to trackpy-specific names like `raw_image` or `f` in the worker entrypoint to allow flexible MCP signatures while maintaining library compatibility.
- **URI-to-Path Resolution**: (Phase 5-03) Added robust URI parsing in the worker entrypoint to handle artifacts where the `path` field is missing but `uri` (file://) is present.
- **Tolerance-based Equivalence**: (Phase 5-03) Used 1e-3 relative tolerance for trackpy equivalence tests to handle environment-specific numeric variations.
- **Strict Worker Termination**: (Phase 5-04) Decided to kill worker processes immediately upon any communication error (JSON error, ordinal mismatch, unexpected EOF) to prevent state desync and ensure clean recovery.
- **Robust JSON extraction**: (Phase 5-04) Switched to searching for the first '{' in subprocess output to avoid parsing failures caused by non-JSON warnings during environment discovery.
- **Full Verbosity for E2E**: (Phase 5-06) Used `verbosity='full'` in E2E tests to verify rich metadata (columns, row_count) for `TableRef` artifacts, as default `minimal` verbosity strips these fields.
- **Optional Readiness Checks**: (Phase 5-07) Introduced `required` field to `CheckResult` to allow non-blocking failures (e.g., missing `conda-lock`) to be surfaced as warnings.
- **Worker-Style meta.describe**: (Phase 5-08) Normalized DiscoveryService to send `command: execute` and handle wrapped `outputs.result` responses, ensuring parameter schemas are correctly enriched for worker-based tool packs.

### Blockers
- None.

### Next Steps
- Implement plan 05-08-PLAN.md to fix meta.describe schema enrichment for Trackpy.

### Roadmap Evolution
- Phase 5 added: Trackpy Integration - Integrate trackpy particle tracking library as a tool pack with full API coverage and live smoke tests

## Session Continuity

Last session: 2026-01-24T14:55:00Z
Stopped at: Completed 05-07-PLAN.md
Resume file: None
