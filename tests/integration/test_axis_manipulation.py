"""Integration tests for xarray axis manipulation operations (T033-T036)."""

import numpy as np
import pytest
import xarray as xr

from bioimage_mcp.registry.dynamic.xarray_adapter import XarrayAdapter


class TestAxisManipulation:
    """Integration tests for xarray axis manipulation operations."""

    @pytest.fixture
    def adapter(self):
        return XarrayAdapter()

    @pytest.fixture
    def sample_5d_data(self):
        """Create sample 5D data (T=2, C=3, Z=4, Y=64, X=64)."""
        return xr.DataArray(
            np.random.rand(2, 3, 4, 64, 64).astype(np.float32),
            dims=["T", "C", "Z", "Y", "X"],
            attrs={"physical_pixel_sizes": {"X": 0.1, "Y": 0.1, "Z": 0.5}},
        )

    @pytest.fixture
    def data_with_singleton(self):
        """Create data with singleton dimensions."""
        return xr.DataArray(
            np.random.rand(1, 3, 1, 64, 64).astype(np.float32), dims=["T", "C", "Z", "Y", "X"]
        )

    def test_rename_z_to_t_updates_metadata(self, adapter):
        """T033: Test that rename Z->T correctly updates dimension names."""
        data = xr.DataArray(np.random.rand(4, 64, 64), dims=["Z", "Y", "X"])
        result = adapter.execute("rename", data, mapping={"Z": "T"})
        assert "T" in result.dims
        assert "Z" not in result.dims
        assert result.dims == ("T", "Y", "X")
        assert result.shape == data.shape  # Shape unchanged

    def test_squeeze_removes_singleton_dimensions(self, adapter, data_with_singleton):
        """T034: Test that squeeze removes singleton dimensions."""
        assert data_with_singleton.shape[0] == 1  # T
        assert data_with_singleton.shape[2] == 1  # Z

        result = adapter.execute("squeeze", data_with_singleton)

        assert "T" not in result.dims
        assert "Z" not in result.dims
        assert result.dims == ("C", "Y", "X")
        assert result.shape == (3, 64, 64)

    def test_squeeze_specific_dim(self, adapter, data_with_singleton):
        """Test squeezing a specific dimension."""
        result = adapter.execute("squeeze", data_with_singleton, dim="T")

        assert "T" not in result.dims
        assert "Z" in result.dims
        assert result.dims == ("C", "Z", "Y", "X")

    def test_transpose_reorders_dimensions(self, adapter, sample_5d_data):
        """T035: Test that transpose correctly reorders dimensions."""
        result = adapter.execute("transpose", sample_5d_data, dims=["C", "T", "Z", "Y", "X"])

        assert result.dims == ("C", "T", "Z", "Y", "X")
        assert result.shape == (3, 2, 4, 64, 64)
        np.testing.assert_array_equal(
            result.values, np.transpose(sample_5d_data.values, (1, 0, 2, 3, 4))
        )

    def test_isel_selects_along_dimension(self, adapter, sample_5d_data):
        """T036: Test that isel correctly selects along dimensions."""
        result = adapter.execute("isel", sample_5d_data, T=0)

        assert "T" not in result.dims
        assert result.shape == (3, 4, 64, 64)
        np.testing.assert_array_equal(result.values, sample_5d_data.values[0])

    def test_isel_with_slice(self, adapter, sample_5d_data):
        """Test isel with slice selection."""
        result = adapter.execute("isel", sample_5d_data, Y=slice(10, 50))

        assert result.dims == sample_5d_data.dims
        assert result.shape == (2, 3, 4, 40, 64)

    def test_expand_dims_adds_dimension(self, adapter):
        """Test that expand_dims adds a new dimension."""
        data = xr.DataArray(np.random.rand(3, 64, 64), dims=["C", "Y", "X"])

        result = adapter.execute("expand_dims", data, dim="T", axis=0)

        assert result.dims == ("T", "C", "Y", "X")
        assert result.shape == (1, 3, 64, 64)

    def test_sum_reduction(self, adapter, sample_5d_data):
        """Test sum reduction along a dimension."""
        result = adapter.execute("sum_reduce", sample_5d_data, dim="Z")

        assert "Z" not in result.dims
        assert result.dims == ("T", "C", "Y", "X")
        assert result.shape == (2, 3, 64, 64)

    def test_mean_reduction(self, adapter, sample_5d_data):
        """Test mean reduction along a dimension."""
        result = adapter.execute("mean_reduce", sample_5d_data, dim="T")

        assert "T" not in result.dims
        assert result.shape == (3, 4, 64, 64)
