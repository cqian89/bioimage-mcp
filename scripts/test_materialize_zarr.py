import tempfile
from pathlib import Path

from bioimage_mcp.api.execution import _materialize_zarr_to_file
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config


def test_materialize_zarr_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        store_root = tmp_path / "store"
        store_root.mkdir()

        # Create a fake Zarr directory
        # valid Zarr has .zgroup
        zarr_path = tmp_path / "test.zarr"
        zarr_path.mkdir()
        (zarr_path / ".zgroup").write_text('{"zarr_format": 2}')
        (zarr_path / ".zattrs").write_text("{}")

        # We need a valid array to read. This is getting complicated to fake without zarr lib.
        # But maybe bioio will at least try to read it and fail with a different error
        # if it recognizes it as zarr.

        config = Config(
            artifact_store_root=store_root,
            tool_manifest_roots=[],
            fs_allowlist_read=[tmp_path],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        store = ArtifactStore(config)
        # Import directory
        ref = store.import_directory(zarr_path, artifact_type="BioImageRef", format="OME-Zarr")

        print(f"Imported URI: {ref.uri}")

        # storage_type should be zarr-temp because of _guess_storage_type_for_directory logic
        # which checks format="OME-Zarr"
        assert ref.storage_type == "zarr-temp"

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        try:
            # This will fail because the Zarr is empty/fake, but we want to see if bioio attempts
            # to read it or if it fails with "UnsupportedFileFormatError" immediately because
            # of the folder name.
            _materialize_zarr_to_file(ref.model_dump(), work_dir, store)
        except Exception as e:
            print(f"Caught expected exception: {type(e).__name__}: {e}")
            # If it's a zarr reading error, then it passed the format detection
            # If it's UnsupportedFileFormatError, it failed format detection


if __name__ == "__main__":
    test_materialize_zarr_dir()
