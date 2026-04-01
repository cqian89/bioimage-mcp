import json
from datetime import UTC, datetime
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
    status: Literal["running", "passed", "failed", "error", "skipped"] = "running"
    interactions: list[Interaction] = Field(default_factory=list)
    server_stderr: str | None = None
    error_summary: str | None = None
    skip_reason: str | None = None


MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class InteractionLogger:
    def __init__(
        self,
        test_run_id: str = "pending",
        scenario: str = "pending",
        max_payload_bytes: int = 10000,
    ):
        self.max_payload_bytes = max_payload_bytes
        self.log = InteractionLog(
            test_run_id=test_run_id,
            scenario=scenario,
            started_at=datetime.now(UTC).isoformat(),
        )

    @property
    def interactions(self) -> list[Interaction]:
        """Return list of interactions."""
        return self.log.interactions

    def log_request(self, tool: str, params: dict) -> str:
        """Log request, return correlation ID (index as string)."""
        correlation_id = str(len(self.log.interactions))
        interaction = Interaction(
            timestamp=datetime.now(UTC).isoformat(),
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
            timestamp=datetime.now(UTC).isoformat(),
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
        self.save_log(self.log, path)

    def save_log(self, log: InteractionLog, path: Path):
        """Save log with size bounding."""
        import json

        if not log.completed_at:
            log.completed_at = datetime.now(UTC).isoformat()

        data = log.model_dump(mode="json")
        serialized = json.dumps(data, indent=2)

        # Truncate if too large
        if len(serialized.encode()) > MAX_LOG_SIZE_BYTES:
            # Truncate interactions from the middle
            while len(serialized.encode()) > MAX_LOG_SIZE_BYTES and len(data["interactions"]) > 2:
                mid = len(data["interactions"]) // 2
                data["interactions"].pop(mid)
                data["_truncated_interactions"] = True
                serialized = json.dumps(data, indent=2)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized)
