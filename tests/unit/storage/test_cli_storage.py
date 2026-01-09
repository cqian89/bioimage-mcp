from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch
import pytest
from bioimage_mcp.cli import _handle_storage_status, _handle_storage_prune
from bioimage_mcp.storage.models import StorageStatus, SessionStorageInfo, PruneResult


@pytest.fixture
def mock_storage_service():
    with patch("bioimage_mcp.storage.service.StorageService") as mock:
        yield mock


@pytest.fixture
def mock_load_config():
    with patch("bioimage_mcp.config.loader.load_config") as mock:
        config = MagicMock()
        config.storage.warning_threshold = 0.8
        config.storage.critical_threshold = 0.9
        mock.return_value = config
        yield config


@pytest.fixture
def mock_connect():
    with patch("bioimage_mcp.storage.sqlite.connect") as mock:
        yield mock


def test_storage_status_exit_codes_T086(mock_storage_service, mock_load_config, mock_connect):
    """T086: Verify correct exit codes for storage status"""
    service_instance = mock_storage_service.return_value

    # Test Normal (0)
    service_instance.get_status.return_value = StorageStatus(
        total_bytes=1000, used_bytes=500, usage_percent=50.0, by_state={}, orphan_bytes=0
    )
    args = argparse.Namespace(json=False, verbose=False)
    assert _handle_storage_status(args) == 0

    # Test Warning (1)
    service_instance.get_status.return_value = StorageStatus(
        total_bytes=1000, used_bytes=850, usage_percent=85.0, by_state={}, orphan_bytes=0
    )
    assert _handle_storage_status(args) == 1

    # Test Critical (2)
    service_instance.get_status.return_value = StorageStatus(
        total_bytes=1000, used_bytes=950, usage_percent=95.0, by_state={}, orphan_bytes=0
    )
    assert _handle_storage_status(args) == 2


def test_storage_prune_exit_codes_T086(mock_storage_service, mock_load_config, mock_connect):
    """T086: Verify correct exit codes for storage prune"""
    service_instance = mock_storage_service.return_value

    # Test Success (0)
    service_instance.prune.return_value = PruneResult(
        sessions_deleted=1,
        artifacts_deleted=1,
        bytes_reclaimed=100,
        orphan_files_deleted=0,
        errors=[],
    )
    args = argparse.Namespace(
        dry_run=False, include_orphans=True, days=None, force=True, json=False
    )
    assert _handle_storage_prune(args) == 0

    # Test Partial Failure (1)
    service_instance.prune.return_value = PruneResult(
        sessions_deleted=0,
        artifacts_deleted=0,
        bytes_reclaimed=0,
        orphan_files_deleted=0,
        errors=["Some error"],
    )
    assert _handle_storage_prune(args) == 1


def test_storage_pin_exit_codes_T086(mock_storage_service, mock_load_config, mock_connect):
    """T086: Verify correct exit codes for storage pin"""
    from bioimage_mcp.cli import _handle_storage_pin

    service_instance = mock_storage_service.return_value

    # Test Success (0)
    service_instance.pin_session.return_value = MagicMock(session_id="s1")
    service_instance.get_session_size.return_value = 1024 * 1024 * 1024
    service_instance.conn.execute.return_value.fetchone.return_value = [5]
    args = argparse.Namespace(session_id="s1", unpin=False)
    assert _handle_storage_pin(args) == 0

    # Test Not Found (1)
    service_instance.pin_session.side_effect = KeyError("Not found")
    assert _handle_storage_pin(args) == 1


def test_storage_list_exit_codes_T086(mock_storage_service, mock_load_config, mock_connect):
    """T086: Verify correct exit codes for storage list"""
    from bioimage_mcp.cli import _handle_storage_list

    service_instance = mock_storage_service.return_value

    # Test Success (0)
    service_instance.list_sessions.return_value = []
    args = argparse.Namespace(state=None, limit=10, sort="age", json=False)
    assert _handle_storage_list(args) == 0
