from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# Import io functions directly for testing
# Make sure we can import bioimage_mcp_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "base"))
from bioimage_mcp_base.ops.io import export, inspect, load, slice_image

EXPECTED_IO_FUNCTIONS = {
    "base.io.bioimage.load",
    "base.io.bioimage.inspect",
    "base.io.bioimage.slice",
    "base.io.bioimage.validate",
    "base.io.bioimage.get_supported_formats",
    "base.io.bioimage.export",
}

DEPRECATED_FUNCTIONS = {
    "base.bioio.export",
}


def test_io_function_discovery(mcp_test_client):
    """
    T049: Verify all 6 I/O functions are discoverable and deprecated one is absent.
    """
    # 1. Check list_tools/search_functions for presence of expected functions
    search_result = mcp_test_client.search_functions("base.io.bioimage")
    found_fns = {fn["fn_id"] for fn in search_result.get("functions", [])}

    missing = EXPECTED_IO_FUNCTIONS - found_fns
    assert not missing, f"Missing expected I/O functions: {missing}"

    # 2. Verify deprecated functions are NOT in discovery
    found_deprecated = DEPRECATED_FUNCTIONS & found_fns
    assert not found_deprecated, f"Found deprecated functions: {found_deprecated}"

    # 3. Double check base.bioio.export specifically isn't there in a broader search
    all_tools = mcp_test_client.list_tools(flatten=True)
    all_fn_ids = {fn["fn_id"] for fn in all_tools.get("functions", [])}
    assert "base.bioio.export" not in all_fn_ids, (
        "base.bioio.export should be removed/deprecated from discovery"
    )

    # 4. Verify describe_function returns valid schema for each
    for fn_id in EXPECTED_IO_FUNCTIONS:
        desc = mcp_test_client.describe_function(fn_id)
        assert desc, f"Could not describe function {fn_id}"
        assert "fn_id" in desc
        assert desc["fn_id"] == fn_id
        assert "schema" in desc
        assert isinstance(desc["schema"], dict)


def create_test_ome_tiff(tmp_path, shape=(1, 2, 10, 64, 64)):
    """Create a test OME-TIFF file."""
    from bioio.writers import OmeTiffWriter

    data = np.random.randint(0, 255, shape, dtype=np.uint16)
    path = tmp_path / "test_image.ome.tiff"
    OmeTiffWriter.save(data, str(path), dim_order="TCZYX")
    return path


def test_load_inspect_slice_export_workflow(tmp_path, monkeypatch):
    """T046: Full load→inspect→slice→export workflow with OME-TIFF."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    # Create sample image
    sample_path = create_test_ome_tiff(tmp_path)

    # 1. Load
    load_result = load(inputs={}, params={"path": str(sample_path)}, work_dir=tmp_path)
    image_ref = load_result["outputs"]["image"]
    assert image_ref["type"] == "BioImageRef"

    # 2. Inspect
    inspect_result = inspect(inputs={}, params={"path": str(sample_path)}, work_dir=tmp_path)
    metadata = inspect_result["outputs"]["metadata"]
    assert "shape" in metadata

    # 3. Slice (middle Z-plane)
    mid_z = 5  # We created 10 Z slices
    slice_result = slice_image(
        inputs={"image": image_ref}, params={"slices": {"Z": mid_z}}, work_dir=tmp_path
    )
    sliced_ref = slice_result["outputs"]["output"]

    # 4. Export to OME-TIFF
    export_result = export(
        inputs={"image": sliced_ref}, params={"format": "OME-TIFF"}, work_dir=tmp_path
    )
    assert export_result["outputs"]["output"]["format"] == "OME-TIFF"


def test_slice_z_export_png_workflow(tmp_path, monkeypatch):
    """T047: Load → slice Z-plane → export PNG workflow."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    # Create 2D-able test image (1 T, 1 C, 5 Z, 64x64)
    sample_path = create_test_ome_tiff(tmp_path, shape=(1, 1, 5, 64, 64))

    # Load
    load_result = load(inputs={}, params={"path": str(sample_path)}, work_dir=tmp_path)
    image_ref = load_result["outputs"]["image"]

    # Slice single Z to get 2D
    slice_result = slice_image(
        inputs={"image": image_ref}, params={"slices": {"Z": 2, "T": 0, "C": 0}}, work_dir=tmp_path
    )
    sliced_ref = slice_result["outputs"]["output"]

    # Export to PNG
    export_result = export(
        inputs={"image": sliced_ref}, params={"format": "PNG"}, work_dir=tmp_path
    )
    assert export_result["outputs"]["output"]["format"] == "PNG"


@pytest.mark.skip(reason="LIF sample not available in test environment")
def test_lif_workflow(tmp_path):
    """T048: Load→slice→export with LIF format."""
    pass


def test_provenance_recording(tmp_path, monkeypatch):
    """T066: Verify provenance includes source_ref_id."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    sample_path = create_test_ome_tiff(tmp_path)

    # Load
    load_result = load(inputs={}, params={"path": str(sample_path)}, work_dir=tmp_path)
    image_ref = load_result["outputs"]["image"]
    orig_ref_id = image_ref["ref_id"]

    # Slice
    slice_result = slice_image(
        inputs={"image": image_ref}, params={"slices": {"Z": 0}}, work_dir=tmp_path
    )
    sliced_ref = slice_result["outputs"]["output"]

    # Verify provenance: sliced output should have source_ref_id pointing to original
    assert "source_ref_id" in sliced_ref.get("metadata", {})
    assert sliced_ref["metadata"]["source_ref_id"] == orig_ref_id
