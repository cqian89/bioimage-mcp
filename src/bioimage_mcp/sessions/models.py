from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Session(BaseModel):
    """A user session for interactive tool executions."""

    session_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_activity_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    is_pinned: bool = False
    status: Literal["active", "expired", "exported", "completed", "pinned"] = "active"
    connection_hint: str | None = None

    @classmethod
    def now(cls) -> str:
        return datetime.now(UTC).isoformat()


class SessionStep(BaseModel):
    """A single tool execution attempt within a session."""

    session_id: str
    step_id: str
    ordinal: int
    fn_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    status: Literal["succeeded", "success", "failed", "running", "cancelled"] = "running"
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    ended_at: str | None = None
    run_id: str | None = None
    error: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    log_ref_id: str | None = None
    canonical: bool = True


class ActiveToolSet(BaseModel):
    """The subset of manifest functions exposed for discovery in a session."""

    session_id: str
    fn_id: str


class SessionExport(BaseModel):
    """A reproducible workflow artifact generated from canonical steps."""

    schema_version: str = "0.1"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    session_id: str
    steps: list[dict[str, Any]]
    attempts: dict[str, Any] | None = None
