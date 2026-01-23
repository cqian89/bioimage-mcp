from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from bioio import BioImage
import pandas as pd

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.fixture
def native_executor():
    return NativeExecutor()


@pytest.fixture
def vendored_trackpy_image():
    """Path to the vendored trackpy example image."""
    path = Path.cwd() / "datasets" / "trackpy-examples" / "bulk_water" / "frame000_green.ome.tiff"
    if not path.exists():
        pytest.skip(f"Vendored trackpy data not found at {path}")
    return path


@pytest.mark.smoke_full
@pytest.mark.requires_env("bioimage-mcp-trackpy")
@pytest.mark.anyio
async def test_trackpy_locate_equivalence(
    live_server, vendored_trackpy_image, helper, native_executor, tmp_path
):
    """
    Test that MCP trackpy.locate matches native trackpy.locate (TRACK-05).
    Uses vendored docs data (TRACK-04).
    """
    diameter = 11
    minmass = 10000.0
    invert = True  # bulk_water has dark particles on light background

    # 1. Run MCP Trackpy
    # Load image via MCP
    load_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(vendored_trackpy_image)},
        },
    )
    assert load_result["status"] == "success", f"Load failed: {load_result.get('error')}"
    img_ref = load_result["outputs"]["image"]

    # Run trackpy.locate
    mcp_result = await live_server.call_tool(
        "run",
        {
            "fn_id": "trackpy.locate",
            "inputs": {"raw_image": img_ref},
            "params": {"diameter": str(diameter), "minmass": str(minmass), "invert": invert},
        },
    )
    assert mcp_result.get("status") == "success", f"MCP run failed: {mcp_result}"
    mcp_output_ref = mcp_result["outputs"]["features"]

    # 2. Run Native Baseline
    baseline_script = Path(__file__).parent / "reference_scripts" / "trackpy_baseline.py"
    native_output_path = tmp_path / "native_features.csv"

    baseline_result = native_executor.run_script(
        env_name="bioimage-mcp-trackpy",
        script_path=baseline_script,
        args=[
            "--input",
            str(vendored_trackpy_image),
            "--output",
            str(native_output_path),
            "--diameter",
            str(diameter),
            "--minmass",
            str(minmass),
            "--invert" if invert else "",
        ],
    )
    assert baseline_result["status"] == "success", f"Baseline failed: {baseline_result}"

    # 3. Compare Results
    mcp_path = Path(mcp_output_ref["path"])

    # Load both result sets
    mcp_df = pd.read_csv(mcp_path)
    native_df = pd.read_csv(native_output_path)

    # Trackpy results can have slight variations in numeric precision
    # depending on the environment and library versions.
    # We use a 1e-3 relative tolerance which is safe for tracking centroids.

    # Sort by coordinates to ensure row-wise correspondence for assert_frame_equal
    mcp_df = mcp_df.sort_values(["y", "x"]).reset_index(drop=True)
    native_df = native_df.sort_values(["y", "x"]).reset_index(drop=True)

    # Basic validations before full frame comparison
    assert len(mcp_df) == len(native_df), (
        f"Feature count mismatch: {len(mcp_df)} != {len(native_df)}"
    )
    assert set(mcp_df.columns) == set(native_df.columns), (
        f"Columns mismatch: {mcp_df.columns} != {native_df.columns}"
    )

    # Use helper for frame comparison with tolerance
    helper.assert_table_equivalent(mcp_df, native_df, rtol=1e-3)

    # Specific trackpy-centric checks
    # Mass should be very close
    assert np.isclose(mcp_df["mass"].mean(), native_df["mass"].mean(), rtol=1e-4)
    # At least some features should have been found
    assert len(mcp_df) > 10
