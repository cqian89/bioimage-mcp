import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field


class Interaction(BaseModel):
    timestamp: str  # ISO 8601 timestamp with timezone
    direction: Literal["request", "response"]
    tool: str  # MCP tool name
    params: dict[str, Any] | None = None  # Request parameters
    result: dict[str, Any] | None = None  # Response result
    duration_ms: float | None = None  # Duration in milliseconds
    error: str | None = None  # Error message if failed
    correlation_id: str | None = None  # Links response to request


class InteractionLog(BaseModel):
    test_run_id: str  # Unique ID (e.g., smoke_2026-01-08_143022)
    scenario: str  # Scenario name
    started_at: str  # ISO 8601 timestamp
    completed_at: str | None = None
    status: Literal["running", "passed", "failed", "error"] = "running"
    interactions: list[Interaction] = Field(default_factory=list)
    server_stderr: str | None = None
    error_summary: str | None = None


class InteractionLogger:
    def __init__(self, test_run_id: str, scenario: str, max_payload_bytes: int = 10000):
        self.max_payload_bytes = max_payload_bytes
        self.log = InteractionLog(
            test_run_id=test_run_id,
            scenario=scenario,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

    def log_request(self, tool: str, params: dict) -> str:
        """Log request, return correlation ID (index as string)."""
        correlation_id = str(len(self.log.interactions))
        interaction = Interaction(
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction="request",
            tool=tool,
            params=self._truncate(params),
            correlation_id=correlation_id,
        )
        self.log.interactions.append(interaction)
        return correlation_id

    def log_response(self, correlation_id: str, result: dict, duration_ms: float):
        """Log response with correlation to request."""
        # Find the request tool
        tool = "unknown"
        try:
            idx = int(correlation_id)
            if idx < len(self.log.interactions):
                tool = self.log.interactions[idx].tool
        except (ValueError, IndexError):
            pass

        interaction = Interaction(
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction="response",
            tool=tool,
            result=self._truncate(result),
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
        self.log.interactions.append(interaction)

    def _truncate(self, data: dict) -> dict:
        """Truncate large payloads. If serialized size > max_payload_bytes,
        return {"_truncated": True, "_size": N}"""
        if not data:
            return data

        try:
            serialized = json.dumps(data)
            if len(serialized) > self.max_payload_bytes:
                return {"_truncated": True, "_size": len(serialized)}
        except (TypeError, ValueError):
            pass
        return data

    def save(self, path: Path):
        """Save log to JSON file."""
        if not self.log.completed_at:
            self.log.completed_at = datetime.now(timezone.utc).isoformat()

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.log.model_dump_json(indent=2))
