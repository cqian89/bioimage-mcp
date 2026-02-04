from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from bioio import BioImage

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.fixture
def native_executor():
    return NativeExecutor()


@pytest.fixture
def synthetic_image():
    """Use existing synthetic image for testing."""
    path = Path("datasets/synthetic/test.tif")
    if not path.exists():
        pytest.skip(f"Dataset missing: {path}")
    return path


@pytest.mark.smoke_pr
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_skimage_gaussian_equivalence(
    live_server, synthetic_image, helper, native_executor, tmp_path
):
    """Test that MCP skimage gaussian matches native skimage gaussian."""
    sigma = 1.5

    # 1. Run MCP Gaussian
    # First load image via MCP to get a BioImageRef
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(synthetic_image)},
        },
    )
    assert load_result["status"] == "success", f"Load failed: {load_result.get('error')}"
    img_ref = load_result["outputs"]["image"]

    # Run gaussian
    mcp_result = await live_server.call_tool(
        "run",
        {
            "id": "base.skimage.filters.gaussian",
            "inputs": {"image": img_ref},
            "params": {"sigma": sigma},
        },
    )
    assert mcp_result.get("status") == "success", f"MCP run failed: {mcp_result}"
    mcp_output_ref = mcp_result["outputs"]["output"]

    # 2. Run Native Baseline
    baseline_script = Path(__file__).parent / "reference_scripts" / "skimage_baseline.py"
    native_output_path = tmp_path / "native_gaussian.ome.tiff"

    baseline_result = native_executor.run_script(
        env_name="bioimage-mcp-base",
        script_path=baseline_script,
        args=[
            "--filter",
            "gaussian",
            "--input",
            str(synthetic_image),
            "--output",
            str(native_output_path),
            "--sigma",
            str(sigma),
        ],
    )
    assert baseline_result["status"] == "success"

    # 3. Compare
    mcp_uri = mcp_output_ref["uri"]
    assert mcp_uri.startswith("file://")
    mcp_path = Path(mcp_uri.replace("file://", ""))

    # Load both and compare
    mcp_img = BioImage(mcp_path)
    native_img = BioImage(native_output_path)

    helper.assert_arrays_equivalent(np.asarray(mcp_img.data), np.asarray(native_img.data))


@pytest.mark.smoke_extended
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_skimage_sobel_equivalence(
    live_server, synthetic_image, helper, native_executor, tmp_path
):
    """Test that MCP skimage sobel matches native skimage sobel."""
    # 1. Run MCP Sobel
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(synthetic_image)},
        },
    )
    assert load_result["status"] == "success", f"Load failed: {load_result.get('error')}"
    img_ref = load_result["outputs"]["image"]

    mcp_result = await live_server.call_tool(
        "run",
        {
            "id": "base.skimage.filters.sobel",
            "inputs": {"image": img_ref},
        },
    )
    assert mcp_result.get("status") == "success", f"MCP run failed: {mcp_result}"
    mcp_output_ref = mcp_result["outputs"]["output"]

    # 2. Run Native Baseline
    baseline_script = Path(__file__).parent / "reference_scripts" / "skimage_baseline.py"
    native_output_path = tmp_path / "native_sobel.ome.tiff"

    baseline_result = native_executor.run_script(
        env_name="bioimage-mcp-base",
        script_path=baseline_script,
        args=[
            "--filter",
            "sobel",
            "--input",
            str(synthetic_image),
            "--output",
            str(native_output_path),
        ],
    )
    assert baseline_result["status"] == "success"

    # 3. Compare
    mcp_uri = mcp_output_ref["uri"]
    assert mcp_uri.startswith("file://")
    mcp_path = Path(mcp_uri.replace("file://", ""))

    mcp_img = BioImage(mcp_path)
    native_img = BioImage(native_output_path)

    helper.assert_arrays_equivalent(np.asarray(mcp_img.data), np.asarray(native_img.data))
