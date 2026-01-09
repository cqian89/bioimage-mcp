import sqlite3
import pytest
from bioimage_mcp.storage.service import StorageService
from bioimage_mcp.storage.sqlite import init_schema
from bioimage_mcp.config.schema import Config, StorageSettings
from pathlib import Path


@pytest.fixture
def storage_service(tmp_path):
    root = (tmp_path / "mcp").absolute()
    root.mkdir()
    config = Config(
        artifact_store_root=root,
        tool_manifest_roots=[(root / "tools").absolute()],
        storage=StorageSettings(quota_bytes=1000, warning_threshold=0.80, critical_threshold=0.95),
        session_ttl_hours=24,
    )
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    # Use row_factory to match StorageService expectations
    conn.row_factory = sqlite3.Row
    return StorageService(config, conn)


def test_check_quota_below_warning(storage_service):
    # 79% usage
    storage_service.conn.execute(
        "INSERT INTO artifacts (ref_id, session_id, type, uri, format, mime_type, size_bytes, checksums_json, metadata_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "art1",
            "sess1",
            "BioImageRef",
            "file:///tmp/1",
            "tiff",
            "image/tiff",
            790,
            "[]",
            "{}",
            "now",
        ),
    )
    storage_service.conn.commit()

    # Action
    result = storage_service.check_quota()

    # Verification
    assert result.allowed is True
    assert result.usage_percent == 79.0
    assert result.used_bytes == 790
    assert "below" in result.message.lower()


def test_check_quota_at_warning_threshold(storage_service):
    # 80% usage
    storage_service.conn.execute(
        "INSERT INTO artifacts (ref_id, session_id, type, uri, format, mime_type, size_bytes, checksums_json, metadata_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "art1",
            "sess1",
            "BioImageRef",
            "file:///tmp/1",
            "tiff",
            "image/tiff",
            800,
            "[]",
            "{}",
            "now",
        ),
    )
    storage_service.conn.commit()

    # Action
    result = storage_service.check_quota()

    # Verification
    assert result.allowed is True
    assert result.usage_percent == 80.0
    assert result.used_bytes == 800
    assert "warning" in result.message.lower()


def test_check_quota_at_critical_threshold(storage_service):
    # 95% usage
    storage_service.conn.execute(
        "INSERT INTO artifacts (ref_id, session_id, type, uri, format, mime_type, size_bytes, checksums_json, metadata_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "art1",
            "sess1",
            "BioImageRef",
            "file:///tmp/1",
            "tiff",
            "image/tiff",
            950,
            "[]",
            "{}",
            "now",
        ),
    )
    storage_service.conn.commit()

    # Action
    result = storage_service.check_quota()

    # Verification
    assert result.allowed is False
    assert result.usage_percent == 95.0
    assert result.used_bytes == 950

    assert result.used_bytes == 950
    assert "critical" in result.message.lower()
    assert "95.0%" in result.message


def test_check_quota_with_orphans(storage_service):
    # 50% artifacts + 45% orphans = 95% total
    storage_service.conn.execute(
        "INSERT INTO artifacts (ref_id, session_id, type, uri, format, mime_type, size_bytes, checksums_json, metadata_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "art1",
            "sess1",
            "BioImageRef",
            "file:///tmp/1",
            "tiff",
            "image/tiff",
            500,
            "[]",
            "{}",
            "now",
        ),
    )
    storage_service.conn.commit()

    # Create an orphan file
    obj_dir = storage_service.root / "objects"
    obj_dir.mkdir()
    orphan = obj_dir / "orphan.dat"
    orphan.write_bytes(b"x" * 450)

    # Action
    result = storage_service.check_quota()

    # Verification
    assert result.allowed is False
    assert result.usage_percent == 95.0
    assert result.used_bytes == 950
