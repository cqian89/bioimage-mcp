from __future__ import annotations

import time
import sqlite3
import shutil
import tempfile
from pathlib import Path
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from bioimage_mcp.config.schema import Config, StorageSettings
from bioimage_mcp.storage.service import StorageService
from bioimage_mcp.storage.sqlite import init_schema


def benchmark():
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        config = MagicMock(spec=Config)
        config.artifact_store_root = tmp_dir
        config.storage = StorageSettings(
            quota_bytes=100 * 1024**3,  # 100GB
            warning_threshold=0.8,
            critical_threshold=0.9,
            retention_days=7,
            auto_cleanup_enabled=False,
        )
        config.session_ttl_hours = 24

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_schema(conn)

        service = StorageService(config, conn)

        print(f"Generating 100 sessions with 10 artifacts each...")
        obj_dir = tmp_dir / "objects"
        obj_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(UTC)
        for i in range(100):
            sid = f"session_{i}"
            # Half are expired
            completed_at = (now - timedelta(days=10)).isoformat() if i < 50 else None
            conn.execute(
                "INSERT INTO sessions (session_id, status, is_pinned, created_at, last_activity_at, completed_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    sid,
                    "completed" if i < 50 else "active",
                    0,
                    now.isoformat(),
                    now.isoformat(),
                    completed_at,
                ),
            )
            for j in range(10):
                ref_id = f"art_{i}_{j}"
                path = obj_dir / f"{ref_id}.dat"
                path.write_bytes(b"data" * 1024)  # 4KB
                conn.execute(
                    "INSERT INTO artifacts (ref_id, type, uri, format, storage_type, mime_type, size_bytes, checksums_json, metadata_json, created_at, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        ref_id,
                        "BioImageRef",
                        f"file://{path}",
                        "OME-TIFF",
                        "file",
                        "image/tiff",
                        4096,
                        "{}",
                        "{}",
                        now.isoformat(),
                        sid,
                    ),
                )
        conn.commit()

        print("Benchmarking get_status()...")
        start = time.time()
        status_before = service.get_status()
        end = time.time()
        print(f"get_status() took {end - start:.3f}s")
        assert end - start < 1.0, f"get_status() too slow: {end - start:.3f}s"

        print("Benchmarking prune()...")
        start = time.time()
        result = service.prune()
        end = time.time()
        print(f"prune() took {end - start:.3f}s")
        print(f"Deleted {result.sessions_deleted} sessions, {result.artifacts_deleted} artifacts")
        assert end - start < 30.0, f"prune() too slow: {end - start:.3f}s"
        assert result.sessions_deleted == 50

        status_after = service.get_status()
        delta = status_before.used_bytes - status_after.used_bytes
        print(f"Status delta: {delta}, Result bytes_reclaimed: {result.bytes_reclaimed}")
        assert delta == result.bytes_reclaimed, f"Mismatch: {delta} != {result.bytes_reclaimed}"

    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    benchmark()
