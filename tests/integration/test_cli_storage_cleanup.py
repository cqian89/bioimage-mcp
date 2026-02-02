from __future__ import annotations

import json
import subprocess
import sys

import pytest
import yaml

from bioimage_mcp.storage.sqlite import connect


@pytest.fixture
def test_env(tmp_path):
    root = tmp_path / "artifact_store"
    root.mkdir()
    (root / "state").mkdir()
    (root / "objects").mkdir()

    config_dir = tmp_path / ".bioimage-mcp"
    config_dir.mkdir()

    config_data = {
        "artifact_store_root": str(root),
        "tool_manifest_roots": [],
        "storage": {
            "retention_days": 7,
            "quota_bytes": 1000,
            "trigger_fraction": 0.9,
            "target_fraction": 0.7,
        },
    }

    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump(config_data))

    # Pre-init DB
    from bioimage_mcp.config.schema import Config, StoragePolicy

    cfg = Config(
        artifact_store_root=root,
        tool_manifest_roots=[],
        storage=StoragePolicy(**config_data["storage"]),
    )
    conn = connect(cfg)
    # init_schema is called by connect

    return {
        "root": root,
        "config_file": config_file,
        "tmp_path": tmp_path,
        "conn": conn,
        "config": cfg,
    }


def run_cli(test_env, args):
    cmd = [sys.executable, "-m", "bioimage_mcp.cli"] + args
    result = subprocess.run(cmd, cwd=test_env["tmp_path"], capture_output=True, text=True)
    return result


def test_cli_status_json(test_env):
    # Insert some data
    test_env["conn"].execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "art1",
            "image",
            "file://test1",
            "tiff",
            "file",
            "image/tiff",
            500,
            "{}",
            "{}",
            "2026-01-01T00:00:00Z",
        ),
    )
    test_env["conn"].commit()

    result = run_cli(test_env, ["status", "--json"])
    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert data["total_bytes"] == 500
    assert data["quota_bytes"] == 1000
    assert data["usage_fraction"] == 0.5


def test_cli_cleanup_dry_run_json(test_env):
    # Insert old data
    test_env["conn"].execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "old1",
            "image",
            "file://test1",
            "tiff",
            "file",
            "image/tiff",
            100,
            "{}",
            "{}",
            "2020-01-01T00:00:00Z",
        ),
    )
    test_env["conn"].commit()

    result = run_cli(test_env, ["cleanup", "--dry-run", "--json"])
    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert data["dry_run"] is True
    assert data["deleted_count"] == 1
    assert data["freed_bytes"] == 100

    # Verify not actually deleted
    row = test_env["conn"].execute("SELECT * FROM artifacts WHERE ref_id = 'old1'").fetchone()
    assert row is not None


def test_cli_pin_unpin(test_env):
    # Insert data
    test_env["conn"].execute(
        """
        INSERT INTO artifacts (
            ref_id, type, uri, format, storage_type, mime_type, 
            size_bytes, checksums_json, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "art1",
            "image",
            "file://test1",
            "tiff",
            "file",
            "image/tiff",
            100,
            "{}",
            "{}",
            "2020-01-01T00:00:00Z",
        ),
    )
    test_env["conn"].commit()

    # Pin it
    result = run_cli(test_env, ["pin", "art1", "--json"])
    assert result.returncode == 0

    row = test_env["conn"].execute("SELECT pinned FROM artifacts WHERE ref_id = 'art1'").fetchone()
    assert row["pinned"] == 1

    # Verify cleanup skips it
    result = run_cli(test_env, ["cleanup", "--dry-run", "--json"])
    data = json.loads(result.stdout)
    assert data["deleted_count"] == 0

    # Unpin it
    result = run_cli(test_env, ["unpin", "art1", "--json"])
    assert result.returncode == 0

    row = test_env["conn"].execute("SELECT pinned FROM artifacts WHERE ref_id = 'art1'").fetchone()
    assert row["pinned"] == 0

    # Verify cleanup catches it now
    result = run_cli(test_env, ["cleanup", "--dry-run", "--json"])
    data = json.loads(result.stdout)
    assert data["deleted_count"] == 1
