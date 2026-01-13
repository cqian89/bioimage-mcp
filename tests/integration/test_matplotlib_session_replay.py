"""Integration test for matplotlib session replay (T046).

Verifies that a plotting workflow (subplots -> hist -> savefig)
can be exported and replayed deterministically.
"""

import pytest
from pathlib import Path
import os
import json
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


@pytest.fixture
def services(tmp_path):
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[Path("tools").resolve()],  # Use real tools
        fs_allowlist_read=[str(tmp_path), os.getcwd()],
        fs_allowlist_write=[str(tmp_path)],
    )

    artifact_store = ArtifactStore(config)
    session_store = SessionStore()  # In-memory
    session_manager = SessionManager(session_store, config)
    execution_service = ExecutionService(config, artifact_store=artifact_store)
    interactive_service = InteractiveExecutionService(session_manager, execution_service)

    yield interactive_service, execution_service, artifact_store

    execution_service.close()
    artifact_store.close()


@pytest.mark.requires_env("bioimage-mcp-base")
def test_matplotlib_session_replay(services, tmp_path):
    interactive, execution, artifact_store = services
    session_id = "test-matplotlib-replay"

    # 1. Create subplots
    res_subplots = interactive.call_tool(
        session_id=session_id,
        fn_id="base.matplotlib.pyplot.subplots",
        inputs={},
        params={"nrows": 1, "ncols": 1},
    )
    assert res_subplots["status"] == "success"
    fig_ref = res_subplots["outputs"]["figure"]
    ax_ref = res_subplots["outputs"]["axes"]

    # 2. Plot histogram
    res_hist = interactive.call_tool(
        session_id=session_id,
        fn_id="base.matplotlib.Axes.hist",
        inputs={"axes": ax_ref},
        params={"x": [1, 2, 2, 3, 3, 3, 4, 4, 5], "bins": 5},
    )
    assert res_hist["status"] == "success"

    # 2b. Set labels (T049: test generic_op recording)
    res_label = interactive.call_tool(
        session_id=session_id,
        fn_id="base.matplotlib.Axes.set_xlabel",
        inputs={"axes": ax_ref},
        params={"xlabel": "Values"},
    )
    if res_label["status"] != "success":
        print(f"set_xlabel failed: {res_label.get('error')}")
    assert res_label["status"] == "success"

    # 3. Save figure
    res_save = interactive.call_tool(
        session_id=session_id,
        fn_id="base.matplotlib.Figure.savefig",
        inputs={"figure": fig_ref},
        params={"format": "png"},
    )
    assert res_save["status"] == "success"
    plot_ref = res_save["outputs"]["plot"]

    # Convert file:// URI to path
    plot_uri = plot_ref["uri"]
    assert plot_uri.startswith("file://")
    from urllib.parse import unquote, urlparse

    plot_path = Path(unquote(urlparse(plot_uri).path))
    # Handle Windows paths if necessary
    if os.name == "nt" and str(plot_path).startswith("/"):
        plot_path = Path(str(plot_path)[1:])

    assert plot_path.exists()

    # Capture original plot size for comparison
    original_size = plot_path.stat().st_size

    # 4. Export session
    export_res = interactive.export_session(session_id)
    workflow_ref = export_res["workflow_ref"]

    # 5. Replay session
    # Replay returns a SessionReplayResponse model-dumped
    replay_res = interactive.replay_session(
        workflow_ref=workflow_ref,
        inputs={},  # No external inputs
    )

    assert replay_res["status"] in ("success", "running", "ready")

    # Since replay runs synchronously in the current implementation of SessionService.replay_session,
    # it should be finished.

    # We need to find the output of the replayed savefig.
    # Replay produces a new session.
    replay_session_id = replay_res["session_id"]
    steps = interactive.session_manager.store.list_step_attempts(replay_session_id)

    # Find the savefig step in the replay
    savefig_step = next(s for s in steps if s.fn_id == "base.matplotlib.Figure.savefig")
    assert savefig_step.status == "succeeded"

    replayed_plot_ref = savefig_step.outputs["plot"]
    replayed_plot_uri = replayed_plot_ref["uri"]
    replayed_plot_path = Path(unquote(urlparse(replayed_plot_uri).path))
    if os.name == "nt" and str(replayed_plot_path).startswith("/"):
        replayed_plot_path = Path(str(replayed_plot_path)[1:])

    assert replayed_plot_path.exists()
    assert replayed_plot_path != plot_path

    # Check if replayed plot has similar size (determinism)
    # Matplotlib output might not be byte-for-byte identical due to timestamps or other metadata,
    # but for a simple plot it should be very close.
    assert replayed_plot_path.stat().st_size > 0
    # For PNG, small differences are possible, but size should be comparable.
    # Using 10% tolerance for now if needed, but usually it's very close.
    assert abs(replayed_plot_path.stat().st_size - original_size) < original_size * 0.1
