from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tests.smoke.utils.native_executor import NativeExecutor


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_native_executor_initialization(native_executor):
    """Sanity check for NativeExecutor initialization and conda detection."""
    assert isinstance(native_executor, NativeExecutor)
    assert native_executor.conda_path is not None
    # We don't want to rely on any specific env existing here, but we can check if it can list envs
    # This might fail if no conda is installed, but the doctor should have caught that.
    # We can at least assert it doesn't crash.
    try:
        native_executor.env_exists("base")
    except Exception as e:
        # If conda is not working at all, this might fail, but let's see.
        pytest.fail(f"NativeExecutor failed to check for 'base' environment: {e}")


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_data_equivalence_arrays(helper, synthetic_image):
    """Sanity check for DataEquivalenceHelper array comparison."""
    # Same array should pass
    helper.assert_arrays_equivalent(synthetic_image, synthetic_image)

    # Slightly modified array should pass within tolerance
    modified = synthetic_image + 1e-9
    helper.assert_arrays_equivalent(synthetic_image, modified)

    # Very different array should fail
    with pytest.raises(AssertionError):
        helper.assert_arrays_equivalent(synthetic_image, synthetic_image + 1.0)


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_data_equivalence_labels(helper, synthetic_labels):
    """Sanity check for DataEquivalenceHelper label comparison."""
    # Same labels should pass
    iou = helper.assert_labels_equivalent(synthetic_labels, synthetic_labels)
    assert iou == 1.0

    # Different labels should fail or have low IoU
    different_labels = np.zeros_like(synthetic_labels)
    different_labels[0:5, 0:5] = 1

    with pytest.raises(AssertionError):
        helper.assert_labels_equivalent(synthetic_labels, different_labels, iou_threshold=0.9)


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_data_equivalence_dataframe(helper, synthetic_dataframe):
    """Sanity check for DataEquivalenceHelper table comparison."""
    # Same dataframe should pass
    helper.assert_table_equivalent(synthetic_dataframe, synthetic_dataframe)

    # Different dataframe should fail
    different_df = synthetic_dataframe.copy()
    different_df.iloc[0, 1] = 999.9

    with pytest.raises(AssertionError):
        helper.assert_table_equivalent(synthetic_dataframe, different_df)


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_data_equivalence_xarray(helper, synthetic_xarray):
    """Sanity check for DataEquivalenceHelper xarray comparison."""
    # Same xarray should pass
    helper.assert_metadata_preserved(synthetic_xarray, synthetic_xarray)

    # Different xarray should fail

    different_xr = synthetic_xarray.copy()
    different_xr.attrs["units"] = "meters"

    with pytest.raises(AssertionError):
        helper.assert_metadata_preserved(synthetic_xarray, different_xr)


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_synthetic_data_fixtures(
    synthetic_image, synthetic_labels, synthetic_dataframe, synthetic_xarray
):
    """Verify that synthetic data fixtures return expected types and shapes."""
    assert isinstance(synthetic_image, np.ndarray)
    assert synthetic_image.shape == (64, 64)
    assert synthetic_image.dtype == np.float32

    assert isinstance(synthetic_labels, np.ndarray)
    assert synthetic_labels.shape == (64, 64)
    assert synthetic_labels.dtype == np.uint16
    assert np.max(synthetic_labels) == 3

    assert isinstance(synthetic_dataframe, pd.DataFrame)
    assert len(synthetic_dataframe) == 3
    assert "area" in synthetic_dataframe.columns

    import xarray as xr

    assert isinstance(synthetic_xarray, xr.DataArray)
    assert synthetic_xarray.shape == (4, 64, 64)
    assert "c" in synthetic_xarray.dims


@pytest.mark.smoke_minimal
@pytest.mark.uses_minimal_data
def test_data_equivalence_plot(helper, tmp_path):
    """Sanity check for DataEquivalenceHelper plot validation."""
    import matplotlib.pyplot as plt

    plot_path = tmp_path / "test_plot.png"
    plt.figure(figsize=(4, 4), dpi=100)
    plt.plot([1, 2, 3], [1, 2, 3])
    plt.title("Test Plot")
    plt.savefig(plot_path)
    plt.close()

    # Should pass basic validation
    helper.assert_plot_valid(
        plot_path, expected_width=400, expected_height=400, dimension_tolerance=10
    )

    # Should fail if file doesn't exist
    with pytest.raises(AssertionError, match="does not exist"):
        helper.assert_plot_valid(tmp_path / "nonexistent.png")

    # Should fail if it looks blank (variance check)
    blank_path = tmp_path / "blank.png"
    import numpy as np
    from PIL import Image

    Image.fromarray(np.zeros((100, 100), dtype=np.uint8)).save(blank_path)

    with pytest.raises(AssertionError, match="appears blank"):
        helper.assert_plot_valid(blank_path, min_variance=1.0, min_size=0)
