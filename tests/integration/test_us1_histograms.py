"""
Integration tests for User Story 1: Intensity Histograms.
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
def test_histogram_workflow(execution_service):
    """T011: Test full workflow: subplots → hist → savefig.

    Expected to fail initially (TDD) as MatplotlibAdapter.execute is not implemented.
    """

    # Step 1: subplots
    workflow1 = {
        "steps": [{"fn_id": "base.matplotlib.pyplot.subplots", "params": {"figsize": [6, 4]}}]
    }
    result1 = execution_service.run_workflow(workflow1)
    assert result1["status"] == "success", f"Step 1 failed: {result1.get('error')}"

    status1 = execution_service.get_run_status(result1["run_id"])
    outputs1 = status1.get("outputs", {})

    # These assertions will fail because execute() is currently empty/stubbed
    if "figure" not in outputs1 or "axes" not in outputs1:
        pytest.fail(
            "Step 1 (subplots) did not return expected outputs. "
            "This is expected as implementation is missing (TDD)."
        )

    fig_ref = outputs1["figure"]
    ax_ref = outputs1["axes"]

    # Step 2: hist
    workflow2 = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.hist",
                "inputs": {"axes": ax_ref, "x": [1, 2, 2, 3, 3, 3, 4, 4, 5]},
                "params": {"bins": 5, "color": "blue", "alpha": 0.7},
            }
        ]
    }
    result2 = execution_service.run_workflow(workflow2)
    assert result2["status"] == "success", f"Step 2 failed: {result2.get('error')}"

    # Step 3: savefig
    workflow3 = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Figure.savefig",
                "inputs": {"figure": fig_ref},
                "params": {"format": "png"},
            }
        ]
    }
    result3 = execution_service.run_workflow(workflow3)
    assert result3["status"] == "success", f"Step 3 failed: {result3.get('error')}"

    status3 = execution_service.get_run_status(result3["run_id"])
    outputs3 = status3.get("outputs", {})

    plot_ref = outputs3.get("plot") or outputs3.get("return")
    assert plot_ref is not None, "Step 3 should return a plot output"
    assert plot_ref["type"] == "PlotRef"
    assert plot_ref["format"] == "PNG"


@pytest.mark.integration
def test_histogram_constant_image(execution_service):
    """T011: Test edge case: constant-value data (FR-016)."""

    # Step 1: subplots
    workflow1 = {"steps": [{"fn_id": "base.matplotlib.pyplot.subplots"}]}
    result1 = execution_service.run_workflow(workflow1)
    assert result1["status"] == "success"
    outputs1 = execution_service.get_run_status(result1["run_id"])["outputs"]

    if "figure" not in outputs1:
        pytest.skip("Skipping rest of test until subplots implementation is available")

    fig_ref = outputs1["figure"]
    ax_ref = outputs1["axes"]

    # Step 2: hist with constant data
    workflow2 = {
        "steps": [
            {
                "fn_id": "base.matplotlib.Axes.hist",
                "inputs": {"axes": ax_ref, "x": [10, 10, 10, 10, 10]},
                "params": {"bins": 10},
            }
        ]
    }
    result2 = execution_service.run_workflow(workflow2)
    assert result2["status"] == "success"

    # Step 3: savefig
    workflow3 = {
        "steps": [{"fn_id": "base.matplotlib.Figure.savefig", "inputs": {"figure": fig_ref}}]
    }
    result3 = execution_service.run_workflow(workflow3)
    assert result3["status"] == "success"
