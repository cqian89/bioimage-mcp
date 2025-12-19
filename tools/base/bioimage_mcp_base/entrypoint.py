#!/usr/bin/env python3
"""Base tool pack entrypoint for bioimage-mcp."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from bioimage_mcp.runtimes.introspect import introspect_python_api

from bioimage_mcp_base import descriptions as desc
from bioimage_mcp_base.io import convert_to_ome_zarr, export_ome_tiff
from bioimage_mcp_base.preprocess import (
    bilateral,
    denoise_nl_means,
    equalize_adapthist,
    gaussian,
    median,
    morph_closing,
    morph_opening,
    normalize_intensity,
    remove_small_objects,
    sobel,
    threshold_otsu,
    threshold_yen,
    unsharp_mask,
)
from bioimage_mcp_base.transforms import (
    crop,
    flip,
    pad,
    project_max,
    project_sum,
    rescale,
    resize,
    rotate,
)

TOOL_VERSION = "0.1.0"


FN_MAP = {
    "base.convert_to_ome_zarr": (convert_to_ome_zarr, desc.CONVERT_TO_OME_ZARR_DESCRIPTIONS),
    "base.export_ome_tiff": (export_ome_tiff, desc.EXPORT_OME_TIFF_DESCRIPTIONS),
    "base.project_sum": (project_sum, desc.PROJECT_SUM_DESCRIPTIONS),
    "base.project_max": (project_max, desc.PROJECT_MAX_DESCRIPTIONS),
    "base.resize": (resize, desc.RESIZE_DESCRIPTIONS),
    "base.rescale": (rescale, desc.RESCALE_DESCRIPTIONS),
    "base.rotate": (rotate, desc.ROTATE_DESCRIPTIONS),
    "base.flip": (flip, desc.FLIP_DESCRIPTIONS),
    "base.crop": (crop, desc.CROP_DESCRIPTIONS),
    "base.pad": (pad, desc.PAD_DESCRIPTIONS),
    "base.normalize_intensity": (normalize_intensity, desc.NORMALIZE_INTENSITY_DESCRIPTIONS),
    "base.gaussian": (gaussian, desc.GAUSSIAN_DESCRIPTIONS),
    "base.median": (median, desc.MEDIAN_DESCRIPTIONS),
    "base.bilateral": (bilateral, desc.BILATERAL_DESCRIPTIONS),
    "base.denoise_nl_means": (denoise_nl_means, desc.DENOISE_NL_MEANS_DESCRIPTIONS),
    "base.unsharp_mask": (unsharp_mask, desc.UNSHARP_MASK_DESCRIPTIONS),
    "base.equalize_adapthist": (equalize_adapthist, desc.EQUALIZE_ADAPTHIST_DESCRIPTIONS),
    "base.sobel": (sobel, desc.SOBEL_DESCRIPTIONS),
    "base.threshold_otsu": (threshold_otsu, desc.THRESHOLD_OTSU_DESCRIPTIONS),
    "base.threshold_yen": (threshold_yen, desc.THRESHOLD_YEN_DESCRIPTIONS),
    "base.morph_opening": (morph_opening, desc.MORPH_OPENING_DESCRIPTIONS),
    "base.morph_closing": (morph_closing, desc.MORPH_CLOSING_DESCRIPTIONS),
    "base.remove_small_objects": (remove_small_objects, desc.REMOVE_SMALL_OBJECTS_DESCRIPTIONS),
}


def handle_meta_describe(params: dict[str, Any]) -> dict[str, Any]:
    target_fn = params.get("target_fn", "")
    if target_fn not in FN_MAP:
        return {"ok": False, "error": f"Unknown function: {target_fn}"}

    func, descriptions = FN_MAP[target_fn]
    schema = introspect_python_api(func, descriptions, exclude_params={"inputs", "params", "work_dir"})

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

    try:
        if fn_id == "meta.describe":
            response = handle_meta_describe(params)
        elif fn_id in FN_MAP:
            func, _descriptions = FN_MAP[fn_id]
            out_path = func(inputs=inputs, params=params, work_dir=work_dir)
            fmt = "OME-Zarr"
            if fn_id == "base.export_ome_tiff":
                fmt = "OME-TIFF"
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
            }
        else:
            response = {"ok": False, "error": f"Unknown fn_id: {fn_id}"}
    except Exception as exc:  # noqa: BLE001
        response = {"ok": False, "error": {"message": str(exc)}, "outputs": {}, "log": "failed"}

    print(json.dumps(response))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
