from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add tools/base to sys.path so we can import bioimage_mcp_base
BASE_TOOLS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "base"
if str(BASE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_TOOLS_ROOT))

# These imports are expected to fail in the TDD RED phase
try:
    from bioimage_mcp_base.ops.io import (
        file_not_found_error,
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
