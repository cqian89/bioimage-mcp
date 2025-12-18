from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManifestDiagnostic:
    path: Path
    tool_id: str | None
    errors: list[str]
