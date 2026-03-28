from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# Add tools/base to sys.path so we can import bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

# These imports are expected to fail in the TDD RED phase
try:
    from bioimage_mcp_base.ops.io import (
        SliceOutOfBoundsError,
        export,
        file_not_found_error,
        get_supported_formats,
        inspect,
        load,
        path_not_allowed_error,
        slice_image,
        unsupported_format_error,
        validate,
        validate_read_path,
        validate_write_path,
        validation_failed_error,
    )
except ImportError:
    # In RED phase, we don't have these yet.
    # We'll let the NameError happen in tests to indicate they are missing.
    pass

# T056: Path Validation Tests


def test_validate_read_path_allowed(monkeypatch):
    """Path within allowed_read should pass."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps(["/data", "/tmp"]))

    # In RED phase, this will raise NameError
    path = validate_read_path("/data/sample.tif")
    assert str(path) == "/data/sample.tif"


def test_validate_read_path_not_allowed(monkeypatch):
    """Path outside allowed_read should raise error."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps(["/data"]))

    with pytest.raises(Exception) as excinfo:
        validate_read_path("/secret/file.tif")
    assert "not in allowed read paths" in str(excinfo.value)


def test_validate_write_path_allowed(monkeypatch):
    """Write path within allowed_write should pass."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps(["/results"]))

    path = validate_write_path("/results/output.tif")
    assert str(path) == "/results/output.tif"


def test_validate_write_path_not_allowed(monkeypatch):
    """Write path outside allowed_write should raise."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps(["/results"]))

    with pytest.raises(Exception):
        validate_write_path("/etc/passwd")


# T057: Structured Error Response Tests


def test_path_not_allowed_error():
    """PATH_NOT_ALLOWED error has correct shape."""
    err = path_not_allowed_error("/secret/data.tif", ["/data", "/home/user"])
    assert err["error"]["code"] == "PATH_NOT_ALLOWED"
    assert "/secret/data.tif" in err["error"]["message"]
    assert err["error"]["details"]["allowed_paths"] == ["/data", "/home/user"]


def test_file_not_found_error():
    """FILE_NOT_FOUND error has correct shape."""
    err = file_not_found_error("/missing.tif")
    assert err["error"]["code"] == "FILE_NOT_FOUND"
    assert "/missing.tif" in err["error"]["message"]


def test_unsupported_format_error():
    """UNSUPPORTED_FORMAT error has correct shape."""
    err = unsupported_format_error("/data/image.xyz")
    assert err["error"]["code"] == "UNSUPPORTED_FORMAT"
    assert "xyz" in err["error"]["message"]


def test_validation_failed_error():
    """VALIDATION_FAILED error has correct shape."""
    err = validation_failed_error("/data/corrupt.tif", "Header is invalid")
    assert err["error"]["code"] == "VALIDATION_FAILED"
    assert "Header is invalid" in err["error"]["details"]["reason"]


# ============== Load Function Tests (T010, T008) ==============


def test_load_valid_path(monkeypatch, tmp_path):
    """T010: Load function returns BioImageRef for valid file."""
    # Mock allowed paths
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))

    # Create image in tmp_path
    from bioio.writers import OmeTiffWriter

    img_path = str(tmp_path / "test.ome.tif")
    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    result = load(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    assert "image" in result["outputs"]
    assert result["outputs"]["image"]["type"] == "BioImageRef"
    assert img_path in result["outputs"]["image"]["uri"]


def test_load_invalid_path(monkeypatch, tmp_path):
    """T010: Load function raises FileNotFoundIOError for missing file."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps(["/tmp"]))
    with pytest.raises(Exception) as excinfo:
        load(
            inputs={},
            params={"path": "/tmp/non_existent_image_12345.tif"},
            work_dir=tmp_path,
        )
    assert "not found" in str(excinfo.value).lower()


def test_load_path_not_allowed(monkeypatch, tmp_path):
    """T010: Load function raises PathNotAllowedError for path outside allowlist."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps(["/allowed"]))
    with pytest.raises(Exception) as excinfo:
        load(inputs={}, params={"path": "/forbidden/image.tif"}, work_dir=tmp_path)
    assert "not allowed" in str(excinfo.value).lower()


def test_load_schema_validation(tmp_path):
    """T008: Contract test for load function schema validation."""
    # Test with missing required parameter
    with pytest.raises(Exception):
        load(inputs={}, params={}, work_dir=tmp_path)
    # Test with invalid type
    with pytest.raises(Exception):
        load(inputs={}, params={"path": 123}, work_dir=tmp_path)


# ============== Inspect Function Tests (T011, T009, T058-T061) ==============


def test_inspect_returns_metadata(monkeypatch, tmp_path):
    """T011: Inspect returns shape, dims, dtype, physical_pixel_sizes."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "meta_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 5, 128, 128), dtype="uint16")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    result = inspect(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    meta = result["outputs"]["metadata"]
    assert meta["shape"] == [1, 1, 5, 128, 128]
    assert meta["dims"] == "TCZYX"
    assert meta["dtype"] == "uint16"
    assert "physical_pixel_sizes" in meta


def test_inspect_reports_tczyx_for_ome_tiff(monkeypatch, tmp_path):
    """T059: OME-TIFF always reports TCZYX per standard."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "3d_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((10, 64, 64), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="ZYX")

    result = inspect(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    meta = result["outputs"]["metadata"]
    assert meta["dims"] == "TCZYX"
    assert meta["shape"] == [1, 1, 10, 64, 64]


def test_inspect_accepts_bioimage_ref(monkeypatch, tmp_path):
    """T058: Inspect can take BioImageRef input instead of path."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "ref_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    result = inspect(inputs={"image": image_ref}, params={}, work_dir=tmp_path)
    assert result["outputs"]["metadata"]["dims"] == "TCZYX"


def test_inspect_does_not_load_pixels(monkeypatch, tmp_path):
    """T060: Inspect is metadata-only, should be fast."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "perf_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    import time

    start = time.time()
    inspect(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    end = time.time()
    assert end - start < 1.0


def test_inspect_returns_channel_names(monkeypatch, tmp_path):
    """T061: Inspect returns channel_names when available."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "chan_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 2, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    result = inspect(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    meta = result["outputs"]["metadata"]
    assert "channel_names" in meta
    assert isinstance(meta["channel_names"], list)


def test_inspect_schema_validation(tmp_path):
    """T009: Contract test for inspect function schema validation."""
    with pytest.raises(Exception):
        inspect(inputs={}, params={}, work_dir=tmp_path)
    with pytest.raises(Exception):
        inspect(inputs={}, params={"path": 123}, work_dir=tmp_path)


# ============== Export Function Tests (T016-T020, T062-T063) ==============


def test_export_to_ome_tiff(tmp_path, monkeypatch):
    """T017: Export BioImageRef to OME-TIFF format."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    # Create temp image to get a BioImageRef
    img_path = str(tmp_path / "source.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    out_path = str(tmp_path / "exported.ome.tif")

    result = export(
        inputs={"artifact": image_ref},
        params={"dest_path": out_path, "format": "OME-TIFF"},
        work_dir=tmp_path,
    )

    assert Path(out_path).exists()
    assert "output" in result["outputs"]


def test_export_to_png(tmp_path, monkeypatch):
    """T018: Export 2D image to PNG format."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    # Create 2D image
    img_path = str(tmp_path / "source2d.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="YX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    out_path = str(tmp_path / "exported.png")

    export(
        inputs={"artifact": image_ref},
        params={"dest_path": out_path, "format": "PNG"},
        work_dir=tmp_path,
    )

    assert Path(out_path).exists()
    # Basic PNG header check
    with open(out_path, "rb") as f:
        header = f.read(8)
    assert header == b"\x89PNG\r\n\x1a\n"


def test_export_float_to_png(tmp_path, monkeypatch):
    """Exporting float images to PNG should auto-convert to PNG-compatible dtype."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    img_path = str(tmp_path / "source_float.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.random.rand(10, 10).astype(np.float32)
    OmeTiffWriter.save(data, img_path, dim_order="YX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    out_path = str(tmp_path / "exported_float.png")

    export(
        inputs={"artifact": image_ref},
        params={"dest_path": out_path, "format": "PNG"},
        work_dir=tmp_path,
    )

    assert Path(out_path).exists()
    with open(out_path, "rb") as f:
        header = f.read(8)
    assert header == b"\x89PNG\r\n\x1a\n"


def test_export_to_ome_zarr(tmp_path, monkeypatch):
    """T019: Export to OME-Zarr format."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    img_path = str(tmp_path / "source.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    out_path = str(tmp_path / "exported.ome.zarr")

    export(
        inputs={"artifact": image_ref},
        params={"dest_path": out_path, "format": "OME-Zarr"},
        work_dir=tmp_path,
    )

    assert Path(out_path).exists()
    assert (Path(out_path) / ".zgroup").exists()


def test_export_infers_format(tmp_path, monkeypatch):
    """T062: Export infers format when omitted."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    # 1. Infer from extension
    img_path = str(tmp_path / "src.ome.tif")
    from bioio.writers import OmeTiffWriter

    OmeTiffWriter.save(np.zeros((1, 1, 1, 5, 5), dtype="uint8"), img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}

    # Export to .png (should infer PNG)
    png_path = str(tmp_path / "auto.png")
    export(inputs={"artifact": image_ref}, params={"dest_path": png_path}, work_dir=tmp_path)
    assert Path(png_path).exists()


def test_export_ome_zarr_lazy(tmp_path, monkeypatch):
    """T063: OME-Zarr export is lazy/chunked (performance proxy)."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    # Create a large image
    img_path = str(tmp_path / "large.ome.tif")
    from bioio.writers import OmeTiffWriter

    # 50x50x50 is big enough to notice if it's not lazy, but keep it small for tests
    data = np.zeros((1, 1, 50, 50, 50), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    out_path = str(tmp_path / "lazy.ome.zarr")

    import time

    start = time.time()
    export(
        inputs={"artifact": image_ref},
        params={"dest_path": out_path, "format": "OME-Zarr"},
        work_dir=tmp_path,
    )
    duration = time.time() - start
    # Should be very fast because bioio-ome-zarr supports chunked writing
    # and we aren't doing complex processing.
    assert duration < 2.0


def test_export_write_path_validation(tmp_path, monkeypatch):
    """Export validates write path against allowlist."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps(["/allowed"]))

    image_ref = {"type": "BioImageRef", "uri": "file:///tmp/src.tif"}

    with pytest.raises(Exception) as excinfo:
        export(
            inputs={"artifact": image_ref},
            params={"dest_path": "/forbidden/out.tif"},
            work_dir=tmp_path,
        )
    assert "not allowed" in str(excinfo.value).lower()


def test_export_schema_validation(tmp_path):
    """T016: Contract test for export function schema validation."""
    # Missing required 'artifact' input
    with pytest.raises(Exception):
        export(inputs={}, params={"path": "out.tif"}, work_dir=tmp_path)

    # Missing required 'path' param
    with pytest.raises(Exception):
        export(
            inputs={"artifact": {"type": "BioImageRef", "uri": "file:///tmp/src.tif"}},
            params={},
            work_dir=tmp_path,
        )


def test_export_accepts_label_image_ref(tmp_path, monkeypatch):
    """Test that export accepts LabelImageRef and preserves the type."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_WRITE", json.dumps([str(tmp_path)]))

    # Create temp image
    img_path = str(tmp_path / "labels.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint32")  # Labels are often uint32
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    label_ref = {"type": "LabelImageRef", "uri": f"file://{img_path}"}
    out_path = str(tmp_path / "exported_labels.ome.tif")

    result = export(
        inputs={"image": label_ref},
        params={"dest_path": out_path, "format": "OME-TIFF"},
        work_dir=tmp_path,
    )

    assert Path(out_path).exists()
    assert result["outputs"]["output"]["type"] == "LabelImageRef"


# ============== Validate and Supported Formats Tests (T028-T032, T064) ==============


def test_get_supported_formats_returns_list(tmp_path):
    """T030: get_supported_formats returns known formats (TIFF, OME-TIFF)."""
    result = get_supported_formats(inputs={}, params={}, work_dir=tmp_path)
    formats = result["outputs"]["result"]["formats"]
    assert isinstance(formats, list)
    assert any("tif" in f.lower() for f in formats)
    assert any("png" in f.lower() for f in formats)


def test_get_supported_formats_schema_validation(tmp_path):
    """T028: Contract test for get_supported_formats schema validation."""
    # Should accept empty params
    result = get_supported_formats(inputs={}, params={}, work_dir=tmp_path)
    assert "outputs" in result


def test_validate_valid_file(monkeypatch, tmp_path):
    """T031: validate returns is_valid=True for valid file."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "valid.ome.tif")
    from bioio.writers import OmeTiffWriter
    from bioio_base.types import PhysicalPixelSizes

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(
        data,
        img_path,
        dim_order="TCZYX",
        physical_pixel_sizes=PhysicalPixelSizes(1.0, 1.0, 1.0),
    )

    result = validate(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    report = result["outputs"]["result"]
    assert report["is_valid"] is True
    assert report["reader_selected"] is not None
    assert report["issues"] == []


def test_validate_corrupt_file(monkeypatch, tmp_path):
    """T032: validate returns is_valid=False for corrupted/invalid file."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    corrupt_path = tmp_path / "corrupt.tif"
    with open(corrupt_path, "w") as f:
        f.write("not a tiff")

    result = validate(inputs={}, params={"path": str(corrupt_path)}, work_dir=tmp_path)
    report = result["outputs"]["result"]
    assert report["is_valid"] is False
    assert any(issue["severity"] == "error" for issue in report["issues"])


def test_validate_does_not_load_pixels(monkeypatch, tmp_path):
    """T064: validate default does not trigger full pixel load."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "perf_test.ome.tif")
    from bioio.writers import OmeTiffWriter
    from bioio_base.types import PhysicalPixelSizes

    # Large enough to notice if it's slow
    data = np.zeros((1, 1, 10, 256, 256), dtype="uint8")
    OmeTiffWriter.save(
        data,
        img_path,
        dim_order="TCZYX",
        physical_pixel_sizes=PhysicalPixelSizes(1.0, 1.0, 1.0),
    )

    import time

    start = time.time()
    validate(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    duration = time.time() - start
    assert duration < 1.0


def test_validate_schema_validation(tmp_path):
    """T029: Contract test for validate function schema validation."""
    with pytest.raises(Exception):
        validate(inputs={}, params={}, work_dir=tmp_path)


# ============== Slice Function Tests (T036-T041, T065) ==============


def test_slice_single_channel(monkeypatch, tmp_path):
    """T037: Slice single channel by index."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "multi_chan.ome.tif")
    from bioio.writers import OmeTiffWriter

    # 3 channels
    data = np.zeros((1, 3, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    params = {"slices": {"C": 1}}

    result = slice_image(inputs={"image": image_ref}, params=params, work_dir=tmp_path)
    out_ref = result["outputs"]["output"]

    # C is removed because it was indexed with an integer
    assert out_ref["dims"] == ["T", "Z", "Y", "X"]
    assert out_ref["metadata"]["shape"] == [1, 1, 10, 10]
    assert out_ref["metadata"]["source_ref_id"] is None  # Since we didn't provide one


def test_slice_timepoint_range(monkeypatch, tmp_path):
    """T038: Slice timepoints 0-5."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "timeseries.ome.tif")
    from bioio.writers import OmeTiffWriter

    # 10 timepoints
    data = np.zeros((10, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    params = {"slices": {"T": {"start": 0, "stop": 5}}}

    result = slice_image(inputs={"image": image_ref}, params=params, work_dir=tmp_path)
    out_ref = result["outputs"]["output"]

    assert out_ref["metadata"]["shape"] == [5, 1, 1, 10, 10]


def test_slice_z_range_with_step(monkeypatch, tmp_path):
    """T039: Slice Z with step."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "zstack.ome.tif")
    from bioio.writers import OmeTiffWriter

    # 20 Z slices
    data = np.zeros((1, 1, 20, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    params = {"slices": {"Z": {"start": 0, "stop": 20, "step": 2}}}

    result = slice_image(inputs={"image": image_ref}, params=params, work_dir=tmp_path)
    out_ref = result["outputs"]["output"]

    assert out_ref["metadata"]["shape"] == [1, 1, 10, 10, 10]


def test_slice_preserves_pixel_sizes(monkeypatch, tmp_path):
    """T040: Physical pixel sizes preserved."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "pixel_size_test.ome.tif")
    from bioio.writers import OmeTiffWriter
    from bioio_base.types import PhysicalPixelSizes

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(
        data,
        img_path,
        dim_order="TCZYX",
        physical_pixel_sizes=PhysicalPixelSizes(0.5, 0.1, 0.1),
    )

    image_ref = {
        "type": "BioImageRef",
        "uri": f"file://{img_path}",
        "physical_pixel_sizes": {"Z": 0.5, "Y": 0.1, "X": 0.1},
    }
    params = {"slices": {"Y": {"start": 0, "stop": 5}}}

    result = slice_image(inputs={"image": image_ref}, params=params, work_dir=tmp_path)
    out_ref = result["outputs"]["output"]

    assert out_ref["physical_pixel_sizes"]["Z"] == 0.5
    assert out_ref["physical_pixel_sizes"]["Y"] == 0.1
    assert out_ref["physical_pixel_sizes"]["X"] == 0.1


def test_slice_out_of_bounds(monkeypatch, tmp_path):
    """T041: Out of bounds raises error."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "small.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 5, 5), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}

    # Slice index 10 for dimension X (size 5)
    params = {"slices": {"X": 10}}

    with pytest.raises(SliceOutOfBoundsError) as excinfo:
        slice_image(inputs={"image": image_ref}, params=params, work_dir=tmp_path)

    assert excinfo.value.dim == "X"
    assert excinfo.value.index == 10
    assert excinfo.value.size == 5


def test_slice_ome_tiff_is_5d(monkeypatch, tmp_path):
    """T065: Slicing OME-TIFF preserves TCZYX structure."""
    monkeypatch.setenv("BIOIMAGE_MCP_FS_ALLOWLIST_READ", json.dumps([str(tmp_path)]))
    img_path = str(tmp_path / "3d_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    # ZYX image (saved as OME-TIFF)
    data = np.zeros((5, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="ZYX")

    image_ref = {
        "type": "BioImageRef",
        "uri": f"file://{img_path}",
        "dims": ["T", "C", "Z", "Y", "X"],
    }
    params = {"slices": {"Z": 2}}

    result = slice_image(inputs={"image": image_ref}, params=params, work_dir=tmp_path)
    out_ref = result["outputs"]["output"]

    # Resulting image should be TCYX (since Z was indexed)
    assert out_ref["dims"] == ["T", "C", "Y", "X"]
    assert out_ref["metadata"]["shape"] == [1, 1, 10, 10]


def test_slice_schema_validation(tmp_path):
    """T036: Contract test for slice function schema validation."""
    with pytest.raises(Exception):
        slice_image(inputs={}, params={}, work_dir=tmp_path)
    with pytest.raises(Exception):
        slice_image(
            inputs={"image": {"type": "BioImageRef", "uri": "file:///tmp/img.tif"}},
            params={},
            work_dir=tmp_path,
        )
