from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest
import tifffile

from tests.smoke.utils.data_equivalence import DataEquivalenceHelper
from tests.smoke.utils.native_executor import NativeExecutor


@pytest.mark.smoke_full
@pytest.mark.uses_minimal_data
@pytest.mark.requires_env("bioimage-mcp-base")
@pytest.mark.anyio
async def test_phasorpy_equivalence(live_server):
    """Test that MCP phasorpy.phasor.phasor_from_signal matches native execution.

    Note: This test is expected to fail initially as it uncovers integration
    complexities with bioio and dimension ordering.
    """
    helper = DataEquivalenceHelper()
    executor = NativeExecutor()
    env_name = "bioimage-mcp-base"

    # Use a directory that is in the server's allowlist for both read and write
    test_dir = Path.home() / ".bioimage-mcp" / "artifacts" / "test_tmp"
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Generate synthetic signal data (3D: phase, Y, X)
        phases = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        y, x = np.ogrid[:32, :32]
        phase_shift = (y + x) / 32.0 * np.pi
        signal_data = 100 + 50 * np.cos(phases[:, None, None] - phase_shift[None, :, :])
        signal_data = signal_data.astype(np.float32)

        input_path = test_dir / "input_signal.ome.tiff"
        from bioio.writers import OmeTiffWriter

        # Save as CYX (16, 32, 32)
        OmeTiffWriter.save(signal_data, str(input_path), dim_order="CYX")

        # 2. Run MCP Tool
        load_result = await live_server.call_tool(
            "run",
            {"fn_id": "base.io.bioimage.load", "inputs": {}, "params": {"path": str(input_path)}},
        )
        assert load_result.get("status") == "success", f"Load failed: {load_result}"
        image_artifact = load_result["outputs"]["image"]

        # Try to find the phase axis (size 16)
        # Note: RunResponseSerializer flattens dimension fields to top-level
        image_shape = image_artifact.get("shape", [])
        try:
            mcp_axis = image_shape.index(16)
        except ValueError:
            mcp_axis = 0

        run_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "base.phasorpy.phasor.phasor_from_signal",
                "inputs": {"signal": image_artifact},
                "params": {"axis": mcp_axis},
            },
        )
        assert run_result.get("status") == "success", f"Phasor failed: {run_result}"
        phasor_result = run_result["outputs"]

        # 3. Run Native Baseline
        baseline_script = (
            Path(__file__).parent / "reference_scripts" / "phasorpy_baseline.py"
        ).absolute()
        output_npy = test_dir / "baseline_output.npy"

        # tifffile.imread usually returns (16, 32, 32) for CYX
        native_data = tifffile.imread(input_path)
        try:
            native_axis = list(native_data.shape).index(16)
        except ValueError:
            native_axis = 0

        executor.run_script(
            env_name,
            baseline_script,
            ["--input", str(input_path), "--output", str(output_npy), "--axis", str(native_axis)],
        )

        # 4. Compare
        baseline_data = np.load(output_npy)
        expected_mean = baseline_data[0]
        expected_real = baseline_data[1]
        expected_imag = baseline_data[2]

        # Export MCP results to NPY
        mcp_mean_path = test_dir / "mcp_mean.npy"
        mcp_real_path = test_dir / "mcp_real.npy"
        mcp_imag_path = test_dir / "mcp_imag.npy"

        for name, path in [
            ("mean", mcp_mean_path),
            ("real", mcp_real_path),
            ("imag", mcp_imag_path),
        ]:
            res = await live_server.call_tool(
                "run",
                {
                    "fn_id": "base.io.bioimage.export",
                    "inputs": {"image": phasor_result[name]},
                    "params": {"format": "NPY", "path": str(path)},
                },
            )
            assert res.get("status") == "success", f"Export {name} failed: {res}"

        actual_mean = np.load(mcp_mean_path)
        actual_real = np.load(mcp_real_path)
        actual_imag = np.load(mcp_imag_path)

        helper.assert_arrays_equivalent(actual_mean, expected_mean, err_msg="Mean mismatch")
        helper.assert_arrays_equivalent(actual_real, expected_real, err_msg="Real mismatch")
        helper.assert_arrays_equivalent(actual_imag, expected_imag, err_msg="Imag mismatch")

    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)
