from __future__ import annotations

from pathlib import Path

from bioimage_mcp.registry.loader import load_manifests


EXPECTED_BASE_FUNCTIONS = {
    "base.convert_to_ome_zarr",
    "base.export_ome_tiff",
    "base.project_sum",
    "base.project_max",
    "base.resize",
    "base.rescale",
    "base.rotate",
    "base.flip",
    "base.crop",
    "base.pad",
    "base.normalize_intensity",
    "base.gaussian",
    "base.median",
    "base.bilateral",
    "base.denoise_nl_means",
    "base.unsharp_mask",
    "base.equalize_adapthist",
    "base.sobel",
    "base.threshold_otsu",
    "base.threshold_yen",
    "base.morph_opening",
    "base.morph_closing",
    "base.remove_small_objects",
    "base.phasor_from_flim",
    "base.denoise_image",
    "meta.describe",
}


def test_base_tool_manifest_functions() -> None:
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifests, _ = load_manifests([tools_root])
    base = next(m for m in manifests if m.tool_id == "tools.base")
    fn_ids = {fn.fn_id for fn in base.functions}

    missing = EXPECTED_BASE_FUNCTIONS - fn_ids
    assert not missing, f"Missing base functions: {sorted(missing)}"
