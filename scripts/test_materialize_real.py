import tempfile
from pathlib import Path

import numpy as np
import tifffile

from bioimage_mcp.api.execution import _materialize_zarr_to_file
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_materialize_real():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        store_root = tmp_path / "store"
        store_root.mkdir()

        # Create a dummy Zarr-like directory artifact (simulating zarr-temp)
        # Since we don't have full OME-Zarr writer easily available without huge deps,
        # we'll create a TIFF file and pretend it's a zarr-temp by setting storage_type manually
        # effectively testing the read path of bioio which supports tiff too.
        # Wait, _materialize_zarr_to_file uses bioio.BioImage(path).
        # So if I point it to a TIFF, it will read it.
        # If I point it to a directory, it expects OME-Zarr.

        # Let's create a simple TIFF file first to verify bioio works
        data = np.zeros((1, 1, 1, 10, 10), dtype=np.uint8)
        src_path = tmp_path / "test.ome.tiff"
        tifffile.imwrite(str(src_path), data)

        config = Config(
            artifact_store_root=store_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        store = ArtifactStore(config)
        # Import as if it was a file first
        ref = store.import_file(src_path, artifact_type="BioImageRef", format="OME-TIFF")

        # Manually change storage_type to zarr-temp to trigger materialization logic
        # (even though it's actually a file, bioio handles both transparently usually)
        ref_dict = ref.model_dump()
        ref_dict["storage_type"] = "zarr-temp"

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        try:
            new_ref = _materialize_zarr_to_file(ref_dict, work_dir, store)
            print("Materialization successful")
            print(new_ref)
            assert new_ref["storage_type"] == "file"
            assert new_ref["format"] == "OME-TIFF"
            assert Path(new_ref["uri"].replace("file://", "")).exists()
        except Exception as e:
            print(f"Materialization failed: {e}")
            raise


if __name__ == "__main__":
    test_materialize_real()
