from __future__ import annotations

import json
import sys
from pathlib import Path

from bioimage_mcp_builtin.ops.convert_to_ome_zarr import convert_to_ome_zarr
from bioimage_mcp_builtin.ops.gaussian_blur import gaussian_blur


def main() -> int:
    request = json.loads(sys.stdin.read() or "{}")

    fn_id = request.get("fn_id")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        if fn_id == "builtin.convert_to_ome_zarr":
            out_path = convert_to_ome_zarr(inputs=inputs, params=params, work_dir=work_dir)
        elif fn_id == "builtin.gaussian_blur":
            out_path = gaussian_blur(inputs=inputs, params=params, work_dir=work_dir)
        else:
            raise ValueError(f"Unknown fn_id: {fn_id}")

        response = {
            "ok": True,
            "outputs": {
                "output": {
                    "type": "BioImageRef",
                    "format": "OME-Zarr",
                    "path": str(out_path),
                }
            },
            "log": "ok",
        }
    except Exception as exc:  # noqa: BLE001
        response = {"ok": False, "error": {"message": str(exc)}, "outputs": {}, "log": "failed"}

    print(json.dumps(response))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
