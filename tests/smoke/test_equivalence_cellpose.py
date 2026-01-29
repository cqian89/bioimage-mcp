from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import scipy.ndimage as ndimage
from bioio import BioImage
from bioio.writers import OmeTiffWriter

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.fixture
def native_executor():
    return NativeExecutor()


@pytest.fixture
def synthetic_cell_image(tmp_path):
    """Generate a small synthetic image with cell-like blobs."""
    # Use datasets/synthetic which is explicitly allowed in config (T016 Fix)
    allowed_tmp = Path.cwd() / "datasets" / "synthetic"
    allowed_tmp.mkdir(parents=True, exist_ok=True)

    shape = (128, 128)
    img = np.zeros(shape, dtype=np.float32)
    # Seed for reproducibility of data generation
    rng = np.random.default_rng(42)

    for _ in range(8):
        r, c = rng.integers(15, shape[0] - 15), rng.integers(15, shape[1] - 15)
        rr, cc = np.ogrid[: shape[0], : shape[1]]
        radius = rng.integers(8, 12)
        mask = (rr - r) ** 2 + (cc - c) ** 2 <= radius**2
        img[mask] = 1.0

    # Smooth to make it look like cells
    img = ndimage.gaussian_filter(img, sigma=2)
    # Add noise
    img += rng.normal(0, 0.05, shape)
    img = np.clip(img, 0, 1)
    img_uint8 = (img * 255).astype(np.uint8)

    import uuid

    path = allowed_tmp / f"synthetic_cells_{uuid.uuid4().hex[:8]}.ome.tiff"
    OmeTiffWriter.save(img_uint8, str(path), dim_order="YX")

    yield path

    # Cleanup
    if path.exists():
        path.unlink()


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-cellpose")
@pytest.mark.anyio
async def test_cellpose_equivalence(
    live_server, synthetic_cell_image, helper, native_executor, tmp_path
):
    """Test that MCP cellpose matches native cellpose (IoU > 0.95)."""
    model_type = "cyto3"
    diameter = 30.0

    # 1. Run MCP Cellpose
    # Load image via MCP to get a BioImageRef
    load_result = await live_server.call_tool(
        "run",
        {
            "id": "base.io.bioimage.load",
            "inputs": {},
            "params": {"path": str(synthetic_cell_image)},
        },
    )
    assert load_result["status"] == "success", f"Load failed: {load_result.get('error')}"
    img_ref = load_result["outputs"]["image"]

    # Initialize model
    model_init_result = await live_server.call_tool(
        "run",
        {
            "id": "cellpose.models.CellposeModel",
            "inputs": {},
            "params": {"model_type": model_type, "gpu": False},
        },
    )
    assert model_init_result["status"] == "success", f"Model init failed: {model_init_result}"
    model_ref = model_init_result["outputs"]["model"]

    # Run eval
    # Note: diameter is a string in the schema
    mcp_result = await live_server.call_tool(
        "run",
        {
            "id": "cellpose.models.CellposeModel.eval",
            "inputs": {"model": model_ref, "x": img_ref},
            "params": {"diameter": str(diameter)},
        },
    )
    assert mcp_result.get("status") == "success", f"MCP run failed: {mcp_result}"
    mcp_output_ref = mcp_result["outputs"]["labels"]

    # 2. Run Native Baseline
    baseline_script = Path(__file__).parent / "reference_scripts" / "cellpose_baseline.py"
    native_output_path = tmp_path / "native_labels.ome.tiff"

    baseline_result = native_executor.run_script(
        env_name="bioimage-mcp-cellpose",
        script_path=baseline_script,
        args=[
            "--input",
            str(synthetic_cell_image),
            "--output",
            str(native_output_path),
            "--model_type",
            model_type,
            "--diameter",
            str(diameter),
        ],
    )
    assert baseline_result["status"] == "success", f"Baseline failed: {baseline_result}"

    # 3. Compare
    mcp_uri = mcp_output_ref["uri"]
    assert mcp_uri.startswith("file://")
    mcp_path = Path(mcp_uri.replace("file://", ""))

    # Load both and compare
    mcp_img = BioImage(mcp_path)
    native_img = BioImage(native_output_path)

    # Use IoU threshold 0.95 as requested to account for nondeterminism
    helper.assert_labels_equivalent(
        np.asarray(mcp_img.data), np.asarray(native_img.data), iou_threshold=0.95
    )
