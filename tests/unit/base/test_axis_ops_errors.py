import sys
from pathlib import Path

import numpy as np
import pytest

# Setup path to import bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import axis_ops


def test_relabel_axes_missing_uri_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        axis_ops.relabel_axes(
            inputs={"image": {}}, params={"axis_mapping": {"Z": "T"}}, work_dir=tmp_path
        )
    assert str(excinfo.value) == "Error in base.relabel_axes: Input 'image' must include uri"


def test_squeeze_missing_uri_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        axis_ops.squeeze(inputs={"image": {}}, params={"axis": 0}, work_dir=tmp_path)
    assert str(excinfo.value) == "Error in base.squeeze: Input 'image' must include uri"


def test_squeeze_no_singleton_axes_error(monkeypatch, tmp_path: Path) -> None:
    # Create data with no singleton dimensions (shape 2, 3, 4)
    data = np.zeros((2, 3, 4))
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)

    with pytest.raises(ValueError) as excinfo:
        axis_ops.squeeze(
            inputs={"image": {"uri": "file:///tmp/test.tif", "metadata": {"axes": "ZYX"}}},
            params={"axis": None},  # Auto-detect singleton axes
            work_dir=tmp_path,
        )
    assert str(excinfo.value) == "Error in base.squeeze: No singleton axes to squeeze"


def test_expand_dims_missing_uri_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        axis_ops.expand_dims(
            inputs={"image": {}}, params={"axis": 0, "new_axis_name": "T"}, work_dir=tmp_path
        )
    assert str(excinfo.value) == "Error in base.expand_dims: Input 'image' must include uri"


def test_moveaxis_missing_uri_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        axis_ops.moveaxis(
            inputs={"image": {}}, params={"source": 0, "destination": 1}, work_dir=tmp_path
        )
    assert str(excinfo.value) == "Error in base.moveaxis: Input 'image' must include uri"


def test_swap_axes_missing_uri_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        axis_ops.swap_axes(inputs={"image": {}}, params={"axis1": 0, "axis2": 1}, work_dir=tmp_path)
    assert str(excinfo.value) == "Error in base.swap_axes: Input 'image' must include uri"
