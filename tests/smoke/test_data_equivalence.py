from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import xarray as xr
from PIL import Image

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.mark.smoke_minimal
def test_assert_arrays_equivalent_pass(helper):
    actual = np.array([1.0, 2.0, 3.0])
    expected = np.array([1.0, 2.0, 3.00000001])
    helper.assert_arrays_equivalent(actual, expected)


@pytest.mark.smoke_minimal
def test_assert_arrays_equivalent_squeeze(helper):
    actual = np.array([[1.0, 2.0, 3.0]])
    expected = np.array([1.0, 2.0, 3.0])
    helper.assert_arrays_equivalent(actual, expected)


@pytest.mark.smoke_minimal
def test_assert_arrays_equivalent_fail_value(helper):
    actual = np.array([1.0, 2.0, 3.0])
    expected = np.array([1.0, 2.0, 4.0])
    with pytest.raises(AssertionError):
        helper.assert_arrays_equivalent(actual, expected)


@pytest.mark.smoke_minimal
def test_assert_arrays_equivalent_fail_shape(helper):
    actual = np.array([1.0, 2.0])
    expected = np.array([1.0, 2.0, 3.0])
    with pytest.raises(AssertionError):
        helper.assert_arrays_equivalent(actual, expected)


@pytest.mark.smoke_minimal
def test_assert_labels_equivalent_pass(helper):
    actual = np.zeros((10, 10), dtype=np.int32)
    actual[2:5, 2:5] = 1
    actual[6:8, 6:8] = 2

    expected = actual.copy()
    iou = helper.assert_labels_equivalent(actual, expected)
    assert iou == 1.0


@pytest.mark.smoke_minimal
def test_assert_labels_equivalent_offset(helper):
    # Slight offset should still pass if IoU threshold is met
    actual = np.zeros((10, 10), dtype=np.int32)
    actual[2:5, 2:5] = 1

    expected = np.zeros((10, 10), dtype=np.int32)
    expected[2:5, 3:6] = 1  # Shifted by 1 pixel

    # Area is 9. Intersection is 3x2=6. Union is 9+9-6=12. IoU = 6/12 = 0.5
    with pytest.raises(AssertionError):
        helper.assert_labels_equivalent(actual, expected, iou_threshold=0.99)

    iou = helper.assert_labels_equivalent(actual, expected, iou_threshold=0.4)
    assert 0.49 < iou < 0.51


@pytest.mark.smoke_minimal
def test_assert_plot_valid_pass(helper, tmp_path):
    plot_path = tmp_path / "plot.png"
    # Create a non-blank image
    data = np.zeros((100, 100, 3), dtype=np.uint8)
    data[25:75, 25:75, :] = 255
    img = Image.fromarray(data)
    img.save(plot_path)

    helper.assert_plot_valid(plot_path, min_size=100)


@pytest.mark.smoke_minimal
def test_assert_plot_valid_fail_missing(helper, tmp_path):
    plot_path = tmp_path / "missing.png"
    with pytest.raises(AssertionError, match="not exist"):
        helper.assert_plot_valid(plot_path)


@pytest.mark.smoke_minimal
def test_assert_plot_valid_fail_blank(helper, tmp_path):
    plot_path = tmp_path / "blank.png"
    data = np.zeros((100, 100, 3), dtype=np.uint8)
    img = Image.fromarray(data)
    img.save(plot_path)

    with pytest.raises(AssertionError, match="variance"):
        helper.assert_plot_valid(plot_path, min_variance=1.0, min_size=10)


@pytest.mark.smoke_minimal
def test_assert_plot_valid_dimensions_tolerance(helper, tmp_path):
    plot_path = tmp_path / "plot_dims.png"
    data = np.zeros((100, 200, 3), dtype=np.uint8)
    data[25:75, 25:75, :] = 255
    img = Image.fromarray(data)
    img.save(plot_path)

    # Exact match
    helper.assert_plot_valid(plot_path, expected_width=200, expected_height=100, min_size=10)

    # Within tolerance
    helper.assert_plot_valid(
        plot_path, expected_width=205, expected_height=95, dimension_tolerance=10, min_size=10
    )

    # Outside tolerance (width)
    with pytest.raises(AssertionError, match="width"):
        helper.assert_plot_valid(
            plot_path,
            expected_width=215,
            expected_height=100,
            dimension_tolerance=10,
            min_size=10,
        )

    # Outside tolerance (height)
    with pytest.raises(AssertionError, match="height"):
        helper.assert_plot_valid(
            plot_path,
            expected_width=200,
            expected_height=85,
            dimension_tolerance=10,
            min_size=10,
        )


@pytest.mark.smoke_minimal
def test_assert_plot_valid_intensity_stats(helper, tmp_path):
    plot_path = tmp_path / "plot_stats.png"
    # Create image with mean ~127.5
    data = np.full((100, 100, 3), 127, dtype=np.uint8)
    img = Image.fromarray(data)
    img.save(plot_path)

    # Should pass with wide ranges
    helper.assert_plot_valid(
        plot_path, min_mean=120, max_mean=130, min_std=0, min_size=10, min_variance=0
    )

    # Fail mean too low
    with pytest.raises(AssertionError, match="mean"):
        helper.assert_plot_valid(plot_path, min_mean=130, min_size=10, min_variance=0)

    # Fail mean too high
    with pytest.raises(AssertionError, match="mean"):
        helper.assert_plot_valid(plot_path, max_mean=120, min_size=10, min_variance=0)

    # Create image with some variance
    data[:50, :, :] = 0
    data[50:, :, :] = 255
    # mean ~ 127.5, std ~ 127.5
    img = Image.fromarray(data)
    img.save(plot_path)

    helper.assert_plot_valid(plot_path, min_std=100, min_size=10)

    # Fail std too low
    with pytest.raises(AssertionError, match="std"):
        helper.assert_plot_valid(plot_path, min_std=150, min_size=10)


@pytest.mark.smoke_minimal
def test_assert_table_equivalent_pass(helper):
    df1 = pd.DataFrame({"a": [1.0, 2.0], "b": [3, 4]})
    df2 = pd.DataFrame({"a": [1.00000001, 2.0], "b": [3, 4]})
    helper.assert_table_equivalent(df1, df2)


@pytest.mark.smoke_minimal
def test_assert_table_equivalent_column_order(helper):
    df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    df2 = pd.DataFrame({"b": [3, 4], "a": [1, 2]})
    helper.assert_table_equivalent(df1, df2, check_column_order=False)

    with pytest.raises(AssertionError):
        helper.assert_table_equivalent(df1, df2, check_column_order=True)


@pytest.mark.smoke_minimal
def test_assert_table_equivalent_fail_value(helper):
    df1 = pd.DataFrame({"a": [1, 2]})
    df2 = pd.DataFrame({"a": [1, 3]})
    with pytest.raises(AssertionError):
        helper.assert_table_equivalent(df1, df2)


@pytest.mark.smoke_minimal
def test_assert_metadata_preserved_pass(helper):
    data = np.random.rand(4, 5)
    da1 = xr.DataArray(
        data,
        dims=("y", "x"),
        coords={"y": [1, 2, 3, 4], "x": [10, 20, 30, 40, 50]},
        attrs={"units": "um", "standard_name": "test"},
    )
    da2 = da1.copy(deep=True)
    helper.assert_metadata_preserved(da1, da2)


@pytest.mark.smoke_minimal
def test_assert_metadata_preserved_fail_dims(helper):
    data = np.random.rand(4, 5)
    da1 = xr.DataArray(data, dims=("y", "x"))
    da2 = xr.DataArray(data, dims=("row", "col"))
    with pytest.raises(AssertionError, match="dimension names"):
        helper.assert_metadata_preserved(da1, da2)


@pytest.mark.smoke_minimal
def test_assert_metadata_preserved_fail_coords(helper):
    data = np.random.rand(4, 5)
    da1 = xr.DataArray(data, dims=("y", "x"), coords={"y": [1, 2, 3, 4], "x": [1, 2, 3, 4, 5]})
    da2 = xr.DataArray(data, dims=("y", "x"), coords={"y": [1, 2, 3, 4], "x": [1, 2, 3, 4, 6]})
    with pytest.raises(AssertionError, match="coordinates"):
        helper.assert_metadata_preserved(da1, da2)


@pytest.mark.smoke_minimal
def test_assert_metadata_preserved_fail_attrs(helper):
    data = np.random.rand(4, 5)
    da1 = xr.DataArray(data, dims=("y", "x"), attrs={"units": "um"})
    da2 = xr.DataArray(data, dims=("y", "x"), attrs={"units": "mm"})
    with pytest.raises(AssertionError, match="attributes"):
        helper.assert_metadata_preserved(da1, da2)
