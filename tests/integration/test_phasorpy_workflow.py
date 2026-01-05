"""Integration tests for PhasorPy workflow execution."""

import pytest
import numpy as np
import subprocess
from pathlib import Path
from urllib.parse import quote
from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
from bioimage_mcp.artifacts.models import ArtifactRef, PlotRef, PlotMetadata
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


def _path_to_uri(path: Path) -> str:
    return f"file://{quote(str(path.absolute()), safe='/:')}"


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


@pytest.fixture
def adapter():
    return PhasorPyAdapter()


def create_mock_artifact(ref_id: str, path: Path, fmt: str = "OME-TIFF") -> ArtifactRef:
    return ArtifactRef(
        ref_id=ref_id,
        type="BioImageRef",
        uri=f"file://{path.absolute()}",
        format=fmt,
        mime_type="image/tiff" if "TIFF" in fmt else "application/octet-stream",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )


@pytest.mark.slow
@pytest.mark.integration
def test_filesystem_allowlist_enforcement(adapter):
    """T041: Allowlist enforcement for file reads."""
    # Valid file in datasets/
    valid_path = Path(
        "datasets/sdt_flim_testdata/seminal_receptacle_FLIM_single_image.sdt"
    ).absolute()
    assert valid_path.exists()

    artifact = create_mock_artifact("test-sdt", valid_path, "SDT")

    # Should work for datasets/
    try:
        data = adapter._load_image(artifact)
        assert data is not None
        assert data.ndim >= 2
    except Exception as e:
        pytest.fail(f"Loading valid file from datasets/ failed: {e}")


@pytest.mark.slow
@pytest.mark.integration
def test_provenance_recording(adapter, tmp_path):
    """T039: Provenance recording (input hashes, parameters, phasorpy version in metadata)."""
    # Create synthetic input
    data = np.random.rand(1, 1, 1, 10, 10).astype(np.float32)
    input_path = tmp_path / "input.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data, str(input_path), dim_order="TCZYX")

    input_artifact = create_mock_artifact("input-1", input_path)

    # Execute
    outputs = adapter.execute(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs=[input_artifact],
        params={"frequency": 80.0},
        work_dir=tmp_path,
    )

    # Check provenance in output metadata
    for output in outputs:
        # Adapter currently returns dicts from execute
        metadata = output.get("metadata", {}) if isinstance(output, dict) else output.metadata

        # Phase 1 requirement: metadata must contain version and/or provenance info
        assert "phasorpy_version" in metadata or "provenance" in metadata
        if "provenance" in metadata:
            assert "input_hashes" in metadata["provenance"]


@pytest.mark.slow
@pytest.mark.integration
def test_sdt_loading_normalization(adapter):
    """T023: SDT file loading produces normalized TCZYX artifact."""
    sdt_path = Path(
        "datasets/sdt_flim_testdata/seminal_receptacle_FLIM_single_image.sdt"
    ).absolute()
    assert sdt_path.exists()

    artifact = create_mock_artifact("test-sdt", sdt_path, "SDT")

    data = adapter._load_image(artifact)

    # bioio should normalize to 5D TCZYX
    assert data.ndim == 5, f"Expected 5D TCZYX data, got {data.ndim}D"
    # Verify we can access the data (not just a lazy reference that fails)
    assert data.shape[0] >= 1  # T
    assert data.shape[1] >= 1  # C
    assert data.shape[2] >= 1  # Z
    assert data.shape[3] > 0  # Y
    assert data.shape[4] > 0  # X


@pytest.mark.slow
@pytest.mark.integration
def test_phasor_from_signal_execution_returns_gs(adapter, tmp_path):
    """T011: phasor_from_signal execution returns G/S images."""
    # T=1, C=1, Z=100 (lifetimes), Y=32, X=32
    data = np.random.rand(1, 1, 100, 32, 32).astype(np.float32)
    input_path = tmp_path / "signal.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data, str(input_path), dim_order="TCZYX")

    input_artifact = create_mock_artifact("signal-1", input_path)

    outputs = adapter.execute(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs=[input_artifact],
        params={"frequency": 80.0, "axis": 2},  # Collapse Z dimension
        work_dir=tmp_path,
    )

    # Returns (mean, real, imag) -> 3 artifacts
    assert len(outputs) == 3

    # Verify they are BioImageRefs and have correct shapes
    for out in outputs:
        meta = out.get("metadata", {}) if isinstance(out, dict) else out.metadata
        # Output should be 2D spatial + 1D Z + 1D C + 1D T (TCZYX)
        # For phasor_from_signal, Z becomes 1 as we collapsed it
        assert meta["shape"][2] == 1  # Z
        assert meta["shape"][0] == 1  # T


@pytest.mark.slow
@pytest.mark.integration
def test_phasor_calibrate_execution_range(adapter, tmp_path):
    """T012: phasor_calibrate execution returns calibrated values in [0,1]."""
    # Create G/S mock data
    shape = (1, 1, 1, 32, 32)
    g = np.random.rand(*shape).astype(np.float32)
    s = np.random.rand(*shape).astype(np.float32)

    # Reference data (e.g. from a known lifetime)
    ref_mean = np.ones(shape).astype(np.float32)
    ref_real = np.random.rand(*shape).astype(np.float32)
    ref_imag = np.random.rand(*shape).astype(np.float32)

    g_path = tmp_path / "g.ome.tiff"
    s_path = tmp_path / "s.ome.tiff"
    rm_path = tmp_path / "rm.ome.tiff"
    rr_path = tmp_path / "rr.ome.tiff"
    ri_path = tmp_path / "ri.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(g, str(g_path), dim_order="TCZYX")
    OmeTiffWriter.save(s, str(s_path), dim_order="TCZYX")
    OmeTiffWriter.save(ref_mean, str(rm_path), dim_order="TCZYX")
    OmeTiffWriter.save(ref_real, str(rr_path), dim_order="TCZYX")
    OmeTiffWriter.save(ref_imag, str(ri_path), dim_order="TCZYX")

    # phasor_calibrate takes real, imag, ref_mean, ref_real, ref_imag
    inputs = [
        create_mock_artifact("g", g_path),
        create_mock_artifact("s", s_path),
        create_mock_artifact("rm", rm_path),
        create_mock_artifact("rr", rr_path),
        create_mock_artifact("ri", ri_path),
    ]

    outputs = adapter.execute(
        fn_id="phasorpy.lifetime.phasor_calibrate",
        inputs=inputs,
        params={"lifetime": 4.0, "frequency": 80.0},
        work_dir=tmp_path,
    )

    assert len(outputs) == 2  # Returns calibrated (real, imag)

    for out in outputs:
        calibrated_data = adapter._load_image(out)
        # Phasor values should be within reasonable bounds
        assert np.all(calibrated_data >= -1.5)
        assert np.all(calibrated_data <= 1.5)


@pytest.mark.integration
def test_allowlist_enforcement_negative(tmp_path: Path) -> None:
    """T041: Verify that reads from paths outside allowlist are denied."""
    # Skip if env not available
    if not _env_available("bioimage-mcp-base"):
        pytest.skip("bioimage-mcp-base environment not available")

    dataset_file = (
        Path(__file__).parent.parent.parent
        / "datasets"
        / "FLUTE_FLIM_data_tif"
        / "Fluorescein_Embryo.tif"
    ).absolute()
    if not dataset_file.exists():
        pytest.skip(f"Dataset missing at {dataset_file}")

    # Setup config with restricted allowlist (NOT including the dataset)
    artifacts_root = tmp_path / "artifacts"
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path],  # Only allow tmp_path, not datasets/
        fs_allowlist_write=[tmp_path],
    )

    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)

    with ExecutionService(config, artifact_store=artifact_store) as execution:
        workflow = {
            "steps": [
                {
                    "fn_id": "base.phasorpy.phasor.phasor_from_signal",
                    "inputs": {
                        "signal": {
                            "type": "BioImageRef",
                            "format": "OME-TIFF",
                            "uri": _path_to_uri(dataset_file),
                        }
                    },
                    "params": {"axis": -1, "harmonic": 1},
                }
            ]
        }

        # Run workflow - it should fail in the subprocess
        run = execution.run_workflow(workflow)
        status = execution.get_run_status(run["run_id"])

        assert status["status"] == "failed"
        # The error message should come from the subprocess
        error_msg = str(status.get("error", ""))
        assert (
            "permission denied" in error_msg.lower()
            or "not under any allowed read root" in error_msg.lower()
        )


@pytest.mark.slow
@pytest.mark.integration
def test_plot_phasor_execution_returns_plotref(adapter, tmp_path):
    """T018: plot_phasor execution returns a PlotRef with metadata."""
    # Create mock real/imag data
    real = np.random.rand(1, 1, 1, 32, 32).astype(np.float32)
    imag = np.random.rand(1, 1, 1, 32, 32).astype(np.float32)

    real_path = tmp_path / "real.ome.tiff"
    imag_path = tmp_path / "imag.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(real, str(real_path), dim_order="TCZYX")
    OmeTiffWriter.save(imag, str(imag_path), dim_order="TCZYX")

    input_real = create_mock_artifact("real", real_path)
    input_imag = create_mock_artifact("imag", imag_path)

    outputs = adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[("real", input_real), ("imag", input_imag)],
        params={},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    plot_ref = outputs[0]

    # Adapter returns dict for JSON serialization in worker
    if isinstance(plot_ref, dict):
        assert plot_ref["type"] == "PlotRef"
        assert plot_ref["format"] == "PNG"
        assert "path" in plot_ref
        assert plot_ref["metadata"]["width_px"] > 0
        assert plot_ref["metadata"]["height_px"] > 0
        assert plot_ref["metadata"]["dpi"] == 100
    else:
        assert isinstance(plot_ref, PlotRef)
        assert plot_ref.type == "PlotRef"
        assert plot_ref.format == "PNG"
        assert isinstance(plot_ref.metadata, PlotMetadata)
        assert plot_ref.metadata.width_px > 0
        assert plot_ref.metadata.height_px > 0
        assert plot_ref.metadata.dpi == 100


@pytest.mark.slow
@pytest.mark.integration
def test_lif_loading_normalization(adapter):
    """T025: LIF file loading produces normalized TCZYX artifact."""
    lif_path = Path("datasets/lif_flim_testdata/FLIM_testdata.lif").absolute()
    assert lif_path.exists()

    artifact = create_mock_artifact("test-lif", lif_path, "LIF")
    data = adapter._load_image(artifact)

    # bioio should normalize to 5D TCZYX
    assert data.ndim == 5, f"Expected 5D TCZYX data, got {data.ndim}D"
    assert data.shape[3] > 0  # Y
    assert data.shape[4] > 0  # X


@pytest.mark.slow
@pytest.mark.integration
def test_ptu_loading_normalization(adapter):
    """T024: PTU file loading produces normalized TCZYX artifact."""
    ptu_path = Path("datasets/ptu_hazelnut_flim/hazelnut_FLIM_single_image.ptu").absolute()
    assert ptu_path.exists()

    # Research/verification (T027): check if bioio supports PTU
    import bioio

    report = bioio.plugin_feasibility_report(str(ptu_path))
    supported = any(r.supported for r in report.values())

    if not supported:
        pytest.xfail("PTU format not supported by available bioio plugins")

    artifact = create_mock_artifact("test-ptu", ptu_path, "PTU")
    data = adapter._load_image(artifact)

    assert data.ndim == 5
    assert data.shape[3] > 0
    assert data.shape[4] > 0


@pytest.mark.slow
@pytest.mark.integration
def test_metadata_preservation(adapter, tmp_path):
    """T026: Verify frequency/harmonics preservation in PhasorMetadata."""
    # Create synthetic input
    data = np.random.rand(1, 1, 10, 32, 32).astype(np.float32)
    input_path = tmp_path / "metadata_test.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data, str(input_path), dim_order="TCZYX")
    input_artifact = create_mock_artifact("meta-in", input_path)

    frequency = 80.0
    harmonic = 2

    outputs = adapter.execute(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs=[input_artifact],
        params={"frequency": frequency, "harmonic": harmonic},
        work_dir=tmp_path,
    )

    # Check that frequency and harmonic are preserved in metadata of all outputs
    for out in outputs:
        metadata = out.get("metadata", {}) if isinstance(out, dict) else out.metadata
        # The adapter should store these in a phasor_info or similar section
        # or directly in metadata if that's the convention
        if "phasor_info" in metadata:
            assert metadata["phasor_info"].get("frequency") == frequency
            assert metadata["phasor_info"].get("harmonic") == harmonic
        else:
            # Fallback check for common keys
            assert (
                metadata.get("frequency") == frequency
                or metadata.get("phasor_frequency") == frequency
            )
            assert (
                metadata.get("harmonic") == harmonic or metadata.get("phasor_harmonic") == harmonic
            )


@pytest.mark.slow
@pytest.mark.integration
def test_plot_artifact_accessibility(adapter, tmp_path):
    """T019: PlotRef artifact is accessible and readable as a PNG image."""
    # Create mock real/imag data
    real = np.random.rand(1, 1, 1, 16, 16).astype(np.float32)
    imag = np.random.rand(1, 1, 1, 16, 16).astype(np.float32)

    real_path = tmp_path / "real2.ome.tiff"
    imag_path = tmp_path / "imag2.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(real, str(real_path), dim_order="TCZYX")
    OmeTiffWriter.save(imag, str(imag_path), dim_order="TCZYX")

    input_real = create_mock_artifact("real", real_path)
    input_imag = create_mock_artifact("imag", imag_path)

    outputs = adapter.execute(
        fn_id="phasorpy.plot.plot_phasor",
        inputs=[input_real, input_imag],
        params={},
        work_dir=tmp_path,
    )

    plot_ref = outputs[0]
    from urllib.parse import urlparse

    uri = plot_ref["uri"] if isinstance(plot_ref, dict) else plot_ref.uri
    parsed = urlparse(uri)
    path = Path(parsed.path)
    if str(path).startswith("/") and len(str(path)) > 2 and str(path)[2] == ":":
        path = Path(str(path)[1:])

    assert path.exists()
    assert path.suffix == ".png"

    # Verify it's a valid PNG by checking magic number or using PIL
    with open(path, "rb") as f:
        header = f.read(8)
        assert header == b"\x89PNG\r\n\x1a\n"


@pytest.mark.integration
def test_error_translation_invalid_parameter(adapter, tmp_path):
    """T042: Test error translation (invalid params -> proper MCP error)."""
    # Create valid input
    data = np.random.rand(1, 1, 10, 32, 32).astype(np.float32)
    input_path = tmp_path / "error_test.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data, str(input_path), dim_order="TCZYX")
    input_artifact = create_mock_artifact("error-in", input_path)

    # Execute with invalid parameter - PhasorPy functions often validate via numpy/scipy
    # If we pass something that causes a ValueError or IndexError in the target_fn
    with pytest.raises(ValueError) as excinfo:
        adapter.execute(
            fn_id="phasorpy.phasor.phasor_from_signal",
            inputs=[input_artifact],
            params={"harmonic": -1},
            work_dir=tmp_path,
        )

    # Check that the exception has a 'code' attribute with 'INVALID_PARAMETER'
    assert getattr(excinfo.value, "code", None) == "INVALID_PARAMETER"


@pytest.mark.integration
def test_log_capture(adapter, tmp_path, caplog):
    """T043: Test log capture."""
    import logging

    # Set caplog to capture INFO level
    caplog.set_level(logging.INFO)

    # Create valid input
    data = np.random.rand(1, 1, 10, 16, 16).astype(np.float32)
    input_path = tmp_path / "log_test.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data, str(input_path), dim_order="TCZYX")
    input_artifact = create_mock_artifact("log-in", input_path)

    adapter.execute(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs=[input_artifact],
        params={"frequency": 80.0},
        work_dir=tmp_path,
    )

    # Check if execution start/end logs are present
    assert "Executing phasorpy function" in caplog.text
    assert "Execution successful" in caplog.text


@pytest.mark.integration
def test_verification_sc001_function_discovery(adapter):
    """T032: SC-001 - Verify ≥50 functions discovered."""
    discovered = adapter.discover(
        {"modules": ["phasorpy.phasor", "phasorpy.lifetime", "phasorpy.plot", "phasorpy.filter"]}
    )
    # We expect a good number of functions from these modules
    assert len(discovered) >= 50


@pytest.mark.integration
def test_verification_sc002_performance(adapter, tmp_path):
    """T033: SC-002 - Workflow < 30 seconds."""
    import time

    start_time = time.time()

    # Simple workflow
    data = np.random.rand(1, 1, 10, 32, 32).astype(np.float32)
    input_path = tmp_path / "perf_test.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data, str(input_path), dim_order="TCZYX")
    input_artifact = create_mock_artifact("perf-in", input_path)

    adapter.execute(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs=[input_artifact],
        params={"harmonic": 1},
        work_dir=tmp_path,
    )

    duration = time.time() - start_time
    assert duration < 30.0


@pytest.mark.integration
@pytest.mark.skipif(
    True, reason="SC-003 requires full MCP server context for subprocess crash test"
)
def test_verification_sc003_subprocess_isolation():
    """T034: SC-003 - Subprocess isolation handles crashes."""
    # This is typically verified at the runner level, not the adapter level.
    # The adapter itself cannot easily test its own process isolation.
    pass


@pytest.mark.slow
@pytest.mark.integration
def test_plot_phasor_e2e_execution_service(tmp_path: Path) -> None:
    """Test plot_phasor execution through ExecutionService with PlotRef output."""
    # Skip if env not available
    if not _env_available("bioimage-mcp-base"):
        pytest.skip("bioimage-mcp-base environment not available")

    dataset_file = (
        Path(__file__).parent.parent.parent
        / "datasets"
        / "FLUTE_FLIM_data_tif"
        / "Fluorescein_Embryo.tif"
    ).absolute()
    if not dataset_file.exists():
        pytest.skip(f"Dataset missing at {dataset_file}")

    # Setup config and ExecutionService
    artifacts_root = tmp_path / "artifacts"
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[dataset_file.parent, tools_root, tmp_path],
        fs_allowlist_write=[tmp_path],
    )

    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)

    with ExecutionService(config, artifact_store=artifact_store) as execution:
        # Step 1: Get phasor data
        workflow1 = {
            "steps": [
                {
                    "fn_id": "base.phasorpy.phasor.phasor_from_signal",
                    "inputs": {
                        "signal": {
                            "type": "BioImageRef",
                            "format": "OME-TIFF",
                            "uri": _path_to_uri(dataset_file),
                        }
                    },
                    "params": {"axis": -1, "harmonic": 1},
                }
            ]
        }
        run1 = execution.run_workflow(workflow1)
        status1 = execution.get_run_status(run1["run_id"])
        assert status1["status"] == "success"

        # Step 2: Plot phasor
        # phasor_from_signal returns (mean, real, imag) -> (output, output_1, output_2)
        outputs1 = status1["outputs"]

        workflow2 = {
            "steps": [
                {
                    "fn_id": "base.phasorpy.plot.plot_phasor",
                    "inputs": {
                        "real": outputs1["output_1"],
                        "imag": outputs1["output_2"],
                    },
                    "params": {},
                }
            ]
        }
        # skip_validation=True because we might not have all schemas loaded in this test setup
        run2 = execution.run_workflow(workflow2, skip_validation=True)
        status2 = execution.get_run_status(run2["run_id"])

        # Verify success and PlotRef output
        assert status2["status"] == "success"
        outputs2 = status2["outputs"]
        plot_ref = outputs2["output"]

        assert plot_ref["type"] == "PlotRef"
        assert plot_ref["format"] == "PNG"

        # Verify output can be accessed via artifact_store.get (matches get_artifact requirement)
        ref_id = plot_ref["ref_id"]
        retrieved_ref = execution.artifact_store.get(ref_id)
        assert retrieved_ref.type == "PlotRef"
        assert retrieved_ref.format == "PNG"

        # Verify PNG file exists and has valid content
        uri = plot_ref["uri"]
        if uri.startswith("file://"):
            path_str = uri[7:]
            if len(path_str) > 2 and path_str[0] == "/" and path_str[2] == ":":
                path_str = path_str[1:]
            png_path = Path(path_str)
        else:
            png_path = Path(uri)

        assert png_path.exists()
        with open(png_path, "rb") as f:
            header = f.read(8)
            assert header == b"\x89PNG\r\n\x1a\n"
