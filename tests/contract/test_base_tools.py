from __future__ import annotations

from pathlib import Path

from bioimage_mcp.registry.loader import load_manifests

EXPECTED_BASE_FUNCTIONS = {
    "base.bioimage_mcp_base.io.convert_to_ome_zarr",
    "base.bioimage_mcp_base.io.export_ome_tiff",
    "base.bioimage_mcp_base.transforms.project_sum",
    "base.bioimage_mcp_base.transforms.project_max",
    "base.bioimage_mcp_base.transforms.resize",
    "base.bioimage_mcp_base.transforms.rescale",
    "base.bioimage_mcp_base.transforms.rotate",
    "base.bioimage_mcp_base.transforms.flip",
    "base.bioimage_mcp_base.transforms.crop",
    "base.bioimage_mcp_base.transforms.pad",
    "base.bioimage_mcp_base.preprocess.normalize_intensity",
    "base.bioimage_mcp_base.preprocess.gaussian",
    "base.bioimage_mcp_base.preprocess.median",
    "base.bioimage_mcp_base.preprocess.bilateral",
    "base.bioimage_mcp_base.preprocess.denoise_nl_means",
    "base.bioimage_mcp_base.preprocess.unsharp_mask",
    "base.bioimage_mcp_base.preprocess.equalize_adapthist",
    "base.bioimage_mcp_base.preprocess.sobel",
    "base.bioimage_mcp_base.preprocess.threshold_otsu",
    "base.bioimage_mcp_base.preprocess.threshold_yen",
    "base.bioimage_mcp_base.preprocess.morph_opening",
    "base.bioimage_mcp_base.preprocess.morph_closing",
    "base.bioimage_mcp_base.preprocess.remove_small_objects",
    "base.bioimage_mcp_base.transforms.phasor_from_flim",
    "base.bioimage_mcp_base.preprocess.denoise_image",
    "base.bioimage_mcp_base.transforms.phasor_calibrate",
    "meta.describe",
}


def test_base_tool_manifest_functions() -> None:
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifests, _ = load_manifests([tools_root])
    base = next(m for m in manifests if m.tool_id == "tools.base")
    fn_ids = {fn.fn_id for fn in base.functions}

    missing = EXPECTED_BASE_FUNCTIONS - fn_ids
    assert not missing, f"Missing base functions: {sorted(missing)}"
