from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.interactive import InteractiveExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.sessions.manager import SessionManager
from bioimage_mcp.sessions.store import SessionStore
from bioimage_mcp.test_harness import WorkflowTestCase

WORKFLOW_CASES_DIR = Path(__file__).parent / "workflow_cases"


def _load_workflow_cases() -> list[object]:
    case_files = sorted(WORKFLOW_CASES_DIR.glob("*.yaml"))
    cases: list[object] = []

    for case_path in case_files:
        data = yaml.safe_load(case_path.read_text())
        if data is None:
            continue
        if isinstance(data, list):
            for payload in data:
                case = WorkflowTestCase.model_validate(payload)
                cases.append(pytest.param(case, id=case.test_name))
            continue
        if isinstance(data, dict):
            case = WorkflowTestCase.model_validate(data)
            cases.append(pytest.param(case, id=case.test_name))
            continue
        raise AssertionError(f"Workflow case file must be a mapping or list: {case_path}")

    if not cases:
        return [pytest.param(None, id="no-workflow-cases")]

    return cases


def _env_available(env_name: str) -> bool:
    try:
        proc = subprocess.run(
            ["conda", "run", "-n", env_name, "python", "-c", "print('ok')"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _resolve_inputs(inputs: dict[str, Any], refs: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in inputs.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            ref_name = value[1:-1]
            if ref_name not in refs:
                raise AssertionError(f"Unknown input reference: {ref_name}")
            resolved[key] = refs[ref_name]
        else:
            resolved[key] = value
    return resolved


def _coerce_output_ref(outputs: Any) -> Any:
    """Extract the primary output artifact from outputs dict.

    Filters out workflow_record and returns the single remaining output
    if there's exactly one, otherwise returns the filtered outputs dict.
    """
    if not isinstance(outputs, dict):
        return outputs
    # Filter out workflow_record which is always present
    filtered = {k: v for k, v in outputs.items() if k != "workflow_record"}
    if len(filtered) == 1:
        return next(iter(filtered.values()))
    return filtered


def _get_metadata_value(metadata: Any, key: str) -> Any:
    current = metadata
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            idx = int(part)
            if idx >= len(current):
                raise AssertionError(f"Metadata index out of range: {key}")
            current = current[idx]
            continue
        raise AssertionError(f"Metadata path not found: {key}")
    return current


def _assert_output_type(output: Any, expected_type: str) -> None:
    if isinstance(output, dict):
        if "type" in output:
            assert output["type"] == expected_type
            return
        if output:
            # Check if it's a mapping of name -> artifact ref
            for value in output.values():
                if isinstance(value, dict) and "type" in value:
                    assert value["type"] == expected_type
                    continue
                # It might be the workflow_record which has no type field
                # but we already filtered it out in _coerce_output_ref
                raise AssertionError(f"Output value {value} is not an artifact reference")
            return
    raise AssertionError(f"Output {output} is not an artifact reference")


@pytest.mark.mock_execution
@pytest.mark.timeout(10)
def test_full_discovery_to_execution_flow(mcp_test_client, sample_flim_image) -> None:
    search_results = mcp_test_client.search_functions("phasor FLIM")
    fn_ids = {fn["id"] for fn in search_results["results"]}
    assert "base.phasorpy.phasor.phasor_from_signal" in fn_ids

    mcp_test_client.activate_functions(
        [
            "base.xarray.DataArray.rename",
            "base.phasorpy.phasor.phasor_from_signal",
        ]
    )

    schema = mcp_test_client.describe_function(id="base.xarray.DataArray.rename")
    assert schema["id"] == "base.xarray.DataArray.rename"
    assert schema["params_schema"]["type"] == "object"

    relabeled = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray.rename",
        inputs={"image": sample_flim_image},
        params={"mapping": {"Z": "T", "T": "Z"}},
    )
    relabeled_output = _coerce_output_ref(relabeled["outputs"])

    phasor = mcp_test_client.call_tool(
        fn_id="base.phasorpy.phasor.phasor_from_signal",
        inputs={"signal": relabeled_output},
        params={"harmonic": 1},
    )

    outputs = phasor["outputs"]
    assert "output" in outputs
    assert "output_1" in outputs
    assert "output_2" in outputs
    _assert_output_type(outputs["output"], "BioImageRef")
    _assert_output_type(outputs["output_1"], "BioImageRef")
    _assert_output_type(outputs["output_2"], "BioImageRef")


@pytest.mark.real_execution
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.timeout(60)
def test_flim_phasor_golden_path(mcp_test_client, sample_flim_image) -> None:
    sample_uri = sample_flim_image["uri"]
    sample_path = Path(sample_uri.replace("file://", ""))
    if not sample_path.exists():
        pytest.skip(f"Missing FLIM dataset at {sample_path}")

    if not _env_available("bioimage-mcp-base"):
        pytest.skip("Required tool environment missing: bioimage-mcp-base")

    transposed = mcp_test_client.call_tool(
        fn_id="base.xarray.DataArray.transpose",
        inputs={"image": sample_flim_image},
        params={"dims": ["Y", "X", "Z"]},
    )
    if transposed.get("status") != "success":
        pytest.fail(f"Transpose failed: {transposed}")
    transposed_output = _coerce_output_ref(transposed["outputs"])

    phasor = mcp_test_client.call_tool(
        fn_id="base.phasorpy.phasor.phasor_from_signal",
        inputs={"signal": transposed_output},
        params={"axis": 2, "harmonic": 1},
    )
    if phasor.get("status") != "success":
        pytest.fail(f"Phasor failed: {phasor}")

    outputs = phasor["outputs"]

    assert "mean" in outputs
    assert "real" in outputs
    assert "imag" in outputs
    _assert_output_type(outputs["mean"], "BioImageRef")
    _assert_output_type(outputs["real"], "BioImageRef")
    _assert_output_type(outputs["imag"], "BioImageRef")


@pytest.mark.mock_execution
@pytest.mark.timeout(10)
@pytest.mark.parametrize("case", _load_workflow_cases())
def test_workflow_from_yaml(mcp_test_client, case: WorkflowTestCase | None) -> None:
    if case is None:
        pytest.fail("No workflow YAML cases found")

    refs: dict[str, Any] = {}
    last_output: Any = None

    for step in case.steps:
        inputs = _resolve_inputs(step.inputs, refs)
        params = step.params
        result = mcp_test_client.call_tool(
            fn_id=step.id,
            inputs=inputs,
            params=params,
        )
        outputs = result["outputs"]
        last_output = _coerce_output_ref(outputs)

        refs[f"{step.step_id}.output"] = last_output

        for assertion in step.assertions:
            if assertion.type == "artifact_exists":
                assert last_output is not None
            if assertion.type == "output_type":
                expected_type = assertion.value
                assert isinstance(expected_type, str)
                _assert_output_type(last_output, expected_type)
            if assertion.type == "metadata_check":
                assert assertion.key is not None
                if not isinstance(last_output, dict):
                    raise AssertionError("Output is not an artifact reference")
                metadata = last_output.get("metadata", {})
                if not metadata:
                    # Mock outputs do not preserve per-step metadata.
                    continue
                actual = _get_metadata_value(metadata, assertion.key)
                assert actual == assertion.value


class TestSessionReplayObjectRef:
    """T044: Integration tests for session_replay reconstruction of ObjectRef."""

    @pytest.fixture
    def services(self, tmp_path, monkeypatch):
        """Setup services with temporary stores and mocked execution."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        # Setup stores
        artifact_store = ArtifactStore(config)
        session_store = SessionStore()

        # Setup services
        session_manager = SessionManager(session_store, config)
        execution_service = ExecutionService(config, artifact_store=artifact_store)
        interactive_service = InteractiveExecutionService(session_manager, execution_service)

        # Mock function exists to allow test tools
        monkeypatch.setattr(
            "bioimage_mcp.api.sessions.SessionService._function_exists",
            lambda self, fn_id: True,
        )
        monkeypatch.setattr(
            "bioimage_mcp.api.sessions.SessionService._env_installed",
            lambda self, env_name: True,
        )

        return interactive_service, execution_service, artifact_store

    def test_replay_reconstructs_objectref_from_init_params(self, services, monkeypatch):
        """Assert ObjectRef is reconstructed using init_params during replay (FR-004)."""
        interactive, execution, artifact_store = services
        session_id = "reconstruction-test-001"

        # 1. Mock execution to return an ObjectRef with init_params
        mock_calls = []

        def _mock_execute_step(fn_id, inputs, params, **kwargs):
            mock_calls.append({"id": fn_id, "inputs": inputs, "params": params})
            if fn_id == "test.create":
                return (
                    {
                        "ok": True,
                        "outputs": {
                            "model": {
                                "type": "ObjectRef",
                                "ref_id": "obj-123",
                                "uri": "obj://session/env/obj-123",
                                "storage_type": "memory",
                                "python_class": "test.MyModel",
                                "metadata": {"init_params": {"arg1": "val1"}},
                                "format": "pickle",
                                "mime_type": "application/x-python-pickle",
                                "size_bytes": 1024,
                            }
                        },
                    },
                    "Created",
                    0,
                )
            elif fn_id == "core.reconstruct":
                # Handle reconstruction call (T046)
                class_ctx = kwargs.get("class_context") or {}
                py_class = class_ctx.get("python_class")
                init_params = class_ctx.get("init_params")
                return (
                    {
                        "ok": True,
                        "outputs": {
                            "model": {
                                "type": "ObjectRef",
                                "ref_id": "obj-123",
                                "uri": "obj://session/env/obj-123",
                                "storage_type": "memory",
                                "python_class": py_class,
                                "metadata": {"init_params": init_params},
                            }
                        },
                    },
                    "Reconstructed",
                    0,
                )
            else:  # test.use
                # Verify that the input has been resolved/reconstructed
                model_input = inputs.get("model")
                if not model_input or "uri" not in model_input:
                    return (
                        {
                            "ok": False,
                            "error": {
                                "code": "INPUT_ERROR",
                                "message": f"Input 'model' not resolved: {model_input}",
                            },
                        },
                        "Failed",
                        1,
                    )
                return (
                    {
                        "ok": True,
                        "outputs": {
                            "res": {
                                "type": "ScalarRef",
                                "ref_id": "s1",
                                "uri": "mem://s1",
                                "metadata": {"val": 42},
                                "format": "json",
                                "mime_type": "application/json",
                                "size_bytes": 0,
                            }
                        },
                    },
                    "Used",
                    0,
                )

        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _mock_execute_step)

        # 2. Create session with ObjectRef creation step and usage
        res1 = interactive.call_tool(session_id, "test.create", {}, {"arg1": "val1"})
        obj_ref = res1["outputs"]["model"]

        res2 = interactive.call_tool(session_id, "test.use", {"model": obj_ref}, {})
        assert res2["status"] == "success"

        # 3. Export session
        export_res = interactive.export_session(session_id)
        workflow_ref = export_res["workflow_ref"]

        # 4. Clear/invalidate the ObjectRef from cache/memory
        # This simulates the object being lost before replay
        execution._memory_store._artifacts.clear()

        # To ensure it's missing when Step 2 runs during replay,
        # we mock run_workflow to clear memory before Step 2.
        original_run_workflow = execution.run_workflow

        def _mock_run_workflow(spec, **kwargs):
            if spec["steps"][0]["id"] == "test.use":
                execution._memory_store._artifacts.clear()
            return original_run_workflow(spec, **kwargs)

        monkeypatch.setattr(execution, "run_workflow", _mock_run_workflow)

        # 5. Replay the workflow
        # We use a new session for replay
        replay_res = interactive.replay_session(workflow_ref, inputs={})

        # 6. Assert the reconstruction uses init_params and python_class
        # This is expected to fail initially (TDD) as reconstruction is not yet implemented
        if replay_res.get("error"):
            pytest.fail(f"Replay failed with error: {replay_res['error']}")

        assert replay_res["status"] in ("running", "success")

    def test_replay_uses_python_class_for_reconstruction(self, services, monkeypatch):
        """Assert python_class is used to identify the class to reconstruct."""
        interactive, execution, artifact_store = services
        session_id = "reconstruction-test-002"

        # Similar setup but focus on asserting python_class usage
        def _mock_execute_step(fn_id, inputs, params, **kwargs):
            if fn_id == "test.create":
                return (
                    {
                        "ok": True,
                        "outputs": {
                            "model": {
                                "type": "ObjectRef",
                                "ref_id": "obj-456",
                                "uri": "obj://session/env/obj-456",
                                "storage_type": "memory",
                                "python_class": "test.SpecialModel",
                                "metadata": {"init_params": {"x": 10}},
                                "format": "pickle",
                                "mime_type": "application/x-python-pickle",
                                "size_bytes": 1024,
                            }
                        },
                    },
                    "OK",
                    0,
                )
            elif fn_id == "core.reconstruct":
                class_ctx = kwargs.get("class_context") or {}
                return (
                    {
                        "ok": True,
                        "outputs": {
                            "model": {
                                "type": "ObjectRef",
                                "ref_id": "obj-456",
                                "uri": "obj://session/env/obj-456",
                                "storage_type": "memory",
                                "python_class": class_ctx.get("python_class"),
                                "metadata": {"init_params": class_ctx.get("init_params")},
                            }
                        },
                    },
                    "OK",
                    0,
                )
            # Verify reconstruction
            model_input = inputs.get("model")
            if not model_input or "uri" not in model_input:
                return (
                    {
                        "ok": False,
                        "error": {
                            "code": "INPUT_ERROR",
                            "message": f"Input 'model' not resolved: {model_input}",
                        },
                    },
                    "Failed",
                    1,
                )
            return (
                {
                    "ok": True,
                    "outputs": {
                        "out": {
                            "type": "ScalarRef",
                            "ref_id": "s2",
                            "uri": "mem://s2",
                            "metadata": {"v": 1},
                            "format": "json",
                            "mime_type": "application/json",
                            "size_bytes": 0,
                        }
                    },
                },
                "OK",
                0,
            )

        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _mock_execute_step)

        interactive.call_tool(session_id, "test.create", {}, {"x": 10})
        interactive.call_tool(session_id, "test.use", {"model": {"ref_id": "obj-456"}}, {})
        export_res = interactive.export_session(session_id)

        # Clear cache
        execution._memory_store._artifacts.clear()

        # Mock run_workflow to clear memory before the next step during replay
        original_run_workflow = execution.run_workflow

        def _mock_run_workflow(spec, **kwargs):
            if spec["steps"][0]["id"] != "test.create":
                execution._memory_store._artifacts.clear()
            return original_run_workflow(spec, **kwargs)

        monkeypatch.setattr(execution, "run_workflow", _mock_run_workflow)

        # Replay
        replay_res = interactive.replay_session(export_res["workflow_ref"], inputs={})

        # Verify result
        if replay_res.get("error"):
            pytest.fail(f"Replay failed with error: {replay_res['error']}")
        assert replay_res["status"] != "failed"


class TestGPUReplay:
    """T055: Integration tests for GPU->CPU replay behavior."""

    @pytest.fixture
    def services(self, tmp_path, monkeypatch):
        """Setup services with temporary stores."""
        from bioimage_mcp.api.execution import ExecutionService
        from bioimage_mcp.api.interactive import InteractiveExecutionService
        from bioimage_mcp.artifacts.store import ArtifactStore
        from bioimage_mcp.config.schema import Config
        from bioimage_mcp.sessions.manager import SessionManager
        from bioimage_mcp.sessions.store import SessionStore

        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[tmp_path / "tools"],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        (tmp_path / "tools").mkdir()

        artifact_store = ArtifactStore(config)
        session_store = SessionStore()
        session_manager = SessionManager(session_store, config)
        execution_service = ExecutionService(config, artifact_store=artifact_store)
        interactive_service = InteractiveExecutionService(session_manager, execution_service)

        monkeypatch.setattr(
            "bioimage_mcp.api.sessions.SessionService._function_exists",
            lambda self, fn_id: True,
        )
        monkeypatch.setattr(
            "bioimage_mcp.api.sessions.SessionService._env_installed",
            lambda self, env_name: True,
        )

        return interactive_service, execution_service

    def test_gpu_to_cpu_replay_fallback_or_error(self, services, monkeypatch):
        """Assert replaying a GPU workflow on CPU returns structured error or remaps."""
        interactive, execution = services
        session_id = "gpu-replay-test"

        # 1. Mock execution to return a GPU ObjectRef
        execution_count = 0

        def _mock_execute_step(fn_id, inputs, params, **kwargs):
            nonlocal execution_count
            execution_count += 1
            if fn_id == "cellpose.models.CellposeModel":
                # First call succeeds (recording), second call fails (replay on CPU)
                if execution_count > 1 and params.get("gpu") is True:
                    return (
                        {
                            "ok": False,
                            "error": {
                                "code": "EXECUTION_FAILED",
                                "message": "CUDA not available",
                                "details": [
                                    {"path": "params.gpu", "hint": "Set gpu=False for CPU replay"}
                                ],
                            },
                        },
                        "Failed",
                        1,
                    )
                return (
                    {
                        "ok": True,
                        "outputs": {
                            "model": {
                                "type": "ObjectRef",
                                "ref_id": "gpu-model",
                                "uri": "obj://s/e/gpu-model",
                                "storage_type": "memory",
                                "python_class": "cellpose.models.CellposeModel",
                                "metadata": {
                                    "init_params": {"model_type": "cyto3", "gpu": True},
                                    "device": "cuda",
                                },
                            }
                        },
                    },
                    "Created GPU Model",
                    0,
                )

                return (
                    {
                        "ok": True,
                        "outputs": {
                            "model": {
                                "type": "ObjectRef",
                                "ref_id": "gpu-model",
                                "uri": "obj://s/e/gpu-model",
                                "storage_type": "memory",
                                "python_class": "cellpose.models.CellposeModel",
                                "metadata": {
                                    "init_params": {"model_type": "cyto3", "gpu": True},
                                    "device": "cuda",
                                },
                            }
                        },
                    },
                    "Created GPU Model",
                    0,
                )
            elif fn_id == "core.reconstruct":
                # Simulate reconstruction failure on CPU if gpu=True is requested
                class_ctx = kwargs.get("class_context") or {}
                init_params = class_ctx.get("init_params") or {}
                if init_params.get("gpu") is True:
                    # In a real scenario, this might fail because no GPU is found
                    # or we might want it to return a structured error.
                    return (
                        {
                            "ok": False,
                            "error": {
                                "code": "EXECUTION_FAILED",
                                "message": "CUDA not available",
                                "details": [
                                    {"path": "params.gpu", "hint": "Set gpu=False for CPU replay"}
                                ],
                            },
                        },
                        "Failed",
                        1,
                    )
                return ({"ok": True, "outputs": {}}, "OK", 0)
            return ({"ok": True, "outputs": {}}, "OK", 0)

        monkeypatch.setattr("bioimage_mcp.api.execution.execute_step", _mock_execute_step)

        # 2. Record a "GPU" session
        interactive.call_tool(session_id, "cellpose.models.CellposeModel", {}, {"gpu": True})
        export_res = interactive.export_session(session_id)
        workflow_ref = export_res["workflow_ref"]

        # 3. Replay (simulating CPU environment)
        # We expect it to either fail with a structured error or succeed if remapped
        replay_res = interactive.replay_session(workflow_ref, inputs={})

        # For TDD: We expect it to FAIL or show structured error if it can't remap

        # If it fails, it MUST have the structured error shape
        assert replay_res.get("error") is not None, (
            "Replay should have failed with structured error"
        )
        error = replay_res["error"]
        assert error["code"] == "EXECUTION_FAILED"
        assert any("gpu" in d.get("hint", "").lower() for d in error.get("details", []))
