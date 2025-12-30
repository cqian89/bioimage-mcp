#!/usr/bin/env python3
"""Base tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
TOOLS_ROOT = BASE_DIR.parent
REPO_ROOT = TOOLS_ROOT.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from bioimage_mcp_base import descriptions as desc  # noqa: I001, E402
from bioimage_mcp_base.wrapper import (  # noqa: I001, E402
    axis as axis_wrappers,
    denoise as denoise_wrappers,
    edge_cases as edge_wrappers,
    io as io_wrappers,
    phasor as phasor_wrappers,
)

TOOL_VERSION = "0.1.0"
TOOL_ENV_NAME = "bioimage-mcp-base"
DYNAMIC_FN_PREFIXES = ("base.", f"{TOOL_ENV_NAME}.")


FN_MAP = {
    # New wrapper namespace
    "base.wrapper.io.convert_to_ome_zarr": (
        io_wrappers.convert_to_ome_zarr,
        desc.CONVERT_TO_OME_ZARR_DESCRIPTIONS,
    ),
    "base.wrapper.io.export_ome_tiff": (
        io_wrappers.export_ome_tiff,
        desc.EXPORT_OME_TIFF_DESCRIPTIONS,
    ),
    "base.wrapper.axis.relabel_axes": (
        axis_wrappers.relabel_axes,
        desc.RELABEL_AXES_DESCRIPTIONS,
    ),
    "base.wrapper.axis.squeeze": (axis_wrappers.squeeze, desc.SQUEEZE_DESCRIPTIONS),
    "base.wrapper.axis.expand_dims": (
        axis_wrappers.expand_dims,
        desc.EXPAND_DIMS_DESCRIPTIONS,
    ),
    "base.wrapper.axis.moveaxis": (axis_wrappers.moveaxis, desc.MOVEAXIS_DESCRIPTIONS),
    "base.wrapper.axis.swap_axes": (axis_wrappers.swap_axes, desc.SWAP_AXES_DESCRIPTIONS),
    "base.wrapper.phasor.phasor_from_flim": (
        phasor_wrappers.phasor_from_flim,
        desc.PHASOR_FROM_FLIM_DESCRIPTIONS,
    ),
    "base.wrapper.phasor.phasor_calibrate": (
        phasor_wrappers.phasor_calibrate,
        desc.PHASOR_CALIBRATE_DESCRIPTIONS,
    ),
    "base.wrapper.denoise.denoise_image": (
        denoise_wrappers.denoise_image,
        desc.DENOISE_IMAGE_DESCRIPTIONS,
    ),
    "base.wrapper.transform.crop": (edge_wrappers.crop, desc.CROP_DESCRIPTIONS),
    "base.wrapper.preprocess.normalize_intensity": (
        edge_wrappers.normalize_intensity,
        desc.NORMALIZE_INTENSITY_DESCRIPTIONS,
    ),
    "base.wrapper.transform.project_sum": (
        edge_wrappers.project_sum,
        desc.PROJECT_SUM_DESCRIPTIONS,
    ),
    "base.wrapper.transform.project_max": (
        edge_wrappers.project_max,
        desc.PROJECT_MAX_DESCRIPTIONS,
    ),
    "base.wrapper.transform.flip": (edge_wrappers.flip, desc.FLIP_DESCRIPTIONS),
    "base.wrapper.transform.pad": (edge_wrappers.pad, desc.PAD_DESCRIPTIONS),
}

LEGACY_REDIRECTS = {
    "base.bioimage_mcp_base.io.convert_to_ome_zarr": "base.wrapper.io.convert_to_ome_zarr",
    "base.bioimage_mcp_base.io.export_ome_tiff": "base.wrapper.io.export_ome_tiff",
    "base.bioimage_mcp_base.transforms.project_sum": "base.wrapper.transform.project_sum",
    "base.bioimage_mcp_base.transforms.project_max": "base.wrapper.transform.project_max",
    "base.bioimage_mcp_base.transforms.flip": "base.wrapper.transform.flip",
    "base.bioimage_mcp_base.transforms.crop": "base.wrapper.transform.crop",
    "base.bioimage_mcp_base.transforms.pad": "base.wrapper.transform.pad",
    "base.bioimage_mcp_base.axis_ops.relabel_axes": "base.wrapper.axis.relabel_axes",
    "base.bioimage_mcp_base.axis_ops.squeeze": "base.wrapper.axis.squeeze",
    "base.bioimage_mcp_base.axis_ops.expand_dims": "base.wrapper.axis.expand_dims",
    "base.bioimage_mcp_base.axis_ops.moveaxis": "base.wrapper.axis.moveaxis",
    "base.bioimage_mcp_base.axis_ops.swap_axes": "base.wrapper.axis.swap_axes",
    "base.bioimage_mcp_base.preprocess.normalize_intensity": (
        "base.wrapper.preprocess.normalize_intensity"
    ),
    "base.bioimage_mcp_base.transforms.phasor_from_flim": "base.wrapper.phasor.phasor_from_flim",
    "base.bioimage_mcp_base.preprocess.denoise_image": "base.wrapper.denoise.denoise_image",
    "base.bioimage_mcp_base.transforms.phasor_calibrate": "base.wrapper.phasor.phasor_calibrate",
}


def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    target_fn = params.get("target_fn", "")
    if target_fn not in FN_MAP:
        return {"ok": False, "error": f"Unknown function: {target_fn}"}

    func, descriptions = FN_MAP[target_fn]

    # Import introspect_python_api only when needed (for meta.describe)
    try:
        from bioimage_mcp.runtimes.introspect import introspect_python_api
    except ImportError:
        return {"ok": False, "error": "Introspection not available in this environment"}

    schema = introspect_python_api(
        func, descriptions, exclude_params={"inputs", "params", "work_dir"}
    )

    return {
        "ok": True,
        "result": {
            "params_schema": schema,
            "tool_version": TOOL_VERSION,
            "introspection_source": "python_api",
        },
    }


def main() -> int:
    request = json.loads(sys.stdin.read() or "{}")

    fn_id = request.get("fn_id")
    params = request.get("params") or {}
    inputs = request.get("inputs") or {}
    work_dir = Path(request.get("work_dir") or ".").absolute()
    work_dir.mkdir(parents=True, exist_ok=True)

    warnings = []
    if fn_id in LEGACY_REDIRECTS:
        new_fn_id = LEGACY_REDIRECTS[fn_id]
        warnings.append(
            f"DEPRECATED: {fn_id} is deprecated and will be removed in v1.0.0. "
            f"Use {new_fn_id} instead."
        )
        fn_id = new_fn_id

    try:
        if fn_id == "meta.describe":
            response = handle_meta_describe(params)
        elif fn_id in FN_MAP:
            func, _descriptions = FN_MAP[fn_id]
            result = func(inputs=inputs, params=params, work_dir=work_dir)
            if isinstance(result, dict):
                outputs = result.get("outputs")
                if outputs is None:
                    raise ValueError(f"{fn_id} did not return outputs")
                response = {
                    "ok": True,
                    "outputs": outputs,
                    "log": result.get("log", "ok"),
                }
                # Combine tool-specific warnings with redirect warnings
                response["warnings"] = warnings + result.get("warnings", [])
                if "provenance" in result:
                    response["provenance"] = result["provenance"]
            else:
                out_path = result
                fmt = "OME-Zarr"
                response = {
                    "ok": True,
                    "outputs": {
                        "output": {
                            "type": "BioImageRef",
                            "format": fmt,
                            "path": str(out_path),
                        }
                    },
                    "log": "ok",
                    "warnings": warnings,
                }
        else:
            # Dynamic dispatch for functions not in FN_MAP
            from bioimage_mcp_base.dynamic_dispatch import dispatch_dynamic

            dynamic_fn_id = fn_id or ""
            for prefix in DYNAMIC_FN_PREFIXES:
                if dynamic_fn_id.startswith(prefix):
                    dynamic_fn_id = dynamic_fn_id[len(prefix) :]
                    break

            result = dispatch_dynamic(
                fn_id=dynamic_fn_id,
                inputs=inputs,
                params=params,
                work_dir=work_dir,
            )
            response = {
                "ok": True,
                "outputs": result.get("outputs", {}),
                "log": "ok (dynamic dispatch)",
            }
    except Exception as exc:  # noqa: BLE001
        error = {"message": str(exc)}
        error_code = getattr(exc, "code", None)
        if error_code:
            error["code"] = error_code
        response = {
            "ok": False,
            "error": error,
            "outputs": {},
            "log": "failed",
        }

    print(json.dumps(response))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
