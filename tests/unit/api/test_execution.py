from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


REPO_ROOT = Path(__file__).resolve().parents[3]


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
                        "id": "hints.fn",
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


def _build_tttrlib_config(tmp_path: Path) -> Config:
    return Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[REPO_ROOT / "tools" / "tttrlib"],
        fs_allowlist_read=[tmp_path, REPO_ROOT],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )


class _FakeWorker:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.requests: list[dict] = []

    def execute(self, *, request: dict, memory_store, timeout_seconds, progress_callback):
        self.requests.append(request)
        return self.response


class _FakeWorkerManager:
    def __init__(self, worker: _FakeWorker) -> None:
        self.worker = worker
        self.env_requests: list[tuple[str, str]] = []
        self._memory_store = None

    def get_worker(self, session_id: str, env_id: str):
        self.env_requests.append((session_id, env_id))
        return self.worker

    def register_artifact(self, session_id: str, env_id: str, ref_id: str) -> None:
        return None


def test_error_hints_selected_by_error_code(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(
        manifest_dir,
        {
            "GENERAL": {
                "diagnosis": "General failure",
                "suggested_fix": {
                    "id": "base.retry",
                    "params": {},
                    "explanation": "Retry with defaults.",
                },
            },
            "AXIS_SAMPLES_ERROR": {
                "diagnosis": "Time axis has too few samples",
                "suggested_fix": {
                    "id": "base.io.bioimage.export",
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
            {"steps": [{"id": "hints.fn", "inputs": {}, "params": {}}]},
            skip_validation=True,
        )

    assert response["status"] == "failed"
    assert response["hints"]["diagnosis"] == "Time axis has too few samples"
    assert response["hints"]["suggested_fix"]["id"] == "base.io.bioimage.export"


def test_error_hints_fallback_to_general(tmp_path: Path, monkeypatch) -> None:
    manifest_dir = tmp_path / "tools"
    _write_manifest(
        manifest_dir,
        {
            "GENERAL": {
                "diagnosis": "General failure",
                "suggested_fix": {
                    "id": "base.retry",
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
            {"steps": [{"id": "hints.fn", "inputs": {}, "params": {}}]},
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


def test_run_workflow_imports_tttr_intensity_trace_with_numeric_schema(tmp_path: Path) -> None:
    config = _build_tttrlib_config(tmp_path)
    trace_csv = tmp_path / "trace.csv"
    trace_csv.write_text("time,count_rate\n0.0,10.0\n0.25,12.5\n", encoding="utf-8")
    worker = _FakeWorker(
        {
            "ok": True,
            "outputs": {
                "trace": {
                    "ref_id": "trace-ref",
                    "type": "TableRef",
                    "path": str(trace_csv),
                    "format": "csv",
                    "columns": ["time", "count_rate"],
                    "row_count": 2,
                    "metadata": {
                        "columns": [
                            {"name": "time", "dtype": "float64"},
                            {"name": "count_rate", "dtype": "float64"},
                        ]
                    },
                }
            },
        }
    )
    worker_manager = _FakeWorkerManager(worker)

    with ExecutionService(config, worker_manager=worker_manager) as svc:
        response = svc.run_workflow(
            {
                "steps": [
                    {
                        "id": "tttrlib.TTTR.get_intensity_trace",
                        "inputs": {"tttr": {"ref_id": "tttr-1", "uri": "file:///tmp/mock.spc"}},
                        "params": {"time_window_length": 0.25},
                    }
                ]
            },
            skip_validation=True,
        )

    assert response["status"] == "success"
    trace = response["outputs"]["trace"]
    assert trace["columns"] == ["time", "count_rate"]
    assert trace["row_count"] == 2
    assert trace["metadata"]["columns"] == [
        {"name": "time", "dtype": "float64"},
        {"name": "count_rate", "dtype": "float64"},
    ]
    assert trace["metadata"]["row_count"] == 2


def test_run_workflow_imports_empty_tttr_selection_table_with_numeric_schema(
    tmp_path: Path,
) -> None:
    config = _build_tttrlib_config(tmp_path)
    selection_csv = tmp_path / "empty_selection.csv"
    selection_csv.write_text("index\n", encoding="utf-8")
    worker = _FakeWorker(
        {
            "ok": True,
            "outputs": {
                "selection": {
                    "ref_id": "selection-empty-ref",
                    "type": "TableRef",
                    "path": str(selection_csv),
                    "format": "csv",
                    "columns": ["index"],
                    "row_count": 0,
                    "metadata": {
                        "columns": [{"name": "index", "dtype": "int64"}],
                    },
                }
            },
        }
    )
    worker_manager = _FakeWorkerManager(worker)

    with ExecutionService(config, worker_manager=worker_manager) as svc:
        response = svc.run_workflow(
            {
                "steps": [
                    {
                        "id": "tttrlib.TTTR.get_selection_by_count_rate",
                        "inputs": {"tttr": {"ref_id": "tttr-1", "uri": "file:///tmp/mock.spc"}},
                        "params": {"time_window": 0.5, "n_ph_max": 3},
                    }
                ]
            },
            skip_validation=True,
        )

    assert response["status"] == "success"
    selection = response["outputs"]["selection"]
    assert selection["columns"] == ["index"]
    assert selection["row_count"] == 0
    assert selection["metadata"]["columns"] == [{"name": "index", "dtype": "int64"}]
    assert selection["metadata"]["row_count"] == 0
