import pytest
import json
import sys
from pathlib import Path
from io import StringIO
import numpy as np
from bioio.writers import OmeTiffWriter

from bioimage_mcp.registry.dynamic.adapters import ADAPTER_REGISTRY


def test_xarray_adapter_registered():
    """Test that xarray adapter is registered in ADAPTER_REGISTRY."""
    assert "xarray" in ADAPTER_REGISTRY


def test_xarray_adapter_execution(tmp_path):
    """Test that xarray adapter can execute a simple isel."""
    if "xarray" not in ADAPTER_REGISTRY:
        pytest.skip("Xarray adapter not registered")

    adapter = ADAPTER_REGISTRY["xarray"]

    img_path = tmp_path / "test.ome.tiff"
    data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)  # TCZYX
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    input_artifact = {
        "type": "BioImageRef",
        "format": "OME-TIFF",
        "uri": img_path.as_uri(),
        "metadata": {"axes": "TCZYX"},
    }

    # Try isel to select a slice
    outputs = adapter.execute(
        fn_id="xarray.isel",
        inputs=[("image", input_artifact)],
        params={"X": slice(0, 5)},
        work_dir=tmp_path,
    )

    assert len(outputs) == 1
    assert outputs[0]["type"] == "BioImageRef"
    assert Path(outputs[0]["path"]).exists()
    assert outputs[0]["metadata"]["shape"][-1] == 5
    assert outputs[0]["metadata"]["axes"] == "TCZYX"


def test_bioio_export_works(tmp_path):
    """Test that base.bioio.export works (statically mapped)."""
    # Add tools/base to sys.path
    tools_base = Path(__file__).resolve().parents[3] / "tools" / "base"
    if str(tools_base) not in sys.path:
        sys.path.insert(0, str(tools_base))

    from bioimage_mcp_base.entrypoint import main

    img_path = tmp_path / "input.ome.tiff"
    data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)
    OmeTiffWriter.save(data, str(img_path), dim_order="TCZYX")

    request = {
        "fn_id": "base.bioio.export",
        "inputs": {
            "image": {"type": "BioImageRef", "format": "OME-TIFF", "uri": img_path.as_uri()}
        },
        "params": {"format": "OME-TIFF"},
        "work_dir": str(tmp_path),
    }

    # Mock stdin/stdout
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    sys.stdin = StringIO(json.dumps(request))
    sys.stdout = StringIO()

    try:
        main()
        response = json.loads(sys.stdout.getvalue())
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout

    assert response["ok"] is True
    assert "output" in response["outputs"]
    assert Path(response["outputs"]["output"]["path"]).exists()
