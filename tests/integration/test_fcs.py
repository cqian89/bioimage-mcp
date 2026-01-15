"""Integration tests for FCS correlation (Phase 3)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

# Mark all tests in this module as requiring tttrlib environment
pytestmark = pytest.mark.requires_env("bioimage-mcp-tttrlib")

# Dataset paths
TTTR_DATA_ROOT = Path(__file__).parents[2] / "datasets" / "tttr-data"


def _mock_execute_step_fcs(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates successful FCS operations."""
    if fn_id == "tttrlib.Correlator":
        # Create a mock correlation curve CSV
        csv_path = work_dir / "correlation.csv"
        data = [
            ["tau", "correlation"],
            [1e-6, 1.5],
            [1e-5, 1.4],
            [1e-4, 1.3],
            [1e-3, 1.1],
            [1e-2, 1.0],
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        log_msg = f"Correlation computed using method: {params.get('method', 'default')}"
        return (
            {
                "ok": True,
                "outputs": {
                    "curve": {
                        "type": "TableRef",
                        "format": "csv",
                        "path": str(csv_path),
                        "row_count": len(data) - 1,
                        "columns": data[0],
                    }
                },
                "log": log_msg,
            },
            log_msg,
            0,
        )

    return (
        {"ok": False, "error": {"code": "UNKNOWN_FUNCTION", "message": f"Unknown fn_id: {fn_id}"}},
        "",
        1,
    )


class TestFCSCorrelation:
    """Integration tests for tttrlib.Correlator."""

    @pytest.fixture
    def fcs_config(self, tmp_path: Path) -> Config:
        """Create a standard test configuration."""
        artifacts_root = tmp_path / "artifacts"
        tools_root = tmp_path / "tools"
        tools_root.mkdir()

        return Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[tools_root],
            fs_allowlist_read=[TTTR_DATA_ROOT, tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

    def test_correlator_basic(self, fcs_config: Config, monkeypatch) -> None:
        """Test basic multi-tau correlation produces TableRef."""
        # Mock execution that returns TableRef with tau, correlation columns
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_fcs,
        )

        mock_tttr = {
            "type": "TTTRRef",
            "format": "SPC-130",
            "uri": "file:///fake/path.spc",
            "ref_id": "mock-tttr-id",
        }

        with ExecutionService(fcs_config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "tttrlib.Correlator",
                            "inputs": {"tttr": mock_tttr},
                            "params": {
                                "channels": [[0], [8]],
                                "n_bins": 7,
                                "n_casc": 27,
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            outputs = status["outputs"]

            assert "curve" in outputs
            assert outputs["curve"]["type"] == "TableRef"
            assert outputs["curve"]["row_count"] > 0

            # Verify file exists and has correct columns
            csv_uri = outputs["curve"]["uri"]
            csv_path = Path(csv_uri.replace("file://", ""))
            assert csv_path.exists()
            with open(csv_path) as f:
                reader = csv.reader(f)
                header = next(reader)
                assert "tau" in header
                assert "correlation" in header

    def test_correlator_wahl_method(self, fcs_config: Config, monkeypatch) -> None:
        """Test Wahl correlation method parameter."""
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_fcs,
        )

        mock_tttr = {
            "type": "TTTRRef",
            "format": "SPC-130",
            "uri": "file:///fake/path.spc",
            "ref_id": "mock-tttr-id",
        }

        with ExecutionService(fcs_config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "tttrlib.Correlator",
                            "inputs": {"tttr": mock_tttr},
                            "params": {
                                "channels": [[0], [8]],
                                "method": "wahl",
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            log_ref = status["log_ref"]
            log_path = Path(log_ref["uri"].replace("file://", ""))
            assert log_path.exists()
            log_content = log_path.read_text()
            assert "method: wahl" in log_content

    def test_correlator_cross_correlation(self, fcs_config: Config, monkeypatch) -> None:
        """Test cross-correlation between channels."""
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_fcs,
        )

        mock_tttr = {
            "type": "TTTRRef",
            "format": "SPC-130",
            "uri": "file:///fake/path.spc",
            "ref_id": "mock-tttr-id",
        }

        with ExecutionService(fcs_config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "tttrlib.Correlator",
                            "inputs": {"tttr": mock_tttr},
                            "params": {
                                "channels": [[0], [8]],  # Cross-correlation
                            },
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            assert "curve" in status["outputs"]

    def test_correlator_output_columns(self, fcs_config: Config, monkeypatch) -> None:
        """Verify output TableRef has correct columns (tau, correlation)."""
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step_fcs,
        )

        mock_tttr = {
            "type": "TTTRRef",
            "format": "SPC-130",
            "uri": "file:///fake/path.spc",
            "ref_id": "mock-tttr-id",
        }

        with ExecutionService(fcs_config) as svc:
            result = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "tttrlib.Correlator",
                            "inputs": {"tttr": mock_tttr},
                            "params": {"channels": [[0], [0]]},
                        }
                    ]
                },
                skip_validation=True,
            )

            assert result["status"] == "success"
            status = svc.get_run_status(result["run_id"])
            curve = status["outputs"]["curve"]
            assert set(curve["columns"]) >= {"tau", "correlation"}
