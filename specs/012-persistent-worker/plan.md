# Implementation Plan: 012-persistent-worker

**Branch**: `012-persistent-worker` | **Date**: 2026-01-01 | **Spec**: [link]
**Input**: Feature specification from `/specs/012-persistent-worker/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.codex/prompts/speckit.plan.md` for the execution workflow.

## Summary
Transition from Phase 1 (one-shot subprocess execution) to Phase 2 (persistent worker subprocesses) with real memory artifacts, delegated materialization, and NDJSON IPC protocol. This addresses Constitution requirements II (Isolated Tool Execution) and III (Artifact References Only) by ensuring Core never performs heavy I/O operations.

## Technical Context (filled in)

**Language/Version**: Python 3.13 (core server); Python 3.10+ (tool envs)  
**Core Dependencies**: MCP Python SDK (`mcp`), `pydantic>=2.0`, `subprocess` (stdlib)  
**Worker/Tool Dependencies**: `bioio`, `numpy`, `scikit-image`  
**Storage**: Local filesystem artifact store + SQLite index (MVP); mem:// in worker process memory  
**Testing**: `pytest`, `pytest-asyncio` for async tests  
**Target Platform**: Cross-platform (Linux-first, macOS/Windows best-effort)  
**Project Type**: Python service + CLI  
**Performance Goals**: Warm-start latency < 20% of cold-start latency; eliminate conda activation overhead for sequential calls  
**Constraints**: No bioio imports in Core; worker crashes must not affect Core stability  
**Scale/Scope**: Max 8 concurrent workers default; 600s operation timeout; idle timeout for auto-cleanup

## Constitution Check (all boxes checked with explanations)

- [x] **Stable MCP surface**: No changes to external MCP endpoints. IPC is internal protocol between Core and workers.
- [x] **Summary-first responses**: No changes to discovery APIs.
- [x] **Tool execution isolated**: Workers run in separate subprocess environments per Constitution II. Core coordinates only.
- [x] **Artifact references only**: All I/O delegated to workers via materialize command. Core passes URIs only (Constitution III).
- [x] **Reproducibility**: Worker version info and artifact provenance recorded. mem:// artifacts explicitly excluded from replay (ephemeral by design).
- [x] **Safety + debuggability**: Structured logs capture worker lifecycle. stderr captured by background thread. TDD with contract tests for IPC protocol.

## Project Structure (updated)

```text
# Documentation (this feature)
specs/012-persistent-worker/
├── plan.md              # This file
├── research.md          # Phase 0 output: technology decisions
├── data-model.md        # Phase 1 output: entity definitions
├── quickstart.md        # Phase 1 output: developer guide
├── contracts/
│   └── worker-ipc.yaml  # IPC protocol schema
├── checklists/
│   └── definition-of-done.md
└── tasks.md             # Phase 2 output (not created by /speckit.plan)

# Source Code (changes)
src/bioimage_mcp/runtimes/
├── persistent.py        # UPDATE: Add real subprocess management
├── executor.py          # UPDATE: Support persistent pipe communication
├── worker_ipc.py        # NEW: NDJSON framing and message types
└── protocol.py          # KEEP: Workflow compatibility types

src/bioimage_mcp/api/
├── execution.py         # UPDATE: Remove bioio imports, delegate to workers
└── artifacts.py         # UPDATE: Support mem:// artifact routing and materialization logic

src/bioimage_mcp/config/
└── schema.py            # UPDATE: Add worker settings (max_workers, timeouts)

tools/base/bioimage_mcp_base/
└── entrypoint.py        # UPDATE: NDJSON loop with shutdown command

tests/
├── contract/
│   └── test_worker_ipc_schema.py  # NEW: IPC message validation
├── integration/
│   ├── test_worker_resilience.py  # UPDATE: Test real subprocess lifecycle
│   └── test_persistent_worker.py  # NEW: PID reuse, latency tests
└── unit/
    └── runtimes/
        └── test_worker_ipc.py     # NEW: NDJSON framing tests
```

**Structure Decision**: Single project (Option 1) - extends existing src/bioimage_mcp structure with new worker_ipc.py module and updates to runtimes/persistent.py.

## Complexity Tracking

No constitution violations requiring justification. All changes align with existing patterns and satisfy Constitution II/III requirements.
