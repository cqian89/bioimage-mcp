"""Tests for install utility functions."""

from unittest.mock import MagicMock, patch

from bioimage_mcp.bootstrap.install import _env_exists


def test_env_exists_handles_mixed_stdout_success():
    """Verify _env_exists correctly identifies env despite warnings."""
    mixed_output = (
        'Warning: some conda warning\nWarning: another warning\n{"envs": ["/path/to/my-env"]}'
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mixed_output, stderr="")
        # Should ignore warnings, parse JSON, and return True if path matches
        assert _env_exists("conda", "my-env") is True


def test_env_exists_handles_mixed_stdout_not_found():
    """Verify _env_exists correctly returns False if path mismatch, despite warnings."""
    mixed_output = 'Warning: some conda warning\n{"envs": ["/other/path"]}'
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mixed_output, stderr="")
        assert _env_exists("conda", "my-env") is False


def test_env_exists_safe_fail_on_garbage():
    """Verify _env_exists fails safely on non-JSON output without raising uncaught exception."""
    garbage = "Just some text\nNo json here"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=garbage, stderr="")
        # Should return False and log error, not crash
        assert _env_exists("any-env", "conda") is False
