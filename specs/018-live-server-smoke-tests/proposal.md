# Feature Specification: Live Server Smoke Tests

**Feature Branch**: `018-live-server-smoke-tests`  
**Created**: 2026-01-08  
**Status**: Draft  
**Input**: Address the gap where unit/integration tests pass but live agent-MCP interactions encounter blocking bugs.

## Executive Summary

Despite comprehensive unit, contract, and integration tests passing, real-world agent interactions with the bioimage-mcp server frequently encounter blocking bugs. These bugs arise from subtle differences between test mocks and actual server behavior, race conditions in subprocess execution, serialization edge cases, and MCP protocol nuances that only manifest in true client-server communication.

This specification introduces a **Live Server Smoke Test Framework** that:

1. **Starts a Fresh MCP Server Instance**: Spawns a real server process using stdio transport, exactly as an LLM client would connect.
2. **Simulates LLM Interactions**: Sends real MCP protocol messages (list, search, describe, run) through the stdio interface without any mocking.
3. **Uses Real Datasets**: Executes workflows against actual files in `datasets/*` subfolders, not synthetic test data.
4. **Records Full Interaction Logs**: Captures all requests and responses for debugging, creating an audit trail of exactly what the server received and returned.
5. **Runs After Code Changes**: Integrates into CI/CD as a mandatory gate, catching regressions that slip through faster unit tests.

## Current State Analysis

### Existing Test Infrastructure

The project has three test tiers:

| Tier | Location | What It Tests | Limitation |
|------|----------|---------------|------------|
| Unit | `tests/unit/` | Individual functions, schemas, utilities | No subprocess execution, no real I/O |
| Contract | `tests/contract/` | Schema validation, manifest parsing | No actual tool execution |
| Integration | `tests/integration/` | Multi-step workflows, cross-env handoff | Uses service classes directly, not MCP protocol |

### The MCPTestClient Gap

Spec 007 introduced `MCPTestClient` for workflow testing, but it:
- Calls service methods directly (`DiscoveryService`, `ExecutionService`)
- Often uses `monkeypatch` to mock `execute_step`
- Does not exercise the MCP protocol layer (`FastMCP`, stdio transport)
- Does not start a real server subprocess

### Observed Failure Patterns

Recent debugging sessions have revealed bugs that passed all tests:

1. **Serialization mismatches**: Pydantic models serialized differently via MCP than via direct method calls
2. **Session ID handling**: `get_session_identifier()` behaves differently with real `ServerSession` vs test mocks
3. **Artifact URI resolution**: File paths work in tests but fail when server runs in different working directory
4. **Parameter validation edge cases**: Empty `params={}` vs omitted `params` field causes validation errors in runtime
5. **Background execution timing**: `status()` polling returns unexpected states due to subprocess timing

## Gap Analysis

| What We Test | What We Don't Test | Risk |
|--------------|-------------------|------|
| Schema correctness | MCP message serialization | Protocol bugs |
| Service layer logic | stdio transport handling | Communication bugs |
| Mock subprocess results | Real subprocess execution | Runtime crashes |
| Isolated function calls | Full session lifecycle | State management bugs |
| Synthetic test images | Real dataset loading | Format/metadata bugs |

## Proposed Architecture

### 1. Live Server Test Runner

A pytest plugin/fixture that:
1. Spawns `python -m bioimage_mcp serve --stdio` as a subprocess
2. Connects to the server's stdin/stdout using MCP client SDK
3. Executes test scenarios by sending real MCP tool calls
4. Captures all communication for logging
5. Gracefully shuts down the server after tests

```python
@pytest.fixture
async def live_server():
    """Spawn a real MCP server and connect to it."""
    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "bioimage_mcp", "serve", "--stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    client = MCPClient(proc.stdin, proc.stdout)
    await client.initialize()
    
    yield client
    
    await client.close()
    proc.terminate()
    await proc.wait()
```

### 2. Interaction Logger

Every request and response is logged to a structured JSON file:

```json
{
  "test_run_id": "smoke_2026-01-08_143022",
  "interactions": [
    {
      "timestamp": "2026-01-08T14:30:23.456Z",
      "direction": "request",
      "tool": "list",
      "params": {"path": null, "limit": 50},
      "raw_message": "{...}"
    },
    {
      "timestamp": "2026-01-08T14:30:23.789Z",
      "direction": "response",
      "tool": "list",
      "result": {"items": [...], "cursor": null},
      "raw_message": "{...}",
      "duration_ms": 333
    }
  ]
}
```

### 3. Smoke Test Scenarios

#### Scenario 1: FLIM Phasor Analysis (Priority: P0)

**Dataset**: `datasets/FLUTE_FLIM_data_tif/hMSC control.tif`

**Steps**:
1. `list()` - Verify server returns environments
2. `search(query="phasor")` - Find phasor functions
3. `describe(fn_id="base.phasorpy.phasor.phasor_from_signal")` - Get full schema
4. `run(fn_id="base.io.bioimage.read", inputs={...})` - Load the FLIM image
5. `run(fn_id="base.phasorpy.phasor.phasor_from_signal", ...)` - Compute phasors with Z as time axis (axis=2, or "Z" axis name if using named axis param)

**Assertions**:
- All calls return `status: "success"` or valid response
- Output artifacts have valid `ref_id` and `uri`
- No error messages in server stderr

#### Scenario 2: Intensity Projection + Cellpose (Priority: P0)

**Dataset**: `datasets/FLUTE_FLIM_data_tif/hMSC control.tif` (same source)

**Steps** (parallel branch from load):
1. Load image (same as Scenario 1 step 4)
2. `run(fn_id="base.xarray.sum", inputs={...}, params={"dim": "Z"})` - Sum projection
3. `run(fn_id="base.io.bioimage.export", ...)` - Convert to OME-TIFF for Cellpose compatibility
4. `run(fn_id="cellpose.denoise.DenoiseModel.eval", ...)` - Denoise the sum projection
5. `run(fn_id="cellpose.models.CellposeModel.eval", ...)` - Segment cells

**Assertions**:
- Sum projection reduces Z dimension to 1
- Cellpose returns `LabelImageRef` output
- Workflow completes without subprocess crashes

### 4. Test Execution Modes

| Mode | When | Environments Required |
|------|------|----------------------|
| `--smoke-minimal` | Every commit (CI) | bioimage-mcp-base only |
| `--smoke-full` | PR merge, release | All tool environments |
| `--smoke-record` | Debugging | Any, writes verbose logs |

### 5. Log Storage

Interaction logs are stored as artifacts:
- **CI**: Uploaded as GitHub Actions artifacts
- **Local**: Written to `.bioimage-mcp/smoke_logs/`
- **Format**: JSON with optional NDJSON streaming for large runs

## User Scenarios & Testing

### User Story 1: Developer Catches Protocol Bug Before Merge (Priority: P0)

**Given** a developer modifies `src/bioimage_mcp/api/server.py`,
**When** they run `pytest tests/smoke/ -v`,
**Then** the smoke tests spawn a real server and catch any MCP protocol regressions that unit tests missed.

### User Story 2: CI Blocks Broken Commits (Priority: P0)

**Given** a PR that breaks artifact serialization,
**When** CI runs the smoke test suite,
**Then** the PR is blocked with a clear failure showing the exact request/response that failed.

### User Story 3: Debugging Production Issues (Priority: P1)

**Given** a user reports "function X fails in Claude Desktop",
**When** developer runs `pytest tests/smoke/test_scenario_X.py --smoke-record`,
**Then** the full interaction log is saved for comparison with the user's failure.

### User Story 4: Regression Prevention (Priority: P1)

**Given** a bug is fixed,
**When** developer adds a new smoke test case covering that scenario,
**Then** the bug cannot regress without failing the smoke test.

## Edge Cases

### Server Startup Failures
- **Scenario**: Server fails to start (missing dependency, port conflict)
- **Handling**: Test fails fast with server stderr captured in log
- **Timeout**: 30 seconds for server initialization

### Subprocess Crashes
- **Scenario**: Tool subprocess crashes during `run()`
- **Handling**: `status()` returns error, smoke test captures crash details
- **Assertion**: Test fails but logs are preserved

### Missing Tool Environments
- **Scenario**: `bioimage-mcp-cellpose` not installed
- **Handling**: Skip cellpose scenarios with `pytest.mark.requires_env`
- **Minimal mode**: Only tests requiring `bioimage-mcp-base`

## Requirements

### Constitution Constraints

#### 1. Stable MCP Surface
**Compliance**: Smoke tests exercise the exact MCP surface that LLM clients use. Any deviation is a test failure.

#### 2. Isolated Tool Execution
**Compliance**: Smoke tests verify subprocess isolation by running real tool subprocesses. Crashes are detected and logged.

#### 3. Artifact References Only
**Compliance**: Tests validate that all I/O uses artifact references, never embedded data.

#### 4. Reproducibility & Provenance
**Compliance**: Interaction logs provide complete audit trail for reproducing failures.

#### 5. Safety & Observability
**Compliance**: Full logging of server stderr, request/response pairs, and timing.

#### 6. Test-Driven Development
**Compliance**: Smoke tests are written for known failure patterns before implementing fixes.

### Functional Requirements

- **FR-001**: System MUST provide a pytest fixture that spawns a real MCP server subprocess
- **FR-002**: System MUST connect to the server using MCP client SDK over stdio transport
- **FR-003**: System MUST log all requests and responses to a structured JSON file
- **FR-004**: System MUST support `--smoke-minimal` mode requiring only base environment
- **FR-005**: System MUST support `--smoke-full` mode requiring all tool environments
- **FR-006**: System MUST include smoke test for FLIM phasor workflow with real dataset
- **FR-007**: System MUST include smoke test for sum projection + Cellpose workflow
- **FR-008**: System MUST fail fast if server subprocess crashes, capturing stderr
- **FR-009**: System MUST support `pytest.mark.requires_env("env-name")` for conditional skip
- **FR-010**: Interaction logs MUST include: timestamp, direction, tool name, params, result, duration_ms

### Non-Functional Requirements

- **NFR-001**: Server startup MUST complete within 30 seconds
- **NFR-002**: Individual smoke test scenarios MUST complete within 5 minutes
- **NFR-003**: `--smoke-minimal` suite MUST complete within 2 minutes for CI integration
- **NFR-004**: Interaction logs MUST be under 10MB per test run (truncate large payloads)

## Implementation Plan

### Phase 1: Infrastructure (0.18.1)

1. Create `tests/smoke/` directory structure
2. Implement `live_server` pytest fixture with subprocess management
3. Implement `InteractionLogger` for request/response capture
4. Add `conftest.py` with session-scoped server fixture

### Phase 2: Core Scenarios (0.18.2)

1. Implement FLIM phasor smoke test (`test_flim_phasor_live.py`)
2. Implement sum projection + Cellpose smoke test (`test_cellpose_pipeline_live.py`)
3. Add `--smoke-minimal` and `--smoke-full` pytest markers

### Phase 3: CI Integration (0.18.3)

1. Add GitHub Actions workflow for smoke tests
2. Configure artifact upload for interaction logs
3. Add smoke test as required status check for PRs

## File Changes

### New Files

```
tests/smoke/
  __init__.py
  conftest.py              # live_server fixture, InteractionLogger
  test_flim_phasor_live.py # FLIM phasor scenario
  test_cellpose_pipeline_live.py  # Cellpose scenario
  utils/
    __init__.py
    mcp_client.py          # Async MCP client wrapper for stdio
    interaction_logger.py  # JSON logging utility
```

### Modified Files

```
pytest.ini                 # Add smoke test markers
.github/workflows/ci.yml   # Add smoke test job (if exists)
pyproject.toml             # Add smoke test dependencies (mcp client SDK)
```

## Success Criteria

- **SC-001**: `pytest tests/smoke/ --smoke-minimal` passes on fresh server with base environment only
- **SC-002**: `pytest tests/smoke/ --smoke-full` passes with all tool environments installed
- **SC-003**: Smoke tests catch at least one bug that unit/integration tests miss (validated by intentionally breaking server code)
- **SC-004**: Interaction logs contain all fields: timestamp, direction, tool, params, result, duration_ms
- **SC-005**: Server subprocess crashes are detected and logged (test by killing subprocess mid-execution)
- **SC-006**: CI runs `--smoke-minimal` in under 2 minutes
- **SC-007**: FLIM phasor workflow completes successfully on `hMSC control.tif`
- **SC-008**: Cellpose workflow completes successfully on sum projection of `hMSC control.tif`

## Migration Notes

- No breaking changes to existing APIs
- New test infrastructure is additive
- Existing unit/integration tests remain unchanged

## Dependencies

### Prerequisites
- MCP Python SDK with client support (`mcp` package)
- `asyncio` subprocess management
- Existing tool environments (base required, cellpose optional)

### Test Data
- `datasets/FLUTE_FLIM_data_tif/hMSC control.tif` (required)
- `datasets/FLUTE_FLIM_data_tif/Fluorescein_hMSC.tif` (required, phasor reference for calibration)

## Out of Scope

1. **Visual regression testing**: Comparing output images pixel-by-pixel
2. **Performance benchmarking**: Tracking execution time trends
3. **Fuzzing**: Random input generation for stress testing
4. **Multi-client testing**: Concurrent connections to same server
5. **Network transport**: SSE/WebSocket testing (stdio only for MVP)

---

This proposal establishes the foundation for catching "works in tests, breaks in production" bugs by testing the actual server-client interaction path that LLM agents use.