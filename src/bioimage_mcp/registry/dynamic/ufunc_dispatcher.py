from collections.abc import Callable

import xarray as xr

from bioimage_mcp.registry.dynamic.models import ApplyUfuncConfig


class UfuncDispatcher:
    """Dispatcher for applying numpy functions to xarray data using apply_ufunc."""

    def dispatch(
        self, func: Callable, data: xr.DataArray, config: ApplyUfuncConfig, **kwargs
    ) -> xr.DataArray:
        """Apply a numpy function to xarray data using xr.apply_ufunc."""
        return xr.apply_ufunc(
            func,
            data,
            input_core_dims=config.input_core_dims,
            output_core_dims=config.output_core_dims,
            vectorize=config.vectorize,
            dask=config.dask,
            output_dtypes=config.output_dtypes,
            kwargs=kwargs,
        )

    def dispatch_spatial_filter(
        self, filter_func: Callable, data: xr.DataArray, **kwargs
    ) -> xr.DataArray:
        """Convenience method for spatial (YX) filters like gaussian, median."""
        config = ApplyUfuncConfig(
            input_core_dims=[["Y", "X"]],
            output_core_dims=[["Y", "X"]],
            vectorize=True,
            dask="parallelized",
        )
        return self.dispatch(filter_func, data, config, **kwargs)


def create_spatial_config() -> ApplyUfuncConfig:
    """Create config for YX spatial operations."""
    return ApplyUfuncConfig(
        input_core_dims=[["Y", "X"]],
        output_core_dims=[["Y", "X"]],
        vectorize=True,
        dask="parallelized",
    )


def create_volumetric_config() -> ApplyUfuncConfig:
    """Create config for ZYX volumetric operations."""
    return ApplyUfuncConfig(
        input_core_dims=[["Z", "Y", "X"]],
        output_core_dims=[["Z", "Y", "X"]],
        vectorize=True,
        dask="parallelized",
    )
