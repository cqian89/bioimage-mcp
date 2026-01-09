import pytest
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
from bioimage_mcp.storage.models import (
    StorageStatus,
    SessionStorageInfo,
    SessionSummary,
    OrphanFile,
    PruneResult,
    QuotaCheckResult,
)


def test_session_storage_info():
    info = SessionStorageInfo(session_count=5, artifact_count=20, total_bytes=1024 * 1024 * 100)
    assert info.session_count == 5
    assert info.total_bytes == 104857600


def test_storage_status():
    active_info = SessionStorageInfo(session_count=2, artifact_count=10, total_bytes=5000)
    status = StorageStatus(
        total_bytes=10000,
        used_bytes=6000,
        usage_percent=60.0,
        by_state={"active": active_info},
        orphan_bytes=1000,
    )
    assert status.total_bytes == 10000
    assert status.by_state["active"].session_count == 2


def test_session_summary():
    now = datetime.now(timezone.utc)
    summary = SessionSummary(
        session_id="sess_123",
        status="completed",
        is_pinned=False,
        created_at=now,
        completed_at=now,
        artifact_count=3,
        total_bytes=3000,
        age_seconds=3600,
    )
    assert summary.session_id == "sess_123"
    assert summary.status == "completed"


def test_orphan_file():
    orphan = OrphanFile(path=Path("/tmp/orphan.tiff"), size_bytes=1024)
    assert orphan.size_bytes == 1024


def test_prune_result():
    result = PruneResult(
        sessions_deleted=2,
        artifacts_deleted=10,
        bytes_reclaimed=5000,
        orphan_files_deleted=1,
        errors=[],
    )
    assert result.sessions_deleted == 2


def test_quota_check_result():
    result = QuotaCheckResult(allowed=True, usage_percent=85.0, message="Usage at 85%")
    assert result.allowed is True
