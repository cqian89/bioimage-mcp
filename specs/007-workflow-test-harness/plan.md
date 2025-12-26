# Implementation Plan: Axis Manipulation Tools, LLM Guidance Hints & Workflow Test Harness

**Branch**: `007-workflow-test-harness` | **Date**: 2025-12-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-workflow-test-harness/spec.md`

## Summary

This plan addresses four P0-P2 priorities from the project roadmap:

1. **Axis Manipulation Tools (P0)**: 5 functions (`relabel_axes`, `squeeze`, `expand_dims`, `moveaxis`, `swap_axes`) to enable FLIM phasor workflows where time bins are stored in non-standard axes.

2. **Automated MCP Workflow Test Harness (P0)**: `MCPTestClient` class + pytest fixtures enabling developers to test multi-step MCP tool sequences without manual testing.

3. **LLM Guidance Hints (P1)**: Structured hints in `describe_function` responses (input requirements, `expected_axes`, `preprocessing_hint`) and tool responses (`next_steps`, `diagnosis`, `suggested_fix`).

4. **Rich Artifact Metadata (P2)**: Enhanced `metadata` in artifact references (shape, dtype, axes, `axes_inferred`, physical_pixel_sizes).

## Technical Context

**Language/Version**: Python 3.13 (core server); Python 3.13 (base tool env)  
**Primary Dependencies**: MCP Python SDK (`mcp>=1.25.0`), `pydantic>=2.0`, `bioio`, `numpy`, `pytest`, `pytest-asyncio`, `pyyaml`  
**Storage**: Local filesystem artifact store + SQLite index (MVP)  
**Testing**: `pytest` with `pytest-asyncio` for async tests  
**Target Platform**: Linux-first (macOS/Windows best-effort); subprocess isolation  
**Project Type**: Python service + CLI + test harness  
**Performance Goals**: Axis tools <1s for 100MB images; workflow tests <10s mock / <60s real  
**Constraints**: No large binary payloads in MCP; artifact references only; TDD required  
**Scale/Scope**: 5 new axis tools + MCPTestClient + hints schema + artifact metadata extension

### Key Technical Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Axis tool location | `tools/base/bioimage_mcp_base/axis_ops.py` | Follows existing transform pattern in `transforms.py` |
| Test harness location | `tests/integration/mcp_test_client.py` | Reusable fixture for workflow tests |
| YAML test cases | `tests/integration/workflow_cases/*.yaml` | Data-driven testing without Python code |
| Hints in manifest | `functions[].hints` field in `manifest.yaml` | Source of truth for per-function hints |
| Artifact metadata | Extended `ArtifactRef.metadata` dict | Backward-compatible additive schema extension |

### Research Questions (Resolved)

These items are resolved by the spec clarifications and design artifacts in this feature directory; there are no open research blockers:

1. Atomic axis relabeling with overlapping keys/values (e.g., `{"Z":"T","T":"Z"}`): mapping is applied atomically (simultaneous rename).
2. Physical size metadata preservation: reorder/remove `physical_pixel_sizes` alongside axis operations; new axes default to `None`.
3. Mock executor boundary: mock at the tool execution boundary so orchestration can be validated without tool envs installed.
4. YAML workflow test case schema: defined in `specs/007-workflow-test-harness/contracts/workflow-testcase.yaml`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Stable MCP surface: No changes to MCP endpoints or pagination. Axis tools use existing `list_tools`, `search_functions`, `describe_function`, `call_tool` APIs. Hints are additions to existing response schemas.
- [x] Summary-first responses: Axis tool schemas fetched on-demand via `describe_function(fn_id)`. Hints included in responses don't expand MCP surface.
- [x] Tool execution isolated: Axis tools run in `bioimage-mcp-base` environment via subprocess. Test harness mocks isolate from external dependencies.
- [x] Artifact references only: All axis tool I/O uses `BioImageRef` typed references. No arrays in MCP messages.
- [x] Reproducibility: Axis tool params recorded in run records. Test harness includes `replay_workflow` test. Axis ops are deterministic.
- [x] Safety + debuggability: Minimum 2 tests per axis tool (10 total). Test harness structured error reporting. All tools validate params before execution.
- [x] TDD: Contract tests written before axis tool implementation. MCPTestClient tests before implementation.

**Constitution Compliance Summary**: All six principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/007-workflow-test-harness/
├── plan.md              # This file
├── research.md          # Phase 0 output - technical research findings
├── data-model.md        # Phase 1 output - entity models
├── quickstart.md        # Phase 1 output - validation commands
├── contracts/           # Phase 1 output - API contracts
│   ├── axis-tools-schema.yaml      # JSON Schema for axis tool params
│   ├── hints-schema.yaml           # Schema for LLM guidance hints
│   └── workflow-testcase.yaml      # Schema for YAML test cases
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Core server additions
src/bioimage_mcp/
├── api/
│   └── discovery.py            # Modified: add hints to describe_function response
│   └── tools.py                # Modified: add hints to call_tool response
└── artifacts/
    └── models.py               # Modified: extend metadata schema

# Base toolkit additions
tools/base/
├── bioimage_mcp_base/
│   └── axis_ops.py             # NEW: relabel_axes, squeeze, expand_dims, moveaxis, swap_axes
└── manifest.yaml               # Modified: add axis tool definitions + hints

# Test harness
tests/
├── integration/
│   ├── mcp_test_client.py      # NEW: MCPTestClient class
│   ├── test_workflows.py       # NEW: workflow tests
│   ├── workflow_cases/         # NEW: YAML test case definitions
│   │   ├── flim_phasor.yaml
│   │   └── axis_manipulation.yaml
│   └── conftest.py             # Modified: add mcp_test_client, mock_executor fixtures
├── contract/
│   ├── test_axis_tools_schema.py   # NEW: schema validation tests
│   └── test_hints_schema.py        # NEW: hints schema validation
└── unit/
    └── base/
        └── test_axis_ops.py        # NEW: axis operation unit tests
```

**Structure Decision**: Single project structure (Option 1) - all additions are within existing `src/`, `tools/`, and `tests/` directories.

## Complexity Tracking

No Constitution violations requiring justification. All new functionality fits within existing architectural patterns.

## Constitution Check (Post-Design Re-evaluation)

*Re-check after Phase 1 design to confirm no new violations.*

All principles remain satisfied after design phase:

| Principle | Pre-Design | Post-Design | Notes |
|-----------|------------|-------------|-------|
| I. Stable MCP Surface | Pass | Pass | No new endpoints. Axis tools use existing discovery/execution APIs. Hints extend existing response schemas. |
| II. Isolated Tool Execution | Pass | Pass | Axis tools run in bioimage-mcp-base env. Mock executor allows testing without tool envs. |
| III. Artifact References Only | Pass | Pass | All axis I/O uses BioImageRef. Extended metadata stays within ArtifactRef.metadata dict. |
| IV. Reproducibility | Pass | Pass | Atomic axis string mapping is deterministic. Physical size preservation documented. |
| V. Safety & Observability | Pass | Pass | 10+ tests required. Error codes defined in contracts/axis-tools-schema.yaml. |
| VI. TDD | Pass | Pass | Contract tests specified in quickstart.md before implementation. |

**Research Resolutions**:
1. Atomic axis relabeling: Single-pass string substitution (see research.md)
2. Physical size preservation: Explicit PhysicalPixelSizes reconstruction (see research.md)
3. Mock executor: Mock at `execute_step` function level (see research.md)
4. YAML test schema: Step-based with `{step_id.output}` references (see contracts/workflow-testcase.yaml)

**No new violations introduced during design phase.**
