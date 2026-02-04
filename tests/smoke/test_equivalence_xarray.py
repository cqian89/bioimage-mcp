from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor


@pytest.fixture
def helper():
    return DataEquivalenceHelper()


@pytest.fixture
def executor():
    return NativeExecutor()


@pytest.mark.smoke_pr
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
class TestXarrayEquivalence:
    @pytest.mark.anyio
    async def test_xarray_mean_equivalence(self, live_server, helper, executor, tmp_path):
        """Test that MCP xarray.mean matches native xarray execution."""

        # 1. Run native baseline
        baseline_script = Path(__file__).parent / "reference_scripts" / "xarray_baseline.py"
        native_result = executor.run_script("bioimage-mcp-base", baseline_script, [])
        expected_mean = native_result["mean"]

        # 2. Prepare same synthetic data for MCP
        # We must use the same seed as the baseline script
        np.random.seed(42)
        data = np.random.rand(10, 10).astype(np.float32)

        # Use a path in the allowed datasets directory
        img_path = Path("datasets/synthetic/test_xarray.tif")
        img_path.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(img_path, data, ome=True)

        try:
            image_ref = {
                "type": "BioImageRef",
                "uri": f"file://{img_path.absolute()}",
                "format": "OME-TIFF",
            }

            # 3. Run MCP tool sequence
            # Step A: Instantiate DataArray
            da_result = await live_server.call_tool(
                "run",
                {
                    "id": "base.xarray.DataArray",
                    "inputs": {"image": image_ref},
                },
            )
            assert da_result.get("status") == "success", (
                f"DataArray instantiation failed: {da_result}"
            )
            da_ref = da_result["outputs"]["output"]
            # Verify initial dims are preserved (BioIO normalizes to uppercase, might expand to 5D)
            da_meta = da_ref.get("metadata") or da_ref
            mcp_dims = [d.upper() for d in da_meta["dims"]]
            assert "Y" in mcp_dims and "X" in mcp_dims

            # Step B: Compute mean (returns ObjectRef)
            mean_result = await live_server.call_tool(
                "run",
                {
                    "id": "base.xarray.DataArray.mean",
                    "inputs": {"image": da_ref},
                },
            )
            assert mean_result.get("status") == "success", f"Mean computation failed: {mean_result}"
            mean_obj_ref = mean_result["outputs"]["output"]
            # Verify dims are preserved after reduction (scalar has empty dims)
            mean_meta = mean_obj_ref.get("metadata") or mean_obj_ref
            mcp_mean_dims = mean_meta.get("dims", [])
            assert mcp_mean_dims == native_result["dims"]

            # Step C: Materialize to BioImageRef
            materialize_result = await live_server.call_tool(
                "run",
                {
                    "id": "base.xarray.DataArray.to_bioimage",
                    "inputs": {"image": mean_obj_ref},
                },
            )
            assert materialize_result.get("status") == "success", (
                f"Materialization failed: {materialize_result}"
            )
            output_ref = materialize_result["outputs"]["output"]

            # 4. Get result from MCP output
            uri = output_ref["uri"]
            assert uri.startswith("file://")
            output_path = Path(uri[7:])

            # Read back the image (use BioImage to support OME-Zarr directories)
            from bioio import BioImage

            img = BioImage(output_path)
            mcp_data = img.reader.data
            mcp_mean = float(mcp_data.mean())

            # 5. Compare
            helper.assert_arrays_equivalent(
                np.array([mcp_mean]), np.array([expected_mean]), rtol=1e-5
            )

            # Check that final metadata is sensible (expanded to 2D for TIFF)
            out_meta = output_ref.get("metadata") or output_ref
            assert "Y" in [d.upper() for d in out_meta["dims"]]
            assert "X" in [d.upper() for d in out_meta["dims"]]
        finally:
            if img_path.exists():
                img_path.unlink()
