from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ManifestDiagnostic:
    path: Path
    tool_id: str | None
    errors: list[str]
    warnings: list[str] = field(default_factory=list)
