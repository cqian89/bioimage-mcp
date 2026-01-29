"""
Integration tests for T043/T044: Axes styling, annotations, and colorbar.
"""

from pathlib import Path

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.fixture
def execution_service(tmp_path: Path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

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
def test_axes_styling_workflow(execution_service):
    """T043: Integration test for axes styling (set_title, set_xlabel, set_ylabel, grid, limits)."""

    # Step 1: Create subplots
    result1 = execution_service.run_workflow(
        {"steps": [{"id": "base.matplotlib.pyplot.subplots", "params": {"nrows": 1, "ncols": 1}}]}
    )
    assert result1["status"] == "success", f"subplots failed: {result1.get('error')}"
    outputs1 = execution_service.get_run_status(result1["run_id"])["outputs"]

    fig_ref = outputs1["figure"]
    ax_ref = outputs1["axes"]

    # Step 2: Set title
    result_title = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.set_title",
                    "inputs": {"axes": ax_ref},
                    "params": {"label": "Styled Axes Test"},
                }
            ]
        }
    )
    assert result_title["status"] == "success", f"set_title failed: {result_title.get('error')}"

    # Step 3: Set x and y labels
    result_xlabel = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.set_xlabel",
                    "inputs": {"axes": ax_ref},
                    "params": {"xlabel": "X Axis Label"},
                }
            ]
        }
    )
    assert result_xlabel["status"] == "success", f"set_xlabel failed: {result_xlabel.get('error')}"

    result_ylabel = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.set_ylabel",
                    "inputs": {"axes": ax_ref},
                    "params": {"ylabel": "Y Axis Label"},
                }
            ]
        }
    )
    assert result_ylabel["status"] == "success", f"set_ylabel failed: {result_ylabel.get('error')}"

    # Step 4: Enable grid
    result_grid = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.grid",
                    "inputs": {"axes": ax_ref},
                    "params": {"visible": True, "linestyle": "--"},
                }
            ]
        }
    )
    assert result_grid["status"] == "success", f"grid failed: {result_grid.get('error')}"

    # Step 5: Set xlim and ylim
    result_xlim = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.set_xlim",
                    "inputs": {"axes": ax_ref},
                    "params": {"left": 0, "right": 100},
                }
            ]
        }
    )
    assert result_xlim["status"] == "success", f"set_xlim failed: {result_xlim.get('error')}"

    result_ylim = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.set_ylim",
                    "inputs": {"axes": ax_ref},
                    "params": {"bottom": 0, "top": 50},
                }
            ]
        }
    )
    assert result_ylim["status"] == "success", f"set_ylim failed: {result_ylim.get('error')}"

    # Step 6: Save figure
    result_save = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Figure.savefig",
                    "inputs": {"figure": fig_ref},
                    "params": {"format": "png"},
                }
            ]
        }
    )
    assert result_save["status"] == "success", f"savefig failed: {result_save.get('error')}"

    outputs_save = execution_service.get_run_status(result_save["run_id"])["outputs"]
    plot_ref = outputs_save.get("plot") or outputs_save.get("return")
    assert plot_ref is not None
    assert plot_ref["type"] == "PlotRef"
    assert plot_ref["format"] == "PNG"


@pytest.mark.integration
def test_annotation_and_legend(execution_service):
    """T043: Integration test for annotations and legend (FR-012, FR-013)."""

    # Step 1: Create subplots
    result1 = execution_service.run_workflow({"steps": [{"id": "base.matplotlib.pyplot.subplots"}]})
    assert result1["status"] == "success"
    outputs1 = execution_service.get_run_status(result1["run_id"])["outputs"]
    fig_ref = outputs1["figure"]
    ax_ref = outputs1["axes"]

    # Step 2: Plot a line with label
    result_plot = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.plot",
                    "inputs": {"axes": ax_ref},
                    "params": {"x": [1, 2, 3, 4, 5], "y": [1, 4, 9, 16, 25], "label": "y = x^2"},
                }
            ]
        }
    )
    assert result_plot["status"] == "success", f"plot failed: {result_plot.get('error')}"

    # Step 3: Add legend
    result_legend = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.legend",
                    "inputs": {"axes": ax_ref},
                    "params": {},
                }
            ]
        }
    )
    assert result_legend["status"] == "success", f"legend failed: {result_legend.get('error')}"

    # Step 4: Add annotation
    result_annotate = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.annotate",
                    "inputs": {"axes": ax_ref},
                    "params": {"text": "Peak", "xy": [5, 25], "xytext": [4, 20]},
                }
            ]
        }
    )
    assert result_annotate["status"] == "success", (
        f"annotate failed: {result_annotate.get('error')}"
    )

    # Step 5: Add text
    result_text = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Axes.text",
                    "inputs": {"axes": ax_ref},
                    "params": {"x": 1, "y": 20, "s": "Quadratic Curve"},
                }
            ]
        }
    )
    assert result_text["status"] == "success", f"text failed: {result_text.get('error')}"

    # Step 6: Save
    result_save = execution_service.run_workflow(
        {
            "steps": [
                {
                    "id": "base.matplotlib.Figure.savefig",
                    "inputs": {"figure": fig_ref},
                    "params": {"format": "png"},
                }
            ]
        }
    )
    assert result_save["status"] == "success"

    outputs_save = execution_service.get_run_status(result_save["run_id"])["outputs"]
    plot_ref = outputs_save.get("plot") or outputs_save.get("return")
    assert plot_ref is not None
    assert plot_ref["type"] == "PlotRef"
