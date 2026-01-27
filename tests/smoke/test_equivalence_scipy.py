from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import pytest
from bioio import BioImage

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor

SYNTHETIC_IMAGE = Path("datasets/synthetic/test.tif")


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.fixture
def native_executor():
    return NativeExecutor()


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_scipy_ndimage_gaussian_filter_equivalence(
    live_server, helper, native_executor, tmp_path
):
    """Test that MCP scipy.ndimage.gaussian_filter matches native execution.

    Verification includes:
    1. Pixel-level numerical equivalence (tolerance 1e-5)
    2. Dimension/shape preservation
    3. Proper OME-TIFF artifact creation by MCP
    """
    if not SYNTHETIC_IMAGE.exists():
        pytest.skip(f"Test image missing: {SYNTHETIC_IMAGE}")

    sigma = 1.5

    # 1. Run via MCP
    # Step A: Load image
    load_result = await live_server.call_tool_checked(
        "run",
        {
            "fn_id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(SYNTHETIC_IMAGE.absolute())},
        },
    )
    # The output key for load is "image" (from manifest)
    img_ref = load_result["outputs"]["image"]

    # Step B: Run gaussian_filter
    mcp_result = await live_server.call_tool_checked(
        "run",
        {
            "fn_id": "base.scipy.ndimage.gaussian_filter",
            "inputs": {"image": img_ref},
            "params": {"sigma": sigma},
        },
    )

    if mcp_result.get("status") != "success":
        log_ref = mcp_result.get("log_ref", {})
        log_id = log_ref.get("ref_id")
        log_content = "Log not available"
        if log_id:
            log_info = await live_server.call_tool(
                "artifact_info", {"ref_id": log_id, "text_preview_bytes": 2000}
            )
            log_content = log_info.get("text_preview", "Log preview not available")
        stderr = live_server.get_stderr()
        pytest.fail(
            f"MCP execution failed with status {mcp_result.get('status')}.\n"
            f"Error: {mcp_result.get('error')}\n"
            f"Log: {log_content}\n"
            f"Server STDERR: {stderr}"
        )

    # Scipy adapter returns [output_ref], which defaults to "output" in dynamic dispatch
    mcp_output_ref = mcp_result["outputs"]["output"]

    mcp_uri = mcp_output_ref["uri"]
    parsed = urlparse(mcp_uri)
    mcp_path = unquote(parsed.path)
    # Remove leading slash on Windows
    if mcp_path.startswith("/") and len(mcp_path) > 2 and mcp_path[2] == ":":
        mcp_path = mcp_path[1:]

    # Load MCP result data and force float32 for bit-for-bit comparison
    mcp_img = BioImage(mcp_path)
    mcp_data = mcp_img.reader.data
    if hasattr(mcp_data, "compute"):
        mcp_data = mcp_data.compute()
    mcp_data = np.asarray(mcp_data, dtype=np.float32)

    # 2. Run via Native Reference Script
    script_path = Path(__file__).parent / "reference_scripts" / "scipy_baseline.py"
    baseline_result = native_executor.run_script(
        "bioimage-mcp-base",
        script_path,
        ["--input", str(SYNTHETIC_IMAGE.absolute()), "--sigma", str(sigma)],
    )

    assert baseline_result["status"] == "success"
    expected_data = np.load(baseline_result["output_path"])
    expected_data = np.asarray(expected_data, dtype=np.float32)

    # 3. Compare bit-for-bit
    try:
        np.testing.assert_array_equal(mcp_data, expected_data)
    finally:
        # Cleanup baseline temp file
        baseline_tmp_path = Path(baseline_result["output_path"])
        if baseline_tmp_path.exists():
            baseline_tmp_path.unlink()
