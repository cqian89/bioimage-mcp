import pytest
import importlib
from bioimage_mcp.registry.loader import load_manifest_file
from pathlib import Path


def test_wrapper_modules_importable(monkeypatch):
    """T018: Validate tools/base/bioimage_mcp_base/wrapper/ modules can be imported."""
    repo_root = Path(__file__).resolve().parents[3]
    tools_base = repo_root / "tools" / "base"
    monkeypatch.syspath_prepend(str(tools_base))

    # These should fail initially because the files don't exist yet
    modules = [
        "bioimage_mcp_base.wrapper.io",
        "bioimage_mcp_base.wrapper.axis",
        "bioimage_mcp_base.wrapper.phasor",
        "bioimage_mcp_base.wrapper.denoise",
        "bioimage_mcp_base.wrapper.edge_cases",
    ]

    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
        except ImportError:
            pytest.fail(f"Could not import {mod_name}")


def test_wrapper_namespace_in_manifest():
    """T018: Validate manifest functions list contains base.wrapper.* IDs."""
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = repo_root / "tools" / "base" / "manifest.yaml"

    manifest, diag = load_manifest_file(manifest_path)
    assert manifest is not None, f"Failed to load manifest: {diag}"

    wrapper_ids = [fn.fn_id for fn in manifest.functions if fn.fn_id.startswith("base.wrapper.")]

    expected_ids = {
        "base.wrapper.io.convert_to_ome_zarr",
        "base.wrapper.io.export_ome_tiff",
        "base.wrapper.axis.relabel_axes",
        "base.wrapper.axis.squeeze",
        "base.wrapper.axis.expand_dims",
        "base.wrapper.axis.moveaxis",
        "base.wrapper.axis.swap_axes",
        "base.wrapper.phasor.phasor_from_flim",
        "base.wrapper.phasor.phasor_calibrate",
        "base.wrapper.denoise.denoise_image",
        "base.wrapper.transform.crop",
        "base.wrapper.preprocess.normalize_intensity",
        "base.wrapper.transform.project_sum",
        "base.wrapper.transform.project_max",
        "base.wrapper.transform.flip",
        "base.wrapper.transform.pad",
    }

    missing_ids = expected_ids - set(wrapper_ids)
    assert not missing_ids, f"Missing wrapper IDs in manifest: {missing_ids}"

    # Also check that old IDs are NOT in the functions list (they will be in legacy redirects later)
    old_ids = {
        fn.fn_id for fn in manifest.functions if fn.fn_id.startswith("base.bioimage_mcp_base.")
    }
    assert not old_ids, f"Old IDs still present in functions list: {old_ids}"
