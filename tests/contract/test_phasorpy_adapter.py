"""
Contract tests for PhasorPyAdapter.

Verifies that PhasorPyAdapter correctly implements the BaseAdapter protocol
for discovering and executing phasorpy functions.
"""

from unittest.mock import MagicMock, patch

import numpy as np

from bioimage_mcp.artifacts.models import ArtifactRef
from bioimage_mcp.registry.dynamic.adapters import BaseAdapter
from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_phasorpy_adapter_implements_base_adapter():
    """PhasorPyAdapter must implement BaseAdapter protocol."""
    adapter = PhasorPyAdapter()
    assert isinstance(adapter, BaseAdapter)


def test_phasorpy_adapter_discovers_phasor_functions():
    """Adapter should discover phasor_from_signal and phasor_transform."""
    adapter = PhasorPyAdapter()

    # Mock module config for phasorpy.phasor
    module_config = {
        "module_name": "phasorpy.phasor",
        "include": ["phasor_from_signal", "phasor_transform"],
    }

    discovered = adapter.discover(module_config)

    # Should discover both functions
    assert len(discovered) == 2
    fn_names = [fn.name for fn in discovered]
    assert "phasor_from_signal" in fn_names
    assert "phasor_transform" in fn_names

    # Verify metadata structure
    for fn_meta in discovered:
        assert fn_meta.module == "phasorpy.phasor"
        assert fn_meta.source_adapter == "phasorpy"
        assert fn_meta.qualified_name.startswith("phasorpy.phasor.")
        assert fn_meta.fn_id.startswith("phasorpy.")


def test_phasorpy_adapter_resolves_signal_to_phasor_pattern():
    """resolve_io_pattern should return SIGNAL_TO_PHASOR for phasor_from_signal."""
    adapter = PhasorPyAdapter()

    # Mock signature (simplified - just need func_name really)
    mock_signature = MagicMock()

    io_pattern = adapter.resolve_io_pattern("phasor_from_signal", mock_signature)

    assert io_pattern == IOPattern.SIGNAL_TO_PHASOR


def test_phasorpy_adapter_resolves_phasor_transform_pattern():
    """resolve_io_pattern should return PHASOR_TRANSFORM for phasor_transform."""
    adapter = PhasorPyAdapter()

    mock_signature = MagicMock()

    io_pattern = adapter.resolve_io_pattern("phasor_transform", mock_signature)

    assert io_pattern == IOPattern.PHASOR_TRANSFORM


@patch("bioio.writers.OmeTiffWriter")
@patch("bioio.BioImage")
@patch("phasorpy.phasor.phasor_from_signal")
def test_phasorpy_adapter_executes_phasor_from_signal(mock_phasor_fn, mock_bioimage, mock_writer):
    """execute() should call phasorpy.phasor.phasor_from_signal with correct args."""
    adapter = PhasorPyAdapter()

    # Mock BioImage to return fake data
    mock_img = MagicMock()
    mock_img.data = np.random.rand(1, 1, 1, 10, 10)  # 5D TCZYX
    mock_bioimage.return_value = mock_img

    # Mock the phasorpy function to return fake phasor data
    mock_mean = np.random.rand(10, 10)
    mock_real = np.random.rand(10, 10)
    mock_imag = np.random.rand(10, 10)
    mock_phasor_fn.return_value = (mock_mean, mock_real, mock_imag)

    # Create input artifact
    input_artifact = ArtifactRef(
        ref_id="test-signal-1",
        type="BioImageRef",
        uri="file:///tmp/test_signal.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )

    # Execute
    params = {
        "frequency": 80.0,
        "harmonic": 1,
    }

    outputs = adapter.execute(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs=[input_artifact],
        params=params,
    )

    # Verify phasorpy function was called
    assert mock_phasor_fn.called

    # Verify outputs are artifact references
    assert len(outputs) >= 1
    # Check for dict or ArtifactRef since adapter currently returns dicts
    output = outputs[0]
    if isinstance(output, dict):
        assert output["type"] == "BioImageRef"
    else:
        assert isinstance(output, ArtifactRef)
        assert output.type == "BioImageRef"


def test_phasorpy_adapter_discover_returns_function_metadata_fields():
    """Discovered functions should have all required FunctionMetadata fields."""
    adapter = PhasorPyAdapter()

    module_config = {
        "module_name": "phasorpy.phasor",
        "include": ["phasor_from_signal"],
    }

    discovered = adapter.discover(module_config)
    fn_meta = discovered[0]

    # Verify FunctionMetadata fields
    assert hasattr(fn_meta, "name")
    assert hasattr(fn_meta, "module")
    assert hasattr(fn_meta, "qualified_name")
    assert hasattr(fn_meta, "fn_id")
    assert hasattr(fn_meta, "source_adapter")
    assert hasattr(fn_meta, "description")
    assert hasattr(fn_meta, "parameters")
    assert hasattr(fn_meta, "io_pattern")
    assert hasattr(fn_meta, "tags")


@patch("bioio.writers.OmeTiffWriter")
@patch("bioio.BioImage")
@patch("phasorpy.phasor.phasor_from_signal")
def test_execute_phasor_from_signal_returns_three_artifacts(
    mock_phasor_fn, mock_bioimage, mock_writer
):
    """execute() should return 3 artifacts for SIGNAL_TO_PHASOR pattern.

    phasor_from_signal returns (mean, real, imag) arrays, so execute()
    must create 3 separate ArtifactRef objects for the SIGNAL_TO_PHASOR pattern.
    """
    adapter = PhasorPyAdapter()

    # Mock BioImage to return fake data
    mock_img = MagicMock()
    mock_img.data = np.random.rand(1, 1, 1, 10, 10)  # 5D TCZYX
    mock_bioimage.return_value = mock_img

    # Mock phasor_from_signal to return 3 arrays (mean, real, imag)
    mock_mean = np.random.rand(10, 10)
    mock_real = np.random.rand(10, 10)
    mock_imag = np.random.rand(10, 10)
    mock_phasor_fn.return_value = (mock_mean, mock_real, mock_imag)

    # Create input artifact
    input_artifact = ArtifactRef(
        ref_id="test-signal-1",
        type="BioImageRef",
        uri="file:///tmp/test_signal.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )

    # Execute
    params = {
        "frequency": 80.0,
        "harmonic": 1,
    }

    outputs = adapter.execute(
        fn_id="phasorpy.phasor.phasor_from_signal",
        inputs=[input_artifact],
        params=params,
    )

    # Verify phasorpy function was called
    assert mock_phasor_fn.called

    # SIGNAL_TO_PHASOR pattern requires 3 output artifacts
    assert len(outputs) == 3, f"Expected 3 artifacts for SIGNAL_TO_PHASOR, got {len(outputs)}"

    # All outputs should be ArtifactRef or dict
    for output in outputs:
        if isinstance(output, dict):
            assert output["type"] == "BioImageRef"
        else:
            assert isinstance(output, ArtifactRef)
            assert output.type == "BioImageRef"

    # Verify artifact names/identifiers distinguish the outputs
    if isinstance(outputs[0], dict):
        # For dicts, check path or some other unique field
        paths = [out["path"] for out in outputs]
        assert len(set(paths)) == 3
    else:
        ref_ids = [out.ref_id for out in outputs]
        assert len(set(ref_ids)) == 3, "Each output artifact should have unique ref_id"


@patch("bioio.writers.OmeTiffWriter")
@patch("bioio.BioImage")
@patch("phasorpy.phasor.phasor_transform")
def test_execute_phasor_transform_returns_two_artifacts(
    mock_phasor_transform, mock_bioimage, mock_writer
):
    """execute() should return 2 artifacts for PHASOR_TRANSFORM pattern.

    phasor_transform takes (real, imag) and returns (real', imag') arrays,
    so execute() must create 2 separate ArtifactRef objects for the
    PHASOR_TRANSFORM pattern.
    """
    adapter = PhasorPyAdapter()

    # Mock BioImage to return fake data
    mock_img = MagicMock()
    mock_img.data = np.random.rand(1, 1, 1, 10, 10)  # 5D TCZYX
    mock_bioimage.return_value = mock_img

    # Mock phasor_transform to return 2 arrays (real, imag)
    mock_real_out = np.random.rand(10, 10)
    mock_imag_out = np.random.rand(10, 10)
    mock_phasor_transform.return_value = (mock_real_out, mock_imag_out)

    # Create 2 input artifacts for PHASOR_TRANSFORM pattern (G, S)
    input_g = ArtifactRef(
        ref_id="test-phasor-g",
        type="BioImageRef",
        uri="file:///tmp/test_phasor_g.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )
    input_s = ArtifactRef(
        ref_id="test-phasor-s",
        type="BioImageRef",
        uri="file:///tmp/test_phasor_s.tif",
        format="OME-TIFF",
        mime_type="image/tiff",
        size_bytes=1024,
        created_at=ArtifactRef.now(),
    )

    # Execute
    params = {
        "angle": 45.0,
    }

    outputs = adapter.execute(
        fn_id="phasorpy.phasor.phasor_transform",
        inputs=[input_g, input_s],
        params=params,
    )

    # Verify phasorpy function was called
    assert mock_phasor_transform.called

    # PHASOR_TRANSFORM pattern requires 2 output artifacts (real', imag')
    assert len(outputs) == 2, f"Expected 2 artifacts for PHASOR_TRANSFORM, got {len(outputs)}"

    # All outputs should be ArtifactRef or dict
    for output in outputs:
        if isinstance(output, dict):
            assert output["type"] == "BioImageRef"
        else:
            assert isinstance(output, ArtifactRef)
            assert output.type == "BioImageRef"

    # Verify artifact identifiers distinguish the outputs
    if isinstance(outputs[0], dict):
        paths = [out["path"] for out in outputs]
        assert len(set(paths)) == 2
    else:
        ref_ids = [out.ref_id for out in outputs]
        assert len(set(ref_ids)) == 2, "Each output artifact should have unique ref_id"


def test_save_image_metadata_includes_ndim(tmp_path):
    """T011: _save_image must include ndim in metadata matching shape length."""
    from bioimage_mcp.registry.dynamic.adapters.phasorpy import PhasorPyAdapter
    import numpy as np

    adapter = PhasorPyAdapter()

    # Create a 2D array that will be expanded to 5D
    arr = np.random.rand(64, 64).astype(np.float32)

    result = adapter._save_image(arr, work_dir=tmp_path, name="test_ndim")

    metadata = result["metadata"]
    assert "ndim" in metadata, "metadata must include 'ndim'"
    assert metadata["ndim"] == len(metadata["shape"]), (
        f"ndim ({metadata['ndim']}) must match shape length ({len(metadata['shape'])})"
    )
    # After expansion, should be 5D
    assert metadata["ndim"] == 5
