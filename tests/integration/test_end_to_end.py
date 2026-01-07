from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore


@pytest.fixture
def end_to_end_context(mcp_services, tmp_path):
    config = mcp_services["config"]
    discovery = mcp_services["discovery"]
    execution = mcp_services["execution"]
    artifact_store = mcp_services["artifact_store"]

    session_store = SessionStore(config)
    session_manager = SessionManager(session_store, config)
    interactive = InteractiveExecutionService(session_manager, execution, discovery=discovery)

    return {
        "config": config,
        "discovery": discovery,
        "execution": execution,
        "artifact_store": artifact_store,
        "session_manager": session_manager,
        "interactive": interactive,
        "tmp_path": tmp_path,
    }


@pytest.mark.integration
def test_discover_describe_run_flow(end_to_end_context, monkeypatch):
    """T102: Complete flow: list -> describe -> run -> check outputs."""
    ctx = end_to_end_context
    discovery: DiscoveryService = ctx["discovery"]
    interactive: InteractiveExecutionService = ctx["interactive"]

    # Mock execution for speed
    def mock_execute_step(*args, **kwargs):
        work_dir = kwargs.get("work_dir") or Path("/tmp")
        out_path = Path(work_dir) / "output.tif"
        if not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"dummy")
        return (
            {"ok": True, "outputs": {"output": {"type": "BioImageRef", "path": str(out_path)}}},
            "Mock success",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", mock_execute_step)

    # 1. list_tools() to discover environments
    envs = discovery.list_tools()
    assert "items" in envs
    assert len(envs["items"]) > 0
    # Check if 'base' is in envs (tools. prefix is stripped in hierarchy)
    tool_ids = [item["id"] for item in envs["items"]]
    assert "base" in tool_ids

    # 2. list_tools(path="base") to find functions
    # Based on server.py, list_tools calls discovery.list_tools
    funcs = discovery.list_tools(path="base", flatten=True)
    assert "items" in funcs
    fn_ids = [item["id"] for item in funcs["items"]]
    # Flattened list should contain the function
    assert any(fn_id.startswith("base.") for fn_id in fn_ids)

    # Let's pick a function
    target_fn = "base.io.bioimage.load"
    assert target_fn in fn_ids

    # 3. describe_function(fn_id="base.xarray.squeeze") to get full details
    details = discovery.describe_function(fn_id=target_fn)
    assert details["id"] == target_fn
    assert "params_schema" in details

    # 4. run_function(fn_id="base.xarray.squeeze", inputs={...}, params={...})
    # run_function in server.py calls interactive.call_tool
    session_id = f"test-session-{uuid.uuid4()}"
    run_result = interactive.call_tool(
        session_id=session_id,
        fn_id=target_fn,
        inputs={"image": {"type": "BioImageRef", "ref_id": "input-ref"}},
        params={"dim": "Z"},
    )

    # 5. Verify outputs contain valid ArtifactRefs
    assert run_result["status"] == "success"
    assert "outputs" in run_result
    assert "output" in run_result["outputs"]
    assert run_result["outputs"]["output"]["type"] == "BioImageRef"


@pytest.mark.integration
def test_search_describe_run_flow(end_to_end_context, monkeypatch):
    """T103: Complete flow: search -> describe -> run."""
    ctx = end_to_end_context
    discovery: DiscoveryService = ctx["discovery"]
    interactive: InteractiveExecutionService = ctx["interactive"]

    # Mock execution
    def mock_execute_step(*args, **kwargs):
        work_dir = kwargs.get("work_dir") or Path("/tmp")
        out_path = Path(work_dir) / "output.tif"
        if not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"dummy")
        return (
            {"ok": True, "outputs": {"output": {"type": "BioImageRef", "path": str(out_path)}}},
            "Mock success",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", mock_execute_step)

    # 1. search_functions(query="squeeze") to find functions
    search_results = discovery.search_functions(query="squeeze")
    assert "results" in search_results
    assert len(search_results["results"]) > 0

    top_result = search_results["results"][0]
    fn_id = top_result["id"]

    # 2. describe the top result
    details = discovery.describe_function(fn_id=fn_id)
    assert details["id"] == fn_id

    # 3. run the function
    session_id = f"test-session-{uuid.uuid4()}"
    run_result = interactive.call_tool(
        session_id=session_id,
        fn_id=fn_id,
        inputs={"image": {"type": "BioImageRef", "ref_id": "input-ref"}},
        params={},
    )

    # 4. Verify success
    assert run_result["status"] == "success"


@pytest.mark.integration
def test_session_export_replay_flow(end_to_end_context, monkeypatch):
    """T104: Complete flow: run multiple steps -> export -> replay with new data."""
    ctx = end_to_end_context
    interactive: InteractiveExecutionService = ctx["interactive"]

    # Mock execution
    def mock_execute_step(*args, **kwargs):
        # Return a different output each time to simulate change
        work_dir = kwargs.get("work_dir") or Path("/tmp")
        out_path = Path(work_dir) / f"output-{uuid.uuid4().hex[:8]}.tif"
        if not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"dummy")
        return (
            {
                "ok": True,
                "outputs": {"output": {"type": "BioImageRef", "path": str(out_path)}},
            },
            "Mock success",
            0,
        )

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", mock_execute_step)

    session_id = "s1"

    # 1. run(session_id="s1", ...) step 1
    res1 = interactive.call_tool(
        session_id=session_id,
        fn_id="base.xarray.squeeze",
        inputs={"image": {"type": "BioImageRef", "ref_id": "orig-input"}},
        params={"dim": "Z"},
    )
    assert res1["status"] == "success"
    output1 = res1["outputs"]["output"]

    # 2. run(session_id="s1", ...) step 2 using step 1 output
    res2 = interactive.call_tool(
        session_id=session_id,
        fn_id="base.xarray.expand_dims",
        inputs={"image": output1},
        params={"dim": "T", "axis": 0},
    )
    assert res2["status"] == "success"

    # 3. export_session(session_id="s1")
    export_response = interactive.export_session(session_id=session_id)
    assert export_response["session_id"] == session_id
    export_result = export_response["workflow_ref"]
    assert "ref_id" in export_result
    assert export_result["type"] == "NativeOutputRef"

    # 4. replay_session with new external inputs
    # Replay session wants inputs to be a map of original_ref_id -> new_ref_id
    replay_inputs = {"orig-input": "new-input-ref"}
    replay_result = interactive.replay_session(workflow_ref=export_result, inputs=replay_inputs)

    # 5. Verify replay produces outputs
    assert "run_id" in replay_result
    assert replay_result["status"] in {"success", "running", "queued"}


@pytest.mark.integration
def test_run_crash_includes_log(end_to_end_context, monkeypatch):
    """T120: When function crashes, run should return failed with log_ref."""
    ctx = end_to_end_context
    interactive: InteractiveExecutionService = ctx["interactive"]

    # Mock execution failure
    def mock_execute_step(*args, **kwargs):
        return {"ok": False, "error": {"message": "Crash!"}}, "Execution failed", 1

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", mock_execute_step)

    session_id = "crash-session"
    run_result = interactive.call_tool(
        session_id=session_id,
        fn_id="base.xarray.squeeze",
        inputs={"image": {"type": "BioImageRef", "ref_id": "input-ref"}},
        params={},
    )

    # 1. Run a function that will crash
    # 2. Verify status == "failed"
    assert run_result["status"] == "failed"

    # 3. Verify log_ref is present
    assert "log_ref" in run_result
    assert run_result["log_ref"]["type"] == "LogRef"


@pytest.mark.integration
def test_concurrent_runs_in_session(end_to_end_context, monkeypatch):
    """T121: Multiple runs in same session should work (append-only)."""
    ctx = end_to_end_context
    interactive: InteractiveExecutionService = ctx["interactive"]

    # Mock execution
    def mock_execute_step(*args, **kwargs):
        return {"ok": True, "outputs": {}}, "Mock success", 0

    monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", mock_execute_step)

    session_id = "concurrent-session"

    # 1. Start run A in session
    # (Since our mock is synchronous, they will happen sequentially in this test,
    # but the point is that the session manager should handle them)
    res_a = interactive.call_tool(
        session_id=session_id,
        fn_id="base.xarray.squeeze",
        inputs={"image": {"type": "BioImageRef", "ref_id": "input-A"}},
        params={},
    )

    # 2. Start run B in same session
    res_b = interactive.call_tool(
        session_id=session_id,
        fn_id="base.xarray.expand_dims",
        inputs={"image": {"type": "BioImageRef", "ref_id": "input-B"}},
        params={"dim": "Z"},
    )

    # 3. Both should complete successfully
    assert res_a["status"] == "success"
    assert res_b["status"] == "success"

    # Verify both steps are in session
    session_store: SessionStore = ctx["session_manager"].store
    steps = session_store.list_step_attempts(session_id)
    assert len(steps) == 2
    assert steps[0].fn_id == "base.xarray.squeeze"
    assert steps[1].fn_id == "base.xarray.expand_dims"
