"""Integration tests for P1 extended features (Phase 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

# Mark all tests in this module as requiring tttrlib environment
pytestmark = pytest.mark.requires_env("bioimage-mcp-tttrlib")


def _mock_execute_step_p1(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None = None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates successful P1 operations."""
    if fn_id == "tttrlib.TTTR.get_intensity_trace":
        csv_path = work_dir / "intensity_trace.csv"
        csv_path.write_text("time_s,counts\n0.0,10\n0.01,15\n")
        return (
            {
                "ok": True,
                "outputs": {
                    "trace": {
                        "type": "TableRef",
                        "format": "csv",
                        "path": str(csv_path),
                        "columns": ["time_s", "counts"],
                        "row_count": 2,
                        "metadata": {
                            "columns": [
                                {"name": "time_s", "dtype": "float64"},
                                {"name": "counts", "dtype": "int64"},
                            ],
                            "row_count": 2,
                        },
                    }
                },
                "log": "Extracted intensity trace",
            },
            "Extracted intensity trace",
            0,
        )

    elif fn_id == "tttrlib.TTTR.get_microtime_histogram":
        csv_path = work_dir / "microtime_histogram.csv"
        csv_path.write_text("micro_time_ns,counts\n0.0,100\n1.0,200\n")
        return (
            {
                "ok": True,
                "outputs": {
                    "histogram": {
                        "type": "TableRef",
                        "format": "csv",
                        "path": str(csv_path),
                        "columns": ["micro_time_ns", "counts"],
                        "row_count": 2,
                        "metadata": {
                            "columns": [
                                {"name": "micro_time_ns", "dtype": "float64"},
                                {"name": "counts", "dtype": "int64"},
                            ],
                            "row_count": 2,
                        },
                    }
                },
                "log": "Computed microtime histogram",
            },
            "Computed microtime histogram",
            0,
        )

    elif fn_id == "tttrlib.TTTR.get_selection_by_channel":
        csv_path = work_dir / "selection.csv"
        csv_path.write_text("index\n1\n3\n5\n")
        return (
            {
                "ok": True,
                "outputs": {
                    "selection": {
                        "type": "TableRef",
                        "format": "csv",
                        "path": str(csv_path),
                        "columns": ["index"],
                        "row_count": 3,
                        "metadata": {
                            "columns": [{"name": "index", "dtype": "int64"}],
                            "row_count": 3,
                        },
                    }
                },
                "log": "Selected photons by channel",
            },
            "Selected photons by channel",
            0,
        )

    elif fn_id == "tttrlib.CLSMImage.intensity":
        tiff_path = work_dir / "intensity.ome.tif"
        tiff_path.write_text("fake tiff content")
        return (
            {
                "ok": True,
                "outputs": {
                    "image": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "path": str(tiff_path),
                    }
                },
                "log": "Generated intensity image",
            },
            "Generated intensity image",
            0,
        )

    elif fn_id == "tttrlib.CLSMImage.get_mean_micro_time":
        tiff_path = work_dir / "mean_microtime.ome.tif"
        tiff_path.write_text("fake tiff content")
        return (
            {
                "ok": True,
                "outputs": {
                    "mean_microtime": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "path": str(tiff_path),
                    }
                },
                "log": "Generated mean microtime image",
            },
            "Generated mean microtime image",
            0,
        )

    elif fn_id == "tttrlib.TTTR.write":
        filename = params.get("filename", "exported.h5")
        out_path = work_dir / filename
        out_path.write_text("fake h5 content")
        return (
            {
                "ok": True,
                "outputs": {
                    "tttr_out": {
                        "type": "TTTRRef",
                        "format": "HDF",
                        "path": str(out_path),
                    }
                },
                "log": "Exported TTTR data",
            },
            "Exported TTTR data",
            0,
        )

    return (
        {"ok": False, "error": {"message": f"Unknown function: {fn_id}"}},
        "",
        1,
    )


class TestIntensityTrace:
    """Tests for intensity trace extraction."""

    def test_get_intensity_trace(self, tmp_path: Path, monkeypatch) -> None:
        """Test extracting intensity trace as TableRef."""
        artifacts_root = tmp_path / "artifacts"
        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[str(tmp_path)],
            fs_allowlist_write=[str(tmp_path)],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_p1,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR.get_intensity_trace",
                            "inputs": {"tttr": {"type": "TTTRRef", "uri": "file:///fake.ptu"}},
                            "params": {"time_window_length": 0.010},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            outputs = svc.get_run_status(result["run_id"])["outputs"]
            assert "trace" in outputs
            assert outputs["trace"]["type"] == "TableRef"

            # Verify CSV content
            csv_path = Path(outputs["trace"]["uri"].replace("file://", ""))
            content = csv_path.read_text()
            assert "time_s,counts" in content


class TestMicrotimeHistogram:
    """Tests for microtime histogram."""

    def test_get_microtime_histogram(self, tmp_path: Path, monkeypatch) -> None:
        """Test computing microtime histogram."""
        artifacts_root = tmp_path / "artifacts"
        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[str(tmp_path)],
            fs_allowlist_write=[str(tmp_path)],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_p1,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR.get_microtime_histogram",
                            "inputs": {"tttr": {"type": "TTTRRef", "uri": "file:///fake.ptu"}},
                            "params": {"micro_time_coarsening": 1},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            outputs = svc.get_run_status(result["run_id"])["outputs"]
            assert "histogram" in outputs
            assert outputs["histogram"]["type"] == "TableRef"

            csv_path = Path(outputs["histogram"]["uri"].replace("file://", ""))
            content = csv_path.read_text()
            assert "micro_time_ns,counts" in content


class TestChannelSelection:
    """Tests for channel-based photon selection."""

    def test_get_selection_by_channel(self, tmp_path: Path, monkeypatch) -> None:
        """Test selecting photons by channel."""
        artifacts_root = tmp_path / "artifacts"
        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[str(tmp_path)],
            fs_allowlist_write=[str(tmp_path)],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_p1,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR.get_selection_by_channel",
                            "inputs": {"tttr": {"type": "TTTRRef", "uri": "file:///fake.ptu"}},
                            "params": {"channels": [0, 1]},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            outputs = svc.get_run_status(result["run_id"])["outputs"]
            assert "selection" in outputs
            assert outputs["selection"]["type"] == "TableRef"

            csv_path = Path(outputs["selection"]["uri"].replace("file://", ""))
            content = csv_path.read_text()
            assert "index" in content


class TestCLSMIntensity:
    """Tests for CLSM intensity image."""

    def test_clsm_intensity_image(self, tmp_path: Path, monkeypatch) -> None:
        """Test getting intensity image from CLSMImage."""
        artifacts_root = tmp_path / "artifacts"
        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[str(tmp_path)],
            fs_allowlist_write=[str(tmp_path)],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_p1,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.CLSMImage.intensity",
                            "inputs": {"clsm": {"type": "ObjectRef", "uri": "obj://fake/clsm"}},
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            outputs = svc.get_run_status(result["run_id"])["outputs"]
            assert "image" in outputs
            assert outputs["image"]["type"] == "BioImageRef"


class TestMeanMicrotime:
    """Tests for mean microtime image."""

    def test_get_mean_micro_time(self, tmp_path: Path, monkeypatch) -> None:
        """Test computing mean microtime image."""
        artifacts_root = tmp_path / "artifacts"
        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[str(tmp_path)],
            fs_allowlist_write=[str(tmp_path)],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_p1,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.CLSMImage.get_mean_micro_time",
                            "inputs": {
                                "clsm": {"type": "ObjectRef", "uri": "obj://fake/clsm"},
                                "tttr": {"type": "TTTRRef", "uri": "file:///fake.ptu"},
                            },
                            "params": {},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            outputs = svc.get_run_status(result["run_id"])["outputs"]
            assert "mean_microtime" in outputs
            assert outputs["mean_microtime"]["type"] == "BioImageRef"


class TestTTTRExport:
    """Tests for TTTR data export."""

    def test_tttr_write_export(self, tmp_path: Path, monkeypatch) -> None:
        """Test exporting TTTR to Photon-HDF5."""
        artifacts_root = tmp_path / "artifacts"
        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[str(tmp_path)],
            fs_allowlist_write=[str(tmp_path)],
        )

        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_p1,
        )

        with ExecutionService(config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "id": "tttrlib.TTTR.write",
                            "inputs": {"tttr": {"type": "TTTRRef", "uri": "file:///fake.ptu"}},
                            "params": {"filename": "exported.h5"},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            outputs = svc.get_run_status(result["run_id"])["outputs"]
            assert "tttr_out" in outputs
            assert outputs["tttr_out"]["type"] == "TTTRRef"
            assert outputs["tttr_out"]["uri"].endswith(".h5")
