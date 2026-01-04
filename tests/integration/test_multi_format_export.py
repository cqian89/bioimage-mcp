from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import tifffile
from bioio import BioImage
from PIL import Image

# Add base tool to path for direct testing of export op
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "tools" / "base"))

from bioimage_mcp_base.ops.io import export as tool_export  # noqa: E402

from bioimage_mcp.artifacts.export import export_artifact  # noqa: E402
from bioimage_mcp.artifacts.store import ArtifactStore  # noqa: E402
from bioimage_mcp.config.schema import Config  # noqa: E402
from bioimage_mcp.errors import ArtifactStoreError  # noqa: E402


@pytest.mark.integration
def test_multi_format_export(tmp_path):
    """T033: export 2D to PNG, 5D to OME-TIFF, table to CSV."""
    # Setup store
    store_root = tmp_path / "store"
    store_root.mkdir()

    config = Config(
        artifact_store_root=store_root,
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
    )
    store = ArtifactStore(config)
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # 1. Export 2D -> PNG
    data_2d = np.zeros((64, 64), dtype=np.uint8)
    img_2d_path = tmp_path / "2d.tiff"
    tifffile.imwrite(img_2d_path, data_2d)
    ref_2d = store.import_file(img_2d_path, artifact_type="BioImageRef", format="TIFF")

    dest_png = tmp_path / "exported.png"

    # Confirm core REJECTS direct conversion now
    with pytest.raises(ArtifactStoreError, match="Format conversion not supported in core"):
        export_artifact(store, ref_id=ref_2d.ref_id, dest_path=dest_png, format="PNG")

    # Use base tool to perform conversion
    res = tool_export(
        inputs={"image": ref_2d.model_dump()},
        params={"format": "PNG"},
        work_dir=work_dir,
    )
    converted_path = Path(res["outputs"]["output"]["path"])
    ref_png = store.import_file(converted_path, artifact_type="BioImageRef", format="PNG")

    # Now core export works (simple copy)
    export_artifact(store, ref_id=ref_png.ref_id, dest_path=dest_png)

    assert dest_png.exists()
    assert dest_png.suffix == ".png"
    with Image.open(dest_png) as img:
        assert img.format == "PNG"
        assert img.size == (64, 64)

    # 2. Export 5D -> OME-TIFF
    data_5d = np.zeros((1, 1, 1, 64, 64), dtype=np.float32)
    img_5d_path = tmp_path / "5d.ome.tiff"
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(data_5d, str(img_5d_path), dim_order="TCZYX")
    ref_5d = store.import_file(img_5d_path, artifact_type="BioImageRef", format="OME-TIFF")

    dest_ome = tmp_path / "exported.ome.tiff"
    # This works without conversion because formats match (OME-TIFF -> OME-TIFF)
    export_artifact(store, ref_id=ref_5d.ref_id, dest_path=dest_ome)

    assert dest_ome.exists()
    assert ".ome.tiff" in dest_ome.name
    img = BioImage(str(dest_ome))
    assert img.dims.shape == (1, 1, 1, 64, 64)

    # 3. Export Table -> CSV
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    csv_path = tmp_path / "table.csv"
    df.to_csv(csv_path, index=False)
    ref_table = store.import_file(csv_path, artifact_type="TableRef", format="CSV")

    dest_csv = tmp_path / "exported.csv"
    # This works without conversion because formats match (CSV -> CSV)
    export_artifact(store, ref_id=ref_table.ref_id, dest_path=dest_csv)

    assert dest_csv.exists()
    df_out = pd.read_csv(dest_csv)
    assert df_out.shape == (2, 2)
