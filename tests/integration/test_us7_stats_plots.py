import pytest
import pandas as pd
from pathlib import Path
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
def test_us7_boxplot_violinplot_with_grouping(execution_service, tmp_path):
    """T035: Integration Test: Load grouped data, create box/violin plots."""
    # 1. Create temporary CSV with grouped data
    data = {
        "treatment": ["A"] * 10 + ["B"] * 10 + ["C"] * 10,
        "value": [1.0, 1.2, 1.1, 0.9, 1.0, 1.1, 1.3, 0.8, 1.2, 1.0]
        + [2.0, 2.2, 2.1, 1.9, 2.0, 2.1, 2.3, 1.8, 2.2, 2.0]
        + [1.5, 1.7, 1.6, 1.4, 1.5, 1.6, 1.8, 1.3, 1.7, 1.5],
    }
    csv_path = tmp_path / "grouped_data.csv"
    pd.DataFrame(data).to_csv(csv_path, index=False)

    # Step 1: Load TableRef
    workflow_load = {"steps": [{"fn_id": "base.io.table.load", "params": {"path": str(csv_path)}}]}
    result_load = execution_service.run_workflow(workflow_load)
    assert result_load["status"] == "success"
    table_ref = execution_service.get_run_status(result_load["run_id"])["outputs"]["table"]

    # Step 2: subplots
    workflow_fig = {
        "steps": [{"fn_id": "base.matplotlib.pyplot.subplots", "params": {"nrows": 1, "ncols": 2}}]
    }
    result_fig = execution_service.run_workflow(workflow_fig)
    assert result_fig["status"] == "success"
    outputs_fig = execution_service.get_run_status(result_fig["run_id"])["outputs"]
    fig_ref = outputs_fig["figure"]
    ax1_ref = outputs_fig["axes_0"]
    ax2_ref = outputs_fig["axes_1"]

    # Step 3: boxplot on ax1
    workflow_boxplot = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.boxplot",
                "inputs": {"axes": ax1_ref, "x": "value", "table": table_ref},
                "params": {"positions": "treatment", "patch_artist": True},
            }
        ]
    }
    result_boxplot = execution_service.run_workflow(workflow_boxplot)
    assert result_boxplot["status"] == "success", f"Boxplot failed: {result_boxplot.get('error')}"

    # Step 4: violinplot on ax2
    workflow_violin = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.violinplot",
                "inputs": {"axes": ax2_ref, "dataset": "value", "table": table_ref},
                "params": {"positions": "treatment", "showmeans": True},
            }
        ]
    }
    result_violin = execution_service.run_workflow(workflow_violin)
    assert result_violin["status"] == "success", f"Violinplot failed: {result_violin.get('error')}"

    # Step 5: savefig
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
    if parsed_path.startswith("/") and len(parsed_path) > 2 and parsed_path[2] == ":":
        parsed_path = parsed_path[1:]
    assert Path(parsed_path).exists()
