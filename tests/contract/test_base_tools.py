from __future__ import annotations

from pathlib import Path

from bioimage_mcp.registry.loader import load_manifests

EXPECTED_BASE_FUNCTIONS = {
    "base.xarray.rename",
    "base.xarray.squeeze",
    "base.xarray.expand_dims",
    "base.xarray.transpose",
    "base.xarray.isel",
    "base.xarray.pad",
    "base.xarray.sum",
    "base.xarray.max",
    "base.xarray.mean",
    "base.bioio.export",
    "base.skimage.transform.resize",
    "base.skimage.transform.rescale",
    "base.skimage.transform.rotate",
    "base.skimage.filters.gaussian",
    "base.skimage.filters.median",
    "base.skimage.restoration.denoise_bilateral",
    "base.skimage.restoration.denoise_nl_means",
    "base.skimage.filters.unsharp_mask",
    "base.skimage.exposure.equalize_adapthist",
    "base.skimage.filters.sobel",
    "base.skimage.filters.threshold_otsu",
    "base.skimage.filters.threshold_yen",
    "base.skimage.morphology.remove_small_objects",
    "meta.describe",
}


def test_base_tool_manifest_functions() -> None:
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifests, _ = load_manifests([tools_root])
    base = next(m for m in manifests if m.tool_id == "tools.base")
    fn_ids = {fn.fn_id for fn in base.functions}

    missing = EXPECTED_BASE_FUNCTIONS - fn_ids
    assert not missing, f"Missing base functions: {sorted(missing)}"
