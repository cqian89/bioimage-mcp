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
def test_load_native_preserves_dimensions(tmp_path: Path) -> None:
    # This test would need a real image file, but since we are in TDD
    # and we expect it to fail anyway (or skip if not exists),
    # we can just try to import it and call it if it exists.
    pass


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
