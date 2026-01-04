from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
import numpy as np

# Add tools/base to sys.path so we can import bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

# These imports are expected to fail in the TDD RED phase
try:
    from bioimage_mcp_base.ops.io import (
        file_not_found_error,
        inspect,
        load,
        path_not_allowed_error,
        unsupported_format_error,
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


def test_load_invalid_path(tmp_path):
    """T010: Load function raises FileNotFoundError for missing file."""
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


def test_inspect_returns_metadata(tmp_path):
    """T011: Inspect returns shape, dims, dtype, physical_pixel_sizes."""
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


def test_inspect_preserves_native_axes(tmp_path):
    """T059: Inspect returns native axes, not forced TCZYX."""
    img_path = str(tmp_path / "zyx_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((10, 64, 64), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="ZYX")

    result = inspect(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    meta = result["outputs"]["metadata"]
    assert meta["dims"] == "ZYX"
    assert meta["shape"] == [10, 64, 64]


def test_inspect_accepts_bioimage_ref(tmp_path):
    """T058: Inspect can take BioImageRef input instead of path."""
    img_path = str(tmp_path / "ref_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    image_ref = {"type": "BioImageRef", "uri": f"file://{img_path}"}
    result = inspect(inputs={"image": image_ref}, params={}, work_dir=tmp_path)
    assert result["outputs"]["metadata"]["dims"] == "TCZYX"


def test_inspect_does_not_load_pixels(tmp_path):
    """T060: Inspect is metadata-only, should be fast."""
    img_path = str(tmp_path / "perf_test.ome.tif")
    from bioio.writers import OmeTiffWriter

    data = np.zeros((1, 1, 1, 10, 10), dtype="uint8")
    OmeTiffWriter.save(data, img_path, dim_order="TCZYX")

    import time

    start = time.time()
    inspect(inputs={}, params={"path": img_path}, work_dir=tmp_path)
    end = time.time()
    assert end - start < 1.0


def test_inspect_returns_channel_names(tmp_path):
    """T061: Inspect returns channel_names when available."""
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
