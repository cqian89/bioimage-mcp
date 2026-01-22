from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioimage_mcp.bootstrap.remove import remove_tool


@pytest.fixture
def mock_env_manager():
    with patch("bioimage_mcp.bootstrap.remove.detect_env_manager") as mock:
        mock.return_value = ("micromamba", "/path/to/micromamba", "1.0.0")
        yield mock


@pytest.fixture
def mock_run():
    with patch("subprocess.run") as mock:
        yield mock


@pytest.fixture
def mock_active():
    with patch("bioimage_mcp.bootstrap.remove.is_tool_active") as mock:
        mock.return_value = False
        yield mock


def test_remove_base_blocked():
    assert remove_tool("base") == 1


def test_remove_no_manager():
    with patch("bioimage_mcp.bootstrap.remove.detect_env_manager", return_value=None):
        assert remove_tool("cellpose") == 1


def test_remove_non_existent_tool(mock_env_manager, mock_run):
    # Mock env list output to not contain the tool
    mock_run.return_value = MagicMock(returncode=0, stdout='{"envs": []}')
    assert remove_tool("nonexistent") == 1


def test_remove_active_tool_blocked(mock_env_manager, mock_run, mock_active):
    mock_active.return_value = True
    mock_run.return_value = MagicMock(
        returncode=0, stdout='{"envs": ["/path/to/bioimage-mcp-cellpose"]}'
    )
    assert remove_tool("cellpose") == 1


def test_remove_cancel_confirmation(mock_env_manager, mock_run, mock_active):
    mock_run.return_value = MagicMock(
        returncode=0, stdout='{"envs": ["/path/to/bioimage-mcp-cellpose"]}'
    )
    with patch("builtins.input", return_value="n"):
        assert remove_tool("cellpose") == 0
        # Should not have called remove command
        # Verify no call with "remove"
        for call in mock_run.call_args_list:
            assert "remove" not in call.args[0]


def test_remove_success_with_confirmation(mock_env_manager, mock_run, mock_active):
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout='{"envs": ["/path/to/bioimage-mcp-cellpose"]}'),  # list
        MagicMock(returncode=0),  # remove
    ]
    with patch("builtins.input", return_value="y"):
        assert remove_tool("cellpose") == 0
        # Check remove command called
        mock_run.assert_any_call(
            ["/path/to/micromamba", "env", "remove", "-n", "bioimage-mcp-cellpose", "-y"],
            check=False,
        )


def test_remove_success_with_yes_flag(mock_env_manager, mock_run, mock_active):
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout='{"envs": ["/path/to/bioimage-mcp-cellpose"]}'),  # list
        MagicMock(returncode=0),  # remove
    ]
    assert remove_tool("cellpose", yes=True) == 0
    # Check remove command called
    mock_run.assert_any_call(
        ["/path/to/micromamba", "env", "remove", "-n", "bioimage-mcp-cellpose", "-y"], check=False
    )


def test_remove_failure(mock_env_manager, mock_run, mock_active):
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout='{"envs": ["/path/to/bioimage-mcp-cellpose"]}'),  # list
        MagicMock(returncode=1),  # remove failed
    ]
    assert remove_tool("cellpose", yes=True) == 1
