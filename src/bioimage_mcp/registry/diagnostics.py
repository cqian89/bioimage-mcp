from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class EngineEventType(str, Enum):
    RUNTIME_FALLBACK = "runtime_fallback"
    OVERLAY_APPLIED = "overlay_applied"
    OVERLAY_CONFLICT = "overlay_conflict"
    MISSING_DOCS = "missing_docs"
    SKIPPED_CALLABLE = "skipped_callable"


@dataclass(frozen=True)
class EngineEvent:
    type: EngineEventType
    message: str
    fn_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "fn_id": self.fn_id,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class ManifestDiagnostic:
    path: Path
    tool_id: str | None
    errors: list[str]
    warnings: list[str] = field(default_factory=list)
    engine_events: list[EngineEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "tool_id": self.tool_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "engine_events": [e.to_dict() for e in self.engine_events],
        }
