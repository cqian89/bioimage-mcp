from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class SessionStorageInfo(BaseModel):
    session_count: int
    artifact_count: int
    total_bytes: int


class StorageStatus(BaseModel):
    total_bytes: int
    used_bytes: int
    usage_percent: float
    by_state: dict[str, SessionStorageInfo]  # e.g., {"active": ..., "pinned": ...}
    orphan_bytes: int


class SessionSummary(BaseModel):
    session_id: str
    status: str  # active, completed, expired, pinned
    is_pinned: bool
    created_at: datetime
    completed_at: datetime | None
    artifact_count: int
    total_bytes: int
    age_seconds: int


class OrphanFile(BaseModel):
    path: Path
    size_bytes: int


class PruneResult(BaseModel):
    sessions_deleted: int
    artifacts_deleted: int
    bytes_reclaimed: int
    orphan_files_deleted: int
    errors: list[str]


class QuotaCheckResult(BaseModel):
    allowed: bool
    usage_percent: float
    message: str
