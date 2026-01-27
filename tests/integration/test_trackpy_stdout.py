import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.parametrize("fn_id", ["trackpy.locate", "trackpy.batch"])
def test_stdout_purity_and_capture(fn_id):
    """Verify that trackpy execution doesn't leak to stdout and logs are captured."""
    # Path to entrypoint
    entrypoint = Path("tools/trackpy/bioimage_mcp_trackpy/entrypoint.py").absolute()

    # Use the conda environment's python
    python_exe = "/home/qianchen/miniforge3/envs/bioimage-mcp-trackpy/bin/python"
    if not os.path.exists(python_exe):
        # Fallback to current python if env python not found (e.g. in CI)
        python_exe = sys.executable

    # Create a dummy image for locate (small 10x10)
    test_dir = Path("tests/data/tmp_stdout").absolute()
    test_dir.mkdir(parents=True, exist_ok=True)
    img_path = test_dir / "test_img.ome.tif"

    # Simple OME-TIFF write
    from bioio.writers import OmeTiffWriter

    img_data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint16)
    img_data[0, 0, 0, 5, 5] = 1000
    OmeTiffWriter.save(img_data, img_path, dim_order="TCZYX")

    request = {
        "command": "execute",
        "fn_id": fn_id,
        "params": {"diameter": 3},
        "inputs": {"image": {"type": "BioImageRef", "uri": f"file://{img_path}"}},
        "work_dir": str(test_dir),
    }

    # Run via subprocess to capture ACTUAL stdout
    proc = subprocess.run(
        [python_exe, str(entrypoint)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path("tools/trackpy").absolute())},
    )

    output_lines = [line for line in proc.stdout.strip().split("\n") if line.strip()]

    # Assert every line is valid JSON
    for line in output_lines:
        try:
            json.loads(line)
        except json.JSONDecodeError:
            pytest.fail(f"Non-JSON output detected in stdout for {fn_id}: {line!r}")

    # The last line should be the execute_result
    result = json.loads(output_lines[-1])
    assert result.get("ok") is True, f"Execution of {fn_id} failed: {result.get('error')}"
    assert "_meta" in result
    assert "log" in result["_meta"]
