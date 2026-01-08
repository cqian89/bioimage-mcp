"""Unit tests for Cellpose parameter coercion utilities."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def utils_module():
    """Load the utils module with mocked cellpose dependencies."""
    # We need to mock cellpose since the entrypoint imports it
    mock_cellpose = MagicMock()
    mock_cellpose.__version__ = "3.1.0"

    with patch.dict(sys.modules, {"cellpose": mock_cellpose}):
        # Import directly from the ops/utils module
        ops_path = (
            Path(__file__).resolve().parents[3]
            / "tools"
            / "cellpose"
            / "bioimage_mcp_cellpose"
            / "ops"
        )
        sys.path.insert(0, str(ops_path.parent.parent))
        try:
            from bioimage_mcp_cellpose.ops.utils import _coerce_param, _uri_to_path

            yield _coerce_param, _uri_to_path
        finally:
            sys.path.pop(0)


class TestCoerceParam:
    """Tests for _coerce_param function."""

    def test_coerce_string_to_float(self, utils_module):
        """Test coercing string '180' to float 180.0."""
        _coerce_param, _ = utils_module
        result = _coerce_param("180", float, "diameter")
        assert result == 180.0
        assert isinstance(result, float)

    def test_coerce_string_to_int(self, utils_module):
        """Test coercing string '10' to int 10."""
        _coerce_param, _ = utils_module
        result = _coerce_param("10", int, "n_epochs")
        assert result == 10
        assert isinstance(result, int)

    def test_coerce_string_true_to_bool(self, utils_module):
        """Test coercing string 'true' to bool True."""
        _coerce_param, _ = utils_module
        assert _coerce_param("true", bool, "gpu") is True
        assert _coerce_param("True", bool, "gpu") is True
        assert _coerce_param("TRUE", bool, "gpu") is True
        assert _coerce_param("1", bool, "gpu") is True
        assert _coerce_param("yes", bool, "gpu") is True

    def test_coerce_string_false_to_bool(self, utils_module):
        """Test coercing string 'false' to bool False."""
        _coerce_param, _ = utils_module
        assert _coerce_param("false", bool, "gpu") is False
        assert _coerce_param("0", bool, "gpu") is False
        assert _coerce_param("no", bool, "gpu") is False

    def test_none_passthrough(self, utils_module):
        """Test that None values pass through unchanged."""
        _coerce_param, _ = utils_module
        assert _coerce_param(None, float, "diameter") is None
        assert _coerce_param(None, int, "n_epochs") is None
        assert _coerce_param(None, bool, "gpu") is None

    def test_correct_type_passthrough(self, utils_module):
        """Test that values of correct type pass through unchanged."""
        _coerce_param, _ = utils_module
        assert _coerce_param(180.0, float, "diameter") == 180.0
        assert _coerce_param(10, int, "n_epochs") == 10
        assert _coerce_param(True, bool, "gpu") is True

    def test_invalid_string_raises_valueerror(self, utils_module):
        """Test that invalid string raises ValueError with helpful message."""
        _coerce_param, _ = utils_module
        with pytest.raises(ValueError) as exc_info:
            _coerce_param("not_a_number", float, "diameter")

        assert "diameter" in str(exc_info.value)
        assert "float" in str(exc_info.value)
        assert "not_a_number" in str(exc_info.value)


class TestUriToPath:
    """Tests for _uri_to_path function."""

    def test_file_uri_linux(self, utils_module):
        """Test converting Linux file URI to Path."""
        _, _uri_to_path = utils_module
        result = _uri_to_path("file:///home/user/image.tiff")
        assert result == Path("/home/user/image.tiff")

    def test_file_uri_windows(self, utils_module):
        """Test converting Windows file URI to Path."""
        _, _uri_to_path = utils_module
        result = _uri_to_path("file:///C:/Users/test/image.tiff")
        # On non-Windows, this still works (path starts with C:/)
        assert "image.tiff" in str(result)

    def test_plain_path_passthrough(self, utils_module):
        """Test that plain paths pass through as Paths."""
        _, _uri_to_path = utils_module
        result = _uri_to_path("/home/user/image.tiff")
        assert result == Path("/home/user/image.tiff")

    def test_url_encoded_spaces(self, utils_module):
        """Test that URL-encoded spaces are properly decoded."""
        _, _uri_to_path = utils_module
        result = _uri_to_path("file:///home/user/my%20image.tiff")
        assert result == Path("/home/user/my image.tiff")
