# Data Model: Live Server Smoke Tests

**Feature**: 018-live-server-smoke-tests  
**Date**: 2026-01-08  
**Status**: Draft

This document defines the data models for the smoke test framework. These are internal test infrastructure models, not MCP API contracts.

---

## 1. Interaction Log Models

### 1.1 Interaction

Represents a single request or response in the MCP communication.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

@dataclass
class Interaction:
    """Single request or response in MCP communication."""
    
    timestamp: str
    """ISO 8601 timestamp with timezone (e.g., 2026-01-08T14:30:23.456Z)."""
    
    direction: Literal["request", "response"]
    """Whether this is a request sent or response received."""
    
    tool: str
    """MCP tool name (list, describe, search, run, status, etc.)."""
    
    params: dict[str, Any] | None = None
    """Request parameters (for direction=request)."""
    
    result: dict[str, Any] | None = None
    """Response result (for direction=response)."""
    
    duration_ms: float | None = None
    """Duration in milliseconds (for direction=response)."""
    
    error: str | None = None
    """Error message if the interaction failed."""
    
    correlation_id: str | None = None
    """Links response to its request."""
```

**Validation Rules**:
- `timestamp` MUST be valid ISO 8601
- `direction` MUST be "request" or "response"
- `tool` MUST be one of the 8 MCP tools: list, describe, search, run, status, artifact_info, session_export, session_replay
- For `direction="request"`: `params` MAY be present, `result` MUST be None
- For `direction="response"`: `result` or `error` MUST be present

### 1.2 InteractionLog

Complete log for a smoke test run.

```python
@dataclass
class InteractionLog:
    """Complete interaction log for a smoke test run."""
    
    test_run_id: str
    """Unique identifier for this test run (e.g., smoke_2026-01-08_143022)."""
    
    scenario: str
    """Name of the smoke test scenario (e.g., flim_phasor, cellpose_pipeline)."""
    
    started_at: str
    """ISO 8601 timestamp when the test started."""
    
    completed_at: str | None = None
    """ISO 8601 timestamp when the test completed (None if still running)."""
    
    status: Literal["running", "passed", "failed", "error"] = "running"
    """Final status of the test run."""
    
    interactions: list[Interaction] = field(default_factory=list)
    """Ordered list of request/response interactions."""
    
    server_stderr: str | None = None
    """Captured server stderr (truncated if too large)."""
    
    error_summary: str | None = None
    """Summary of failure if status is failed or error."""
```

**Validation Rules**:
- `test_run_id` MUST be unique per run
- `started_at` MUST be valid ISO 8601
- `completed_at` MUST be >= `started_at` if present
- `status` MUST be updated before serialization
- Total serialized size SHOULD be under 10 MB (FR-007)

### 1.3 InteractionLog JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "InteractionLog",
  "type": "object",
  "required": ["test_run_id", "scenario", "started_at", "status", "interactions"],
  "properties": {
    "test_run_id": { "type": "string" },
    "scenario": { "type": "string" },
    "started_at": { "type": "string", "format": "date-time" },
    "completed_at": { "type": ["string", "null"], "format": "date-time" },
    "status": { "type": "string", "enum": ["running", "passed", "failed", "error"] },
    "interactions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["timestamp", "direction", "tool"],
        "properties": {
          "timestamp": { "type": "string", "format": "date-time" },
          "direction": { "type": "string", "enum": ["request", "response"] },
          "tool": { "type": "string" },
          "params": { "type": ["object", "null"] },
          "result": { "type": ["object", "null"] },
          "duration_ms": { "type": ["number", "null"] },
          "error": { "type": ["string", "null"] },
          "correlation_id": { "type": ["string", "null"] }
        }
      }
    },
    "server_stderr": { "type": ["string", "null"] },
    "error_summary": { "type": ["string", "null"] }
  }
}
```

---

## 2. Smoke Test Configuration Models

### 2.1 SmokeScenario

Defines a smoke test scenario.

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class SmokeScenario:
    """Definition of a smoke test scenario."""
    
    name: str
    """Unique scenario name (e.g., flim_phasor, cellpose_pipeline)."""
    
    description: str
    """Human-readable description of what this scenario tests."""
    
    required_envs: list[str]
    """List of required tool environments (e.g., ["bioimage-mcp-base"])."""
    
    required_datasets: list[str]
    """List of required dataset paths relative to repo root."""
    
    mode: Literal["minimal", "full"]
    """Whether this runs in minimal (CI) or full mode."""
    
    timeout_seconds: int = 300
    """Maximum time for this scenario (default 5 minutes)."""
```

**Validation Rules**:
- `name` MUST be a valid Python identifier (used as test function suffix)
- `required_envs` MUST contain at least one environment
- `required_datasets` paths MUST be relative to repo root
- `timeout_seconds` MUST be > 0 and <= 600 (10 minutes max)

### 2.2 SmokeConfig

Global smoke test configuration.

```python
@dataclass
class SmokeConfig:
    """Global configuration for smoke test suite."""
    
    server_startup_timeout: float = 30.0
    """Maximum seconds to wait for server initialization (SC-002)."""
    
    minimal_suite_timeout: float = 120.0
    """Maximum seconds for entire minimal suite (SC-001)."""
    
    max_log_size_bytes: int = 10 * 1024 * 1024
    """Maximum interaction log size in bytes (SC-004)."""
    
    max_payload_preview_bytes: int = 10000
    """Maximum size for payload previews in logs."""
    
    log_directory: str = ".bioimage-mcp/smoke_logs"
    """Directory for storing interaction logs."""
```

---

## 3. Test Result Models

### 3.1 ScenarioResult

Result of a single scenario execution.

```python
@dataclass
class ScenarioResult:
    """Result of executing a smoke scenario."""
    
    scenario_name: str
    """Name of the executed scenario."""
    
    status: Literal["passed", "failed", "skipped", "error"]
    """Final status."""
    
    duration_seconds: float
    """Total execution time."""
    
    skip_reason: str | None = None
    """Reason if status is skipped."""
    
    failure_step: str | None = None
    """Which step failed if status is failed."""
    
    error_message: str | None = None
    """Error message if status is failed or error."""
    
    interaction_log_path: str | None = None
    """Path to the saved interaction log."""
    
    outputs: dict[str, Any] = field(default_factory=dict)
    """Final outputs from the scenario (artifact refs, etc.)."""
```

**State Transitions**:
```
running -> passed   (all steps complete successfully)
running -> failed   (a step returned error or assertion failed)
running -> error    (server crashed, timeout, or infrastructure failure)
pending -> skipped  (required env or dataset missing)
```

---

## 4. Entity Relationships

```
┌─────────────────┐     1:N     ┌─────────────────┐
│  InteractionLog │─────────────│   Interaction   │
└─────────────────┘             └─────────────────┘
        │                               │
        │ 1:1                           │ N:1 (correlation)
        ▼                               │
┌─────────────────┐                     │
│  ScenarioResult │◄────────────────────┘
└─────────────────┘
        │
        │ N:1
        ▼
┌─────────────────┐
│  SmokeScenario  │
└─────────────────┘
        │
        │ N:1
        ▼
┌─────────────────┐
│   SmokeConfig   │
└─────────────────┘
```

---

## 5. File Locations

| Model | Implementation Location |
|-------|------------------------|
| `Interaction` | `tests/smoke/utils/interaction_logger.py` |
| `InteractionLog` | `tests/smoke/utils/interaction_logger.py` |
| `SmokeScenario` | `tests/smoke/conftest.py` (inline dataclass) |
| `SmokeConfig` | `tests/smoke/conftest.py` (inline dataclass) |
| `ScenarioResult` | `tests/smoke/conftest.py` (inline dataclass) |

---

## 6. Example Data

### Interaction Log Example

```json
{
  "test_run_id": "smoke_2026-01-08_143022",
  "scenario": "flim_phasor",
  "started_at": "2026-01-08T14:30:22.000Z",
  "completed_at": "2026-01-08T14:31:45.000Z",
  "status": "passed",
  "interactions": [
    {
      "timestamp": "2026-01-08T14:30:23.456Z",
      "direction": "request",
      "tool": "list",
      "params": {"path": null, "limit": 50},
      "result": null,
      "duration_ms": null,
      "correlation_id": "0"
    },
    {
      "timestamp": "2026-01-08T14:30:23.789Z",
      "direction": "response",
      "tool": "list",
      "params": null,
      "result": {"items": ["base", "cellpose"], "cursor": null},
      "duration_ms": 333,
      "correlation_id": "0"
    },
    {
      "timestamp": "2026-01-08T14:30:24.000Z",
      "direction": "request",
      "tool": "run",
      "params": {
        "fn_id": "base.io.bioimage.read",
        "inputs": {"path": {"uri": "file:///datasets/FLUTE_FLIM_data_tif/hMSC control.tif"}},
        "params": {},
        "session_id": "smoke-session-abc123"
      },
      "result": null,
      "duration_ms": null,
      "correlation_id": "1"
    },
    {
      "timestamp": "2026-01-08T14:30:26.500Z",
      "direction": "response",
      "tool": "run",
      "params": null,
      "result": {
        "status": "success",
        "outputs": {
          "image": {
            "type": "BioImageRef",
            "ref_id": "art_abc123",
            "uri": "file:///tmp/artifacts/abc123.ome.zarr"
          }
        }
      },
      "duration_ms": 2500,
      "correlation_id": "1"
    }
  ],
  "server_stderr": null,
  "error_summary": null
}
```
