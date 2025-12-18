from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ArtifactChecksum(BaseModel):
    algorithm: str
    value: str


class ArtifactRef(BaseModel):
    ref_id: str
    type: str
    uri: str
    format: str
    mime_type: str
    size_bytes: int
    checksums: list[ArtifactChecksum] = Field(default_factory=list)
    created_at: str
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def now(cls) -> str:
        return datetime.now(UTC).isoformat()
