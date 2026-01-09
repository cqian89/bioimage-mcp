import sqlite3
import pytest
from bioimage_mcp.storage.service import StorageService
from bioimage_mcp.config.schema import Config
from pathlib import Path


def test_storage_service_init():
    root = Path("/tmp/mcp_test").absolute()
    config = Config(artifact_store_root=root, tool_manifest_roots=[root / "tools"])
    conn = sqlite3.connect(":memory:")
    service = StorageService(config, conn)
    assert service.config == config
    assert service.conn == conn
    assert service.root == root
