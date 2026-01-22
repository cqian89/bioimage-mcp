from __future__ import annotations

import json

import numpy as np
import xarray as xr


def main():
    # Use fixed seed for reproducibility across native and MCP
    np.random.seed(42)
    data = np.random.rand(10, 10).astype(np.float32)
    da = xr.DataArray(data, dims=["Y", "X"], name="synthetic")

    # Operation: mean
    res_da = da.mean()
    result = float(res_da)

    print(
        json.dumps(
            {
                "mean": result,
                "dims": list(res_da.dims),
                "coords": {k: list(v.values) for k, v in res_da.coords.items()},
            }
        )
    )


if __name__ == "__main__":
    main()
