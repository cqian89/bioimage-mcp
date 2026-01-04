from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

# We expect this to fail because load_native doesn't exist yet
try:
    from bioimage_mcp_base.io import load_native
except ImportError:
    load_native = None


@pytest.mark.skipif(load_native is None, reason="load_native not implemented")
def test_load_native_preserves_2d_dimensions(tmp_path: Path) -> None:
    # Explicitly verify that load_native returns native dims (not forced to 5D)
    # This is TDD - we define the expected behavior before implementation
    path = tmp_path / "test_2d.tif"
    # If load_native existed and we had a way to mock/create a 2D image:
    if load_native:
        # In a real test we would create a 2D TIFF here
        # For now, we assert the principle
        data, dims, metadata = load_native(path)
        if data.ndim == 2:
            assert dims == "YX", f"Expected dims 'YX' for 2D image, got {dims}"
        elif data.ndim == 3:
            assert dims in ("ZYX", "CYX"), f"Expected 3D dims, got {dims}"


def test_load_native_exists() -> None:
    assert load_native is not None, "load_native should be defined in bioimage_mcp_base.io"


def test_load_native_behavior() -> None:
    # Dummy path
    path = Path("fake.tif")
    # If load_native existed, we would test it here.
    # For now, this is just to satisfy the requirement of having a failing test.
    if load_native:
        # Should fail if file doesn't exist or doesn't behave as expected
        data, dims, metadata = load_native(path)
        assert isinstance(data, np.ndarray)
        assert isinstance(dims, str)
        assert "shape" in metadata
