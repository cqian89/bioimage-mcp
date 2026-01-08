# Implementation Plan: Live Server Smoke Tests

**Branch**: `018-live-server-smoke-tests` | **Date**: 2026-01-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-live-server-smoke-tests/spec.md`

## Summary

This feature introduces a **Live Server Smoke Test Framework** that addresses the gap where unit/integration tests pass but live agent-MCP interactions encounter blocking bugs. The framework spawns a real MCP server subprocess, connects via stdio transport using the MCP Python SDK's client API, and executes representative workflows against actual datasets. All interactions are logged for debugging and reproducibility.

## Technical Context

**Language/Version**: Python 3.13 (core server; tool envs may differ)  
**Primary Dependencies**: 
- `mcp` (MCP Python SDK with `ClientSession`, `StdioServerParameters`, `stdio_client`)
- `pytest`, `pytest-asyncio>=0.23` (async test fixtures)
- `pydantic>=2` (interaction log and config models)
- Existing project dependencies from `pyproject.toml`

**Storage**: Interaction logs stored as JSON artifacts under `.bioimage-mcp/smoke_logs/` (pass or fail)  
**Testing**: `pytest` with `tests/smoke/` directory and custom markers (`smoke_minimal`, `smoke_full`, `requires_env`)  
**Target Platform**: CI runs on Linux by default; local development is best-effort on macOS/Windows (documented skips where subprocess/conda behavior differs).  
**Project Type**: Test infrastructure addition (no changes to core server)  
**Performance Goals**: 
- Server startup within 30 seconds (FR-008, SC-002)
- Minimal suite under 2 minutes (SC-001)
- Individual scenarios under 5 minutes (SC-003)
- Interaction logs under 10 MB (FR-007, SC-004)

**Constraints**: 
- Must use real stdio transport, not mocked service calls
- Must handle async subprocess lifecycle with proper cleanup
- Must skip scenarios when optional tool environments are missing
- No changes to the MCP API surface (Constitution I)

**Scale/Scope**: 
- 2 core smoke scenarios (FLIM phasor, Cellpose pipeline)
- Extensible scenario framework for future additions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Stable MCP surface**: No new/changed endpoints. Smoke tests exercise the existing 8-tool surface (list, describe, search, run, status, artifact_info, session_export, session_replay). Any deviation detected is a test failure.
- [x] **Summary-first responses**: Smoke tests validate that `list()` returns summaries and full schemas are fetched via `describe()`.
- [x] **Tool execution isolated**: Smoke tests verify subprocess isolation by running a real server (`bioimage-mcp serve --stdio`), which dispatches to real tool subprocesses. Crashes are detected and logged, not propagated to the test runner.
- [x] **Artifact references only**: Tests validate that all I/O uses artifact references with non-empty identifiers and usable locations (FR-005).
- [x] **Reproducibility**: Interaction logs provide complete audit trail (timestamps, request/response, durations) for reproducing failures (FR-006, FR-007).
- [x] **Safety + debuggability**: Full logging of server stderr, structured interaction logs, tests added (FR-009, Constitution VI).

(Reference: `.specify/memory/constitution.md`)

## Project Structure

### Documentation (this feature)

```text
specs/018-live-server-smoke-tests/
├── plan.md              # This file
├── research.md          # Phase 0 output: MCP client patterns, pytest-asyncio practices
├── data-model.md        # Phase 1 output: InteractionLog, SmokeScenario models
├── quickstart.md        # Phase 1 output: How to run smoke tests
├── contracts/           # Phase 1 output: N/A (no new API contracts, internal test infra)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
tests/smoke/                    # NEW: Smoke test directory
├── __init__.py
├── conftest.py                 # live_server fixture, session management, markers
├── test_flim_phasor_live.py    # Scenario 1: FLIM phasor workflow
├── test_cellpose_pipeline_live.py  # Scenario 2: Cellpose segmentation
└── utils/
    ├── __init__.py
    ├── mcp_client.py           # TestMCPClient wrapper for stdio transport
    └── interaction_logger.py   # Structured JSON logging

pytest.ini                      # MODIFIED: Add smoke test markers
pyproject.toml                  # MODIFIED: Add smoke test dependencies (if needed)
```

**Structure Decision**: Single project structure, adding `tests/smoke/` as a new test tier alongside existing `tests/unit/`, `tests/contract/`, and `tests/integration/`.

## Complexity Tracking

> No Constitution Check violations. The feature is additive test infrastructure with no MCP API changes.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A       | N/A        | N/A                                 |

---

## Post-Design Constitution Re-Evaluation

*Re-checked after Phase 1 design completion.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Stable MCP Surface** | ✅ PASS | No new MCP tools. Smoke tests exercise existing 8-tool surface. Any API change would cause test failures. |
| **II. Isolated Tool Execution** | ✅ PASS | Tests spawn real server subprocess, which spawns real tool subprocesses. Isolation is tested, not bypassed. |
| **III. Artifact References Only** | ✅ PASS | Tests validate outputs are `BioImageRef`/`LabelImageRef` with valid `ref_id` and `uri`. No embedded data. |
| **IV. Reproducibility & Provenance** | ✅ PASS | `InteractionLog` captures full request/response sequence with timestamps. Logs are saved as JSON artifacts. |
| **V. Safety & Observability** | ✅ PASS | Server stderr captured. Structured logs persisted. Tests added for new infrastructure. |
| **VI. Test-Driven Development** | ✅ PASS | This is test infrastructure. Implementation will follow TDD for the test utilities themselves. |
| **VII. Early Development Policy** | ✅ PASS | No breaking changes. Additive test infrastructure only. |

**Conclusion**: All constitution principles satisfied. No violations or exceptions required.

---

## Generated Artifacts Summary

| Artifact | Path | Description |
|----------|------|-------------|
| Implementation Plan | `specs/018-live-server-smoke-tests/plan.md` | This file |
| Research | `specs/018-live-server-smoke-tests/research.md` | MCP client patterns, pytest-asyncio practices |
| Data Model | `specs/018-live-server-smoke-tests/data-model.md` | InteractionLog, SmokeScenario models |
| Contracts | `specs/018-live-server-smoke-tests/contracts/` | N/A (no new API, README explains) |
| Quickstart | `specs/018-live-server-smoke-tests/quickstart.md` | How to run smoke tests |
| Spec | `specs/018-live-server-smoke-tests/spec.md` | Original feature specification |
| Proposal | `specs/018-live-server-smoke-tests/proposal.md` | Detailed proposal document |

---

## Next Steps

Phase 2 (`/speckit.tasks`) will generate `tasks.md` with implementation tasks:

1. Create `tests/smoke/` directory structure
2. Implement `TestMCPClient` wrapper (TDD: write failing tests first)
3. Implement `InteractionLogger` utility (TDD)
4. Create `live_server` pytest fixture
5. Implement FLIM phasor smoke scenario
6. Implement Cellpose pipeline smoke scenario
7. Add pytest markers and configuration
8. Update `pytest.ini` with smoke test markers
9. Update AGENTS.md with smoke test documentation
