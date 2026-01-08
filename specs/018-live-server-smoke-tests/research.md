# Research: Live Server Smoke Tests

**Feature**: 018-live-server-smoke-tests  
**Date**: 2026-01-08  
**Status**: Complete

This document consolidates research findings for implementing the Live Server Smoke Test Framework.

---

## 1. MCP Python SDK Client API

### Decision
Use the official MCP Python SDK's `stdio_client` context manager with `ClientSession` for stdio transport communication.

### Rationale
- The `mcp` package provides production-ready client-side support
- `stdio_client` handles subprocess lifecycle (spawn, pipe management, cleanup)
- `ClientSession` implements the full MCP protocol (initialization, tool calls, etc.)
- This is the same pattern used by real LLM clients (Claude Desktop, Langflow, etc.)

### Alternatives Considered
1. **Raw subprocess + JSON-RPC**: Rejected because MCP protocol has initialization handshake, message framing, and session state that would need reimplementation.
2. **HTTP/SSE transport**: Rejected for MVP because stdio is simpler and matches the current server implementation (`--stdio` only).
3. **Mock MCP client**: Rejected because it defeats the purpose of smoke testing real protocol interactions.

### Key Code Pattern

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="python",
    args=["-m", "bioimage_mcp", "serve", "--stdio"],
    env={"PYTHONPATH": "."}
)

async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()  # REQUIRED: MCP handshake
        
        # Call tools
        result = await session.call_tool("list", arguments={})
        result = await session.call_tool("run", arguments={
            "fn_id": "base.io.bioimage.read",
            "inputs": {"path": "file:///path/to/image.tif"},
            "params": {},
            "session_id": "smoke-test-session"
        })
```

### References
- GitHub: `browser-use/browser-use/browser_use/mcp/client.py` (MIT license)
- GitHub: `langflow-ai/langflow/src/lfx/src/lfx/base/mcp/util.py` (MIT license)
- GitHub: `ed-donner/agents/6_mcp/.../accounts_client.py` (MIT license)

---

## 2. Subprocess Lifecycle Management

### Decision
Use `AsyncExitStack` for robust cleanup of nested async context managers (stdio_client, ClientSession).

### Rationale
- Ensures subprocess termination even if initialization fails partway
- Handles cleanup in reverse order (session close, then subprocess terminate)
- Standard Python pattern for managing multiple async resources

### Alternatives Considered
1. **Manual try/finally**: Rejected because nested async contexts are error-prone.
2. **pytest-asyncio cleanup hooks**: Rejected because `AsyncExitStack` is more explicit and testable.

### Key Code Pattern

```python
from contextlib import AsyncExitStack

class TestMCPClient:
    def __init__(self):
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def start(self):
        read, write = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()

    async def stop(self):
        await self._exit_stack.aclose()  # Cleans up in reverse order
```

---

## 3. pytest-asyncio Fixture Patterns

### Decision
Use `session`-scoped async fixtures for the server process (expensive to start) and `function`-scoped fixtures for per-test isolation where needed.

### Rationale
- Server startup is slow (~5-10 seconds); reusing across tests is essential for CI performance
- MCP sessions can be reused if tests don't have state conflicts
- Function-scoped fixtures provide isolation for tests that modify session state

### Alternatives Considered
1. **Function-scoped server per test**: Rejected because startup overhead would exceed the 2-minute CI target.
2. **Module-scoped fixtures**: Rejected in favor of session-scoped for maximum reuse.

### Key Code Pattern

```python
import pytest_asyncio
from contextlib import AsyncExitStack

@pytest_asyncio.fixture(scope="session")
async def live_server():
    """Session-scoped fixture: one server for all smoke tests."""
    client = TestMCPClient()
    await client.start()
    yield client
    await client.stop()

@pytest_asyncio.fixture
async def smoke_session(live_server):
    """Function-scoped: fresh session state per test (if needed)."""
    session_id = f"smoke-{uuid.uuid4().hex[:8]}"
    yield {"client": live_server, "session_id": session_id}
```

### Compatibility Note
- Requires `pytest-asyncio>=0.23` for proper async fixture handling
- Use `pytest_plugins = ["pytest_asyncio"]` in conftest.py

---

## 4. Server Readiness Detection

### Decision
Use MCP protocol initialization (`session.initialize()`) as the readiness signal.

### Rationale
- The MCP `initialize` request/response handshake confirms the server is ready
- No need for custom health checks or port polling
- If initialization fails or times out, the server is not ready

### Alternatives Considered
1. **Health check endpoint**: Rejected because bioimage-mcp uses stdio, not HTTP.
2. **Sleep-based delay**: Rejected because it's fragile and wastes time.
3. **Polling server stdout for "ready" message**: Rejected because `session.initialize()` is the official protocol mechanism.

### Key Code Pattern

```python
async def start_with_timeout(self, timeout: float = 30.0):
    """Start server and initialize with timeout."""
    try:
        async with asyncio.timeout(timeout):
            await self.start()
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"Server failed to initialize within {timeout}s. "
            "Check server stderr for errors."
        )
```

---

## 5. Interaction Logging

### Decision
Wrap tool calls to capture request/response pairs with timestamps and durations, storing as structured JSON.

### Rationale
- FR-006 requires full interaction logs for debugging
- JSON format is machine-readable and can be uploaded as CI artifacts
- Size bounding (FR-007) achieved by truncating large payloads

### Alternatives Considered
1. **Raw stdio capture**: Rejected because MCP messages are framed and would need parsing anyway.
2. **NDJSON streaming**: Considered for future; JSON is simpler for MVP.
3. **pytest caplog**: Rejected because we need structured data, not text logs.

### Key Code Pattern

```python
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json

@dataclass
class Interaction:
    timestamp: str
    direction: str  # "request" | "response"
    tool: str
    params: dict | None
    result: dict | None
    duration_ms: float | None
    error: str | None = None

class InteractionLogger:
    def __init__(self, max_payload_bytes: int = 10000):
        self.interactions: list[Interaction] = []
        self.max_payload_bytes = max_payload_bytes

    def log_request(self, tool: str, params: dict) -> str:
        """Log request, return correlation ID."""
        entry = Interaction(
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction="request",
            tool=tool,
            params=self._truncate(params),
            result=None,
            duration_ms=None,
        )
        self.interactions.append(entry)
        return str(len(self.interactions) - 1)

    def log_response(self, correlation_id: str, result: dict, duration_ms: float):
        """Log response with timing."""
        entry = Interaction(
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction="response",
            tool=self.interactions[int(correlation_id)].tool,
            params=None,
            result=self._truncate(result),
            duration_ms=duration_ms,
        )
        self.interactions.append(entry)

    def _truncate(self, data: dict) -> dict:
        """Truncate large payloads to stay under size limit."""
        serialized = json.dumps(data, default=str)
        if len(serialized) > self.max_payload_bytes:
            return {"_truncated": True, "_size": len(serialized)}
        return data

    def save(self, path: Path):
        path.write_text(json.dumps(
            {"interactions": [asdict(i) for i in self.interactions]},
            indent=2
        ))
```

---

## 6. Conditional Test Skipping

### Decision
Use `pytest.mark.requires_env("env-name")` custom marker with a fixture that checks environment availability.

### Rationale
- FR-010 requires clear reporting of skipped scenarios
- Custom marker is explicit and documented
- Fixture-based check runs once per session

### Alternatives Considered
1. **Skip inside test body**: Rejected because skip reason is less visible in test output.
2. **conftest.py autouse fixture**: Rejected because it would affect all tests, not just marked ones.

### Key Code Pattern

```python
# conftest.py
import subprocess
import pytest

def _env_available(env_name: str) -> bool:
    try:
        proc = subprocess.run(
            ["conda", "run", "-n", env_name, "python", "-c", "print('ok')"],
            check=False, capture_output=True, text=True, timeout=10
        )
        return proc.returncode == 0
    except Exception:
        return False

@pytest.fixture(autouse=True)
def check_required_env(request):
    marker = request.node.get_closest_marker("requires_env")
    if marker:
        env_name = marker.args[0]
        if not _env_available(env_name):
            pytest.skip(f"Required environment not available: {env_name}")

# Usage in test file
@pytest.mark.requires_env("bioimage-mcp-cellpose")
async def test_cellpose_pipeline(live_server):
    ...
```

---

## 7. Dataset Availability

### Decision
Use existing `datasets/FLUTE_FLIM_data_tif/` for smoke test scenarios.

### Rationale
- Already present in the repository with known-good files
- Used by existing integration tests (`test_live_workflow.py`)
- Contains both sample images and reference data for calibration

### Key Files
- `datasets/FLUTE_FLIM_data_tif/hMSC control.tif` - Primary test image
- `datasets/FLUTE_FLIM_data_tif/Fluorescein_hMSC.tif` - Reference for phasor calibration
- `datasets/synthetic/test.tif` - Lightweight fallback

### Validation Pattern

```python
FLUTE_DATASET = Path(__file__).parent.parent.parent / "datasets" / "FLUTE_FLIM_data_tif"

@pytest.fixture
def sample_image():
    if not FLUTE_DATASET.exists():
        pytest.skip(f"Dataset missing at {FLUTE_DATASET}")
    image_path = FLUTE_DATASET / "hMSC control.tif"
    if not image_path.exists():
        pytest.skip(f"Sample image missing: {image_path}")
    return image_path
```

---

## 8. Error Handling Strategy

### Decision
Capture server stderr separately, check `CallToolResult.isError` for tool failures, and fail fast with diagnostic output.

### Rationale
- FR-008 requires actionable diagnostics on server failure
- Server errors may appear in stderr before tool responses
- Tool-level errors are returned in the MCP response, not raised as exceptions

### Key Code Pattern

```python
async def call_tool_checked(self, tool: str, arguments: dict) -> dict:
    """Call tool and raise on error with diagnostics."""
    start = time.perf_counter()
    result = await self.session.call_tool(tool, arguments=arguments)
    duration_ms = (time.perf_counter() - start) * 1000
    
    self.logger.log_response(correlation_id, result, duration_ms)
    
    if result.isError:
        # Extract error details from content
        error_msg = str(result.content) if result.content else "Unknown error"
        raise SmokeTestError(
            f"Tool '{tool}' failed: {error_msg}\n"
            f"Arguments: {arguments}\n"
            f"Server stderr: {self._get_stderr()}"
        )
    
    return self._parse_result(result)
```

---

## Summary of Technology Choices

| Aspect | Decision | Package/Pattern |
|--------|----------|-----------------|
| MCP Client | Official SDK | `mcp.client.stdio.stdio_client`, `ClientSession` |
| Async Management | Context stack | `contextlib.AsyncExitStack` |
| Test Framework | pytest async | `pytest-asyncio>=0.23` |
| Fixture Scope | Session-scoped server | `@pytest_asyncio.fixture(scope="session")` |
| Readiness | MCP init handshake | `session.initialize()` |
| Logging | Structured JSON | Custom `InteractionLogger` class |
| Conditional Skip | Custom marker | `@pytest.mark.requires_env` |
| Dataset | Existing repo data | `datasets/FLUTE_FLIM_data_tif/` |

---

## Open Questions (Resolved)

1. ~~Does the `mcp` package support client-side connections?~~ **Yes**, via `mcp.client.stdio.stdio_client` and `ClientSession`.

2. ~~How to detect server readiness?~~ **Use `session.initialize()`** which blocks until the server responds.

3. ~~How to handle tool environments not installed?~~ **Use `@pytest.mark.requires_env` marker** with fixture-based skip.

4. ~~What dataset to use?~~ **`datasets/FLUTE_FLIM_data_tif/`** already present and used by integration tests.
