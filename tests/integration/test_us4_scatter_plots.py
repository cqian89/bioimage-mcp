"""
Integration tests for User Story 4: Scatter Plot Feature Relationships.
"""

from pathlib import Path

import pandas as pd
import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.fixture
def execution_service(tmp_path: Path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

    # Use real tools directory
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path, artifacts_root],
        fs_denylist=[],
    )

    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    service = ExecutionService(config, artifact_store=artifact_store)
    yield service
    service.close()


@pytest.mark.integration
def test_scatter_workflow_with_table(execution_service, tmp_path):
    """T023: Test scatter plot with TableRef input and column mapping."""

    # Create a temporary CSV with feature columns
    csv_path = tmp_path / "features.csv"
    df = pd.DataFrame(
        {
            "area": [100, 200, 150, 300],
            "circularity": [0.9, 0.8, 0.95, 0.7],
            "intensity": [50, 80, 60, 100],
        }
    )
    df.to_csv(csv_path, index=False)

    # Step 1: Load TableRef
    workflow_load = {"steps": [{"fn_id": "base.io.table.load", "params": {"path": str(csv_path)}}]}
    result_load = execution_service.run_workflow(workflow_load)
    assert result_load["status"] == "success"
    table_ref = execution_service.get_run_status(result_load["run_id"])["outputs"]["table"]

    # Step 2: subplots
    workflow_fig = {"steps": [{"fn_id": "base.matplotlib.pyplot.subplots"}]}
    result_fig = execution_service.run_workflow(workflow_fig)
    assert result_fig["status"] == "success"
    outputs_fig = execution_service.get_run_status(result_fig["run_id"])["outputs"]
    fig_ref = outputs_fig["figure"]
    ax_ref = outputs_fig["axes"]

    # Step 3: scatter
    workflow_scatter = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.scatter",
                "inputs": {"axes": ax_ref, "x": "area", "y": "circularity", "table": table_ref},
                "params": {"s": "intensity", "c": "intensity", "cmap": "viridis", "alpha": 0.5},
            }
        ]
    }
    result_scatter = execution_service.run_workflow(workflow_scatter)
    assert result_scatter["status"] == "success", f"Scatter failed: {result_scatter.get('error')}"

    # Step 4: savefig
    workflow_save = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Figure.savefig",
                "inputs": {"figure": fig_ref},
                "params": {"format": "png"},
            }
        ]
    }
    result_save = execution_service.run_workflow(workflow_save)
    assert result_save["status"] == "success"

    status_save = execution_service.get_run_status(result_save["run_id"])
    plot_ref = status_save["outputs"]["plot"]
    assert plot_ref["type"] == "PlotRef"

    # Verify file exists via URI
    uri = plot_ref["uri"]
    assert uri.startswith("file://")
    from urllib.parse import unquote, urlparse

    parsed_path = unquote(urlparse(uri).path)
    # Handle Windows paths like /C:/Users/...
    if parsed_path.startswith("/") and len(parsed_path) > 2 and parsed_path[2] == ":":
        parsed_path = parsed_path[1:]
    assert Path(parsed_path).exists()


@pytest.mark.integration
def test_scatter_empty_table(execution_service, tmp_path):
    """T023: Test scatter plot with empty TableRef (FR-017)."""

    # Create an empty CSV
    csv_path = tmp_path / "empty.csv"
    df = pd.DataFrame(columns=["x", "y"])
    df.to_csv(csv_path, index=False)

    # Load TableRef
    workflow_load = {"steps": [{"fn_id": "base.io.table.load", "params": {"path": str(csv_path)}}]}
    result_load = execution_service.run_workflow(workflow_load)
    table_ref = execution_service.get_run_status(result_load["run_id"])["outputs"]["table"]

    # subplots
    workflow_fig = {"steps": [{"fn_id": "base.matplotlib.pyplot.subplots"}]}
    result_fig = execution_service.run_workflow(workflow_fig)
    ax_ref = execution_service.get_run_status(result_fig["run_id"])["outputs"]["axes"]

    # scatter
    workflow_scatter = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.scatter",
                "inputs": {"axes": ax_ref, "x": "x", "y": "y", "table": table_ref},
            }
        ]
    }
    result_scatter = execution_service.run_workflow(workflow_scatter)
    assert result_scatter["status"] == "success"
