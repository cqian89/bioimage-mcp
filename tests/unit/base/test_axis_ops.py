from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

from bioimage_mcp_base import axis_ops  # noqa: E402


def test_relabel_axes_params_valid() -> None:
    params = axis_ops.RelabelAxesParams.model_validate({"axis_mapping": {"Z": "T", "T": "Z"}})
    assert params.axis_mapping == {"Z": "T", "T": "Z"}


def test_relabel_axes_params_rejects_invalid_axis_name() -> None:
    with pytest.raises(ValidationError):
        axis_ops.RelabelAxesParams.model_validate({"axis_mapping": {"Z": "t"}})
    with pytest.raises(ValidationError):
        axis_ops.RelabelAxesParams.model_validate({"axis_mapping": {"Z": "TT"}})


def test_squeeze_params_optional_axis() -> None:
    params_none = axis_ops.SqueezeParams.model_validate({"axis": None})
    params_int = axis_ops.SqueezeParams.model_validate({"axis": 0})
    params_str = axis_ops.SqueezeParams.model_validate({"axis": "Z"})

    assert params_none.axis is None
    assert params_int.axis == 0
    assert params_str.axis == "Z"


def test_expand_dims_params_requires_axis_and_name() -> None:
    with pytest.raises(ValidationError):
        axis_ops.ExpandDimsParams.model_validate({"new_axis_name": "Z"})
    with pytest.raises(ValidationError):
        axis_ops.ExpandDimsParams.model_validate({"axis": 0})


def test_expand_dims_params_rejects_invalid_axis_name() -> None:
    with pytest.raises(ValidationError):
        axis_ops.ExpandDimsParams.model_validate({"axis": 0, "new_axis_name": "z"})
    with pytest.raises(ValidationError):
        axis_ops.ExpandDimsParams.model_validate({"axis": 0, "new_axis_name": "TT"})


def test_moveaxis_params_valid() -> None:
    params_int = axis_ops.MoveAxisParams.model_validate({"source": 0, "destination": 2})
    params_str = axis_ops.MoveAxisParams.model_validate({"source": "Z", "destination": -1})

    assert params_int.source == 0
    assert params_int.destination == 2
    assert params_str.source == "Z"
    assert params_str.destination == -1


def test_swap_axes_params_valid() -> None:
    params = axis_ops.SwapAxesParams.model_validate({"axis1": "Z", "axis2": 0})
    assert params.axis1 == "Z"
    assert params.axis2 == 0


def test_relabel_axes_rejects_nonexistent_axis(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)

    with pytest.raises(ValueError) as excinfo:
        axis_ops.relabel_axes(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
            params={"axis_mapping": {"W": "Z"}},
            work_dir=tmp_path,
        )

    assert (
        str(excinfo.value)
        == "Error in base.relabel_axes: Axis W not found in image with axes ZYX. Check axis names."
    )


def test_relabel_axes_rejects_duplicate_result(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)

    with pytest.raises(ValueError) as excinfo:
        axis_ops.relabel_axes(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
            params={"axis_mapping": {"Z": "Y"}},
            work_dir=tmp_path,
        )

    assert str(excinfo.value) == (
        "Error in base.relabel_axes: Mapping would create duplicate axis 'Y' in result 'YYX'. "
        "Use unique target names."
    )


def test_relabel_axes_swap_zt(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.relabel_axes(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZTYX"}}},
        params={"axis_mapping": {"Z": "T", "T": "Z"}},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], data)
    assert captured["axes"] == "TZYX"


def test_physical_pixel_sizes_preserved_on_relabel(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", lambda *_args, **_kwargs: tmp_path / "out.tif")

    result = axis_ops.relabel_axes(
        inputs={
            "image": {
                "uri": "file:///tmp/sample.tif",
                "metadata": {
                    "axes": "ZYX",
                    "physical_pixel_sizes": {"Z": 1.0, "Y": 0.1, "X": 0.1},
                },
            }
        },
        params={"axis_mapping": {"Z": "T"}},
        work_dir=tmp_path,
    )

    metadata = result["outputs"]["output"]["metadata"]
    assert metadata["axes"] == "TYX"
    assert metadata["physical_pixel_sizes"] == {"T": 1.0, "Y": 0.1, "X": 0.1}


def test_squeeze_singleton(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(1 * 3 * 4, dtype="uint8").reshape(1, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.squeeze(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"axis": 0},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    assert np.asarray(captured["array"]).shape == (3, 4)
    assert captured["axes"] == "YX"


def test_squeeze_rejects_non_singleton_axis(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)

    with pytest.raises(ValueError) as excinfo:
        axis_ops.squeeze(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
            params={"axis": 0},
            work_dir=tmp_path,
        )

    assert str(excinfo.value) == (
        "Error in base.squeeze: Cannot squeeze axis 0 (index 0) with size 2. "
        "Only singleton axes (size 1) can be squeezed."
    )


def test_physical_pixel_sizes_removed_on_squeeze(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(1 * 3 * 4, dtype="uint8").reshape(1, 3, 4)
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", lambda *_args, **_kwargs: tmp_path / "out.tif")

    result = axis_ops.squeeze(
        inputs={
            "image": {
                "uri": "file:///tmp/sample.tif",
                "metadata": {
                    "axes": "ZYX",
                    "physical_pixel_sizes": {"Z": 1.0, "Y": 0.1, "X": 0.1},
                },
            }
        },
        params={"axis": 0},
        work_dir=tmp_path,
    )

    metadata = result["outputs"]["output"]["metadata"]
    assert metadata["axes"] == "YX"
    assert metadata["physical_pixel_sizes"] == {"Y": 0.1, "X": 0.1}


def test_expand_dims_rejects_existing_axis(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(3 * 4, dtype="uint8").reshape(3, 4)
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)

    with pytest.raises(ValueError) as excinfo:
        axis_ops.expand_dims(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
            params={"axis": 0, "new_axis_name": "Z"},
            work_dir=tmp_path,
        )

    assert str(excinfo.value) == (
        "Error in base.expand_dims: Axis name 'Z' already exists in axes 'ZYX'. Use a unique name."
    )


def test_expand_dims_at_start(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(3 * 4, dtype="uint8").reshape(3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.expand_dims(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "YX"}}},
        params={"axis": 0, "new_axis_name": "Z"},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    assert np.asarray(captured["array"]).shape == (1, 3, 4)
    assert captured["axes"] == "ZYX"


def test_physical_pixel_sizes_added_on_expand(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(3 * 4, dtype="uint8").reshape(3, 4)
    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", lambda *_args, **_kwargs: tmp_path / "out.tif")

    result = axis_ops.expand_dims(
        inputs={
            "image": {
                "uri": "file:///tmp/sample.tif",
                "metadata": {
                    "axes": "YX",
                    "physical_pixel_sizes": {"Y": 0.1, "X": 0.1},
                },
            }
        },
        params={"axis": 0, "new_axis_name": "Z"},
        work_dir=tmp_path,
    )

    metadata = result["outputs"]["output"]["metadata"]
    assert metadata["axes"] == "ZYX"
    assert metadata["physical_pixel_sizes"] == {"Z": None, "Y": 0.1, "X": 0.1}


def test_moveaxis_forward(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.moveaxis(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"source": 0, "destination": 2},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], np.moveaxis(data, 0, 2))
    assert captured["axes"] == "YXZ"


def test_moveaxis_negative_index(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.moveaxis(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"source": 1, "destination": -1},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], np.moveaxis(data, 1, -1))
    assert captured["axes"] == "ZXY"


def test_moveaxis_by_name(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.moveaxis(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"source": "Z", "destination": 1},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], np.moveaxis(data, 0, 1))
    assert captured["axes"] == "YZX"


def test_swap_axes_basic(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.swap_axes(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"axis1": "Z", "axis2": "X"},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], np.swapaxes(data, 0, 2))
    assert captured["axes"] == "XYZ"


def test_swap_axes_by_index(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.swap_axes(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"axis1": 0, "axis2": 1},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], np.swapaxes(data, 0, 1))
    assert captured["axes"] == "YZX"


def test_swap_axes_mixed(monkeypatch, tmp_path: Path) -> None:
    data = np.arange(2 * 3 * 4 * 5, dtype="uint8").reshape(2, 3, 4, 5)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.swap_axes(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "TZYX"}}},
        params={"axis1": "Y", "axis2": 0},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], np.swapaxes(data, 2, 0))
    assert captured["axes"] == "YZTX"


def test_swap_axes_preserves_existing_metadata_keys(monkeypatch, tmp_path: Path) -> None:
    """Test that swap_axes output includes axes metadata."""
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.swap_axes(
        inputs={
            "image": {
                "uri": "file:///tmp/sample.tif",
                "metadata": {"axes": "ZYX", "physical_pixel_sizes": {"Z": 1.0}},
            }
        },
        params={"axis1": "Z", "axis2": "X"},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], np.swapaxes(data, 0, 2))
    assert captured["axes"] == "XYZ"

    metadata = result["outputs"]["output"]["metadata"]
    assert metadata["axes"] == "XYZ"
    assert metadata["physical_pixel_sizes"] == {"Z": 1.0}


def test_swap_axes_double_swap_invariant(monkeypatch, tmp_path: Path) -> None:
    """Test that swapping twice returns to original (data reorder invariant)."""
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, list[np.ndarray]] = {"arrays": []}
    calls = {"count": 0}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["arrays"].append(array)
        return work_dir / name

    def _load_image(_path: Path) -> np.ndarray:
        if calls["count"] == 0:
            calls["count"] += 1
            return data
        return captured["arrays"][0]

    monkeypatch.setattr(axis_ops, "load_image", _load_image)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    axis_ops.swap_axes(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"axis1": 0, "axis2": 2},
        work_dir=tmp_path,
    )
    axis_ops.swap_axes(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "XYZ"}}},
        params={"axis1": 2, "axis2": 0},
        work_dir=tmp_path,
    )

    assert len(captured["arrays"]) == 2
    np.testing.assert_array_equal(captured["arrays"][1], data)


def test_moveaxis_same_position_noop(monkeypatch, tmp_path: Path) -> None:
    """Test that moveaxis with source == destination is effectively a no-op."""
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)
    captured: dict[str, object] = {}

    def _write_ome_tiff(array: np.ndarray, work_dir: Path, name: str, axes: str) -> Path:
        captured["array"] = array
        captured["axes"] = axes
        return work_dir / name

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)
    monkeypatch.setattr(axis_ops, "_write_ome_tiff", _write_ome_tiff)

    result = axis_ops.moveaxis(
        inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
        params={"source": 1, "destination": 1},
        work_dir=tmp_path,
    )

    assert result["outputs"]["output"]["format"] == "OME-TIFF"
    np.testing.assert_array_equal(captured["array"], data)
    assert captured["axes"] == "ZYX"


def test_moveaxis_invalid_axis_name_error(monkeypatch, tmp_path: Path) -> None:
    """Test that invalid axis name gives actionable error message (NFR-004)."""
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)

    with pytest.raises(ValueError) as excinfo:
        axis_ops.moveaxis(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
            params={"source": "W", "destination": 1},
            work_dir=tmp_path,
        )

    message = str(excinfo.value)
    assert "W" in message
    assert "ZYX" in message


def test_swap_axes_out_of_bounds_error(monkeypatch, tmp_path: Path) -> None:
    """Test that out-of-bounds axis index gives actionable error message."""
    data = np.arange(2 * 3 * 4, dtype="uint8").reshape(2, 3, 4)

    monkeypatch.setattr(axis_ops, "load_image", lambda _path: data)

    with pytest.raises(ValueError) as excinfo:
        axis_ops.swap_axes(
            inputs={"image": {"uri": "file:///tmp/sample.tif", "metadata": {"axes": "ZYX"}}},
            params={"axis1": 5, "axis2": 1},
            work_dir=tmp_path,
        )

    message = str(excinfo.value)
    assert "5" in message
    assert "ndim=3" in message


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
