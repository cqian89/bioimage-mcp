from __future__ import annotations

import xarray as xr

from bioimage_mcp.registry.dynamic.allowlists import XARRAY_ALLOWLIST, is_allowed_method


class XarrayAdapter:
    """Adapter for exposing curated xarray.DataArray methods as MCP tools."""

    def __init__(self, allowlist: dict[str, dict] | None = None):
        self.allowlist = allowlist or XARRAY_ALLOWLIST

    def execute(self, method_name: str, data: xr.DataArray, **kwargs) -> xr.DataArray:
        """Execute an allowed xarray method on the data."""
        if not is_allowed_method(method_name):
            raise ValueError(f"Method '{method_name}' is not allowed")

        # Check if we have a specific handler in the adapter
        if hasattr(self, method_name):
            return getattr(self, method_name)(data, **kwargs)

        # Fallback to direct xarray method
        method = getattr(data, method_name)
        return method(**kwargs)

    def rename(self, data: xr.DataArray, mapping: dict[str, str]) -> xr.DataArray:
        """Rename dimensions of the DataArray."""
        return data.rename(mapping)

    def squeeze(self, data: xr.DataArray, dim: str | None = None) -> xr.DataArray:
        """Squeeze singleton dimensions."""
        return data.squeeze(dim=dim)

    def expand_dims(self, data: xr.DataArray, dim: str, axis: int | None = None) -> xr.DataArray:
        """Expand dimensions."""
        return data.expand_dims(dim=dim, axis=axis)

    def transpose(self, data: xr.DataArray, dims: list[str]) -> xr.DataArray:
        """Transpose dimensions."""
        return data.transpose(*dims)

    def isel(self, data: xr.DataArray, **indexers) -> xr.DataArray:
        """Select by index."""
        return data.isel(**indexers)

    def pad(self, data: xr.DataArray, pad_width: dict) -> xr.DataArray:
        """Pad the DataArray."""
        return data.pad(pad_width=pad_width)

    def sum_reduce(self, data: xr.DataArray, dim: str) -> xr.DataArray:
        """Reduce by sum."""
        return data.sum(dim=dim)

    def max_reduce(self, data: xr.DataArray, dim: str) -> xr.DataArray:
        """Reduce by max."""
        return data.max(dim=dim)

    def mean_reduce(self, data: xr.DataArray, dim: str) -> xr.DataArray:
        """Reduce by mean."""
        return data.mean(dim=dim)


def get_available_methods() -> list[str]:
    """Return list of available xarray method names."""
    return list(XARRAY_ALLOWLIST.keys())


def get_method_info(method_name: str) -> dict | None:
    """Return info about a specific method from the allowlist."""
    return XARRAY_ALLOWLIST.get(method_name)
