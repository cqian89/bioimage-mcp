import pytest
import numpy as np
import tifffile
from pathlib import Path
from bioimage_mcp.registry.dynamic.adapters.skimage import SkimageAdapter


def test_skimage_adapter_preserves_2d_output(tmp_path):
    """T015: SkimageAdapter preserves native dimension output (2D)."""
    adapter = SkimageAdapter()

    # Create a 2D image
    img_path = tmp_path / "input_2d.tiff"
    data = np.zeros((100, 100), dtype=np.uint8)
    tifffile.imwrite(str(img_path), data)

    artifact = {
        "uri": f"file://{img_path}",
        "format": "TIFF",
        "type": "BioImageRef",
        "metadata": {"axes": "YX", "shape": [100, 100]},
    }

    # When SkimageAdapter executes gaussian
    results = adapter.execute(
        fn_id="skimage.filters.gaussian",
        inputs=[artifact],
        params={"sigma": 1.0},
        work_dir=tmp_path,
    )

    # Then output is 2D, not expanded to 5D
    # CURRENT BEHAVIOR: SkimageAdapter might try to infer axes or use input axes.
    # But because it uses BioImage._load_image which returns 5D, it will likely return 5D.
    out_artifact = results[0]
    assert out_artifact["metadata"]["axes"] == "YX"
    assert out_artifact["metadata"]["shape"] == [100, 100]
