from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pytest

# Add tools/base to sys.path
tools_base = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(tools_base) not in sys.path:
    sys.path.insert(0, str(tools_base))

try:
    from bioimage_mcp_base.native_io import load_native
except ImportError:
    load_native = None


@pytest.mark.skipif(load_native is None, reason="load_native not implemented")
def test_load_native_preserves_2d_dimensions(tmp_path: Path) -> None:
    # Explicitly verify that load_native returns native dims (not forced to 5D)
    import tifffile

    path = tmp_path / "test_2d.tif"
    data_in = np.zeros((100, 100), dtype=np.uint8)
    tifffile.imwrite(path, data_in)

    if load_native:
        data, dims, metadata = load_native(path)
        assert data.shape == (100, 100)
        assert dims == "YX", f"Expected dims 'YX' for 2D image, got {dims}"


def test_load_native_exists() -> None:
    assert load_native is not None, "load_native should be defined in bioimage_mcp_base.native_io"


def test_load_native_error_on_missing_file() -> None:
    # Test that load_native raises FileNotFoundError for missing files
    path = Path("non_existent_file.tif")
    if load_native:
        with pytest.raises(FileNotFoundError):
            load_native(path)
