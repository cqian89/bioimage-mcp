from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


def _write_manifest(manifest_dir: Path, error_hints: dict[str, dict]) -> None:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "manifest_version": "0.0",
                "tool_id": "tools.hints",
                "tool_version": "0.1.0",
                "name": "Hints Tool",
                "description": "Tool for hints tests",
                "env_id": "bioimage-mcp-hints",
                "entrypoint": "hints/entrypoint.py",
                "functions": [
                    {
                        "fn_id": "hints.fn",
                        "tool_id": "tools.hints",
                        "name": "Hints Function",
                        "description": "Function for hints tests",
                        "tags": ["test"],
                        "inputs": [],
                        "outputs": [],
                        "params_schema": {"type": "object", "properties": {}},
                        "hints": {"error_hints": error_hints},
                    }
                ],
            }
        )
    )


def _build_config(tmp_path: Path, manifest_dir: Path) -> Config:
    return Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[manifest_dir],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )


def test_error_hints_selected_by_error_code(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(
        manifest_dir,
        {
            "GENERAL": {
                "diagnosis": "General failure",
                "suggested_fix": {
                    "fn_id": "base.retry",
                    "params": {},
                    "explanation": "Retry with defaults.",
                },
            },
            "AXIS_SAMPLES_ERROR": {
                "diagnosis": "Time axis has too few samples",
                "suggested_fix": {
                    "fn_id": "base.io.bioimage.export",
                    "params": {"format": "OME-TIFF"},
                    "explanation": "Provide a dataset with multiple time samples.",
                },
            },
        },
    )
    config = _build_config(tmp_path, manifest_dir)

    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        lambda **_kw: (
            {"ok": False, "error": {"message": "boom", "code": "AXIS_SAMPLES_ERROR"}},
            "log",
            1,
        ),
    )

    with ExecutionService(config) as svc:
        response = svc.run_workflow(
            {"steps": [{"fn_id": "hints.fn", "inputs": {}, "params": {}}]},
            skip_validation=True,
        )

    assert response["status"] == "failed"
    assert response["hints"]["diagnosis"] == "Time axis has too few samples"
    assert response["hints"]["suggested_fix"]["fn_id"] == "base.io.bioimage.export"


def test_error_hints_fallback_to_general(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(
        manifest_dir,
        {
            "GENERAL": {
                "diagnosis": "General failure",
                "suggested_fix": {
                    "fn_id": "base.retry",
                    "params": {},
                    "explanation": "Retry with defaults.",
                },
            }
        },
    )
    config = _build_config(tmp_path, manifest_dir)

    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        lambda **_kw: (
            {"ok": False, "error": {"message": "boom", "code": "UNKNOWN"}},
            "log",
            1,
        ),
    )

    with ExecutionService(config) as svc:
        response = svc.run_workflow(
            {"steps": [{"fn_id": "hints.fn", "inputs": {}, "params": {}}]},
            skip_validation=True,
        )

    assert response["status"] == "failed"
    assert response["hints"]["diagnosis"] == "General failure"


def test_close_closes_owned_run_store(tmp_path: Path) -> None:
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    service = ExecutionService(config, artifact_store=artifact_store)

    service.close()

    with pytest.raises(sqlite3.ProgrammingError):
        service._run_store._conn.execute("SELECT 1")

    artifact_store._conn.execute("SELECT 1")
    conn.close()
