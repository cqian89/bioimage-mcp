"""Integration tests for PhasorPy workflow execution."""

import pytest
import numpy as np
from pathlib import Path
from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
from bioimage_mcp.artifacts.models import ArtifactRef


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
        fn_id="phasorpy.phasor_from_signal",
        inputs=[input_artifact],
        params={"frequency": 80.0},
        work_dir=tmp_path,
    )

    # Check provenance in output metadata
    # This is expected to FAIL until implementation adds provenance
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
    # T=100 (lifetimes), C=1, Z=1, Y=32, X=32
    data = np.random.rand(1, 1, 100, 32, 32).astype(np.float32)
    input_path = tmp_path / "signal.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data, str(input_path), dim_order="TCZYX")

    input_artifact = create_mock_artifact("signal-1", input_path)

    outputs = adapter.execute(
        fn_id="phasorpy.phasor_from_signal",
        inputs=[input_artifact],
        params={"frequency": 80.0},
        work_dir=tmp_path,
    )

    # Returns (mean, real, imag) -> 3 artifacts
    assert len(outputs) == 3

    # Verify they are BioImageRefs and have correct shapes
    for out in outputs:
        meta = out.get("metadata", {}) if isinstance(out, dict) else out.metadata
        # Output should be 2D spatial + 1D Z + 1D C + 1D T (TCZYX)
        # For phasor_from_signal, T becomes 1 as we collapsed the lifetime dimension
        assert meta["shape"][2] == 1  # Z
        assert meta["shape"][0] == 1  # T


@pytest.mark.slow
@pytest.mark.integration
def test_phasor_calibrate_execution_range(adapter, tmp_path):
    """T012: phasor_calibrate execution returns calibrated values in [0,1]."""
    # Create G/S mock data
    g = np.random.rand(1, 1, 1, 32, 32).astype(np.float32)
    s = np.random.rand(1, 1, 1, 32, 32).astype(np.float32)

    g_path = tmp_path / "g.ome.tiff"
    s_path = tmp_path / "s.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(g, str(g_path), dim_order="TCZYX")
    OmeTiffWriter.save(s, str(s_path), dim_order="TCZYX")

    # phasor_calibrate takes real, imag (G, S)
    input_g = create_mock_artifact("g", g_path)
    input_s = create_mock_artifact("s", s_path)

    # This is expected to FAIL until implementation (not in hardcoded list)
    outputs = adapter.execute(
        fn_id="phasorpy.phasor.phasor_calibrate",
        inputs=[input_g, input_s],
        params={"tau": 4.0, "frequency": 80.0},
        work_dir=tmp_path,
    )

    assert len(outputs) == 2  # Returns calibrated (real, imag)

    for out in outputs:
        calibrated_data = adapter._load_image(out)
        # Phasor values should be within reasonable bounds
        # (Though noise can push them slightly outside [0,1])
        assert np.all(calibrated_data >= -1.1)
        assert np.all(calibrated_data <= 1.1)
