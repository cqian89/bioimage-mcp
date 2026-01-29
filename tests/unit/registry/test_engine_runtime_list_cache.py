from __future__ import annotations

import unittest.mock as mock

import pytest

from bioimage_mcp.registry.engine import DiscoveryEngine
from bioimage_mcp.registry.manifest_schema import ToolManifest


@pytest.fixture
def mock_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    # Mock Path.home() for both engine.py and tests
    with mock.patch("pathlib.Path.home", return_value=home):
        yield home


@pytest.fixture
def project_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "envs").mkdir()
    return root


@pytest.fixture
def manifest(project_root):
    manifest_path = project_root / "manifest.yaml"
    manifest_path.write_text("tool_id: test.tool\nenv_id: bioimage-mcp-test")
    return ToolManifest(
        manifest_version="0.1.0",
        tool_id="test.tool",
        tool_version="1.0.0",
        env_id="bioimage-mcp-test",
        entrypoint="entry.py",
        manifest_path=manifest_path,
        manifest_checksum="checksum-1",
    )


def test_runtime_list_cache_hit_miss(mock_home, project_root, manifest):
    # 1. Setup lockfile
    lockfile_path = project_root / "envs" / "bioimage-mcp-test.lock.yml"
    lockfile_path.write_text("lockfile-content-1")

    # 2. Mock execute_tool for the first call (cache miss)
    runtime_response = {
        "ok": True,
        "result": {
            "functions": [
                {
                    "id": "test.func1",
                    "name": "func1",
                    "summary": "Summary 1",
                    "module": "mod1",
                }
            ]
        },
    }

    engine = DiscoveryEngine(project_root=project_root)

    with mock.patch("bioimage_mcp.registry.engine.execute_tool") as mock_execute:
        mock_execute.return_value = (runtime_response, "", 0)

        # First call: cache miss
        results1 = engine._runtime_list(manifest)
        assert len(results1) == 1
        assert results1[0]["id"] == "test.func1"
        assert mock_execute.call_count == 1

        # Verify cache file exists
        cache_file = (
            mock_home / ".bioimage-mcp" / "cache" / "dynamic" / "test.tool" / "meta_list_cache.json"
        )
        assert cache_file.exists()

        # Second call: cache hit
        # Reset mock to ensure it's not called
        mock_execute.reset_mock()

        results2 = engine._runtime_list(manifest)
        assert results2 == results1
        mock_execute.assert_not_called()

        # Test across instances
        engine2 = DiscoveryEngine(project_root=project_root)
        results3 = engine2._runtime_list(manifest)
        assert results3 == results1
        mock_execute.assert_not_called()


def test_runtime_list_cache_invalidation_lockfile(mock_home, project_root, manifest):
    lockfile_path = project_root / "envs" / "bioimage-mcp-test.lock.yml"
    lockfile_path.write_text("lockfile-content-1")

    runtime_response = {
        "ok": True,
        "result": {"functions": [{"id": "f1", "name": "n1", "summary": "s1"}]},
    }

    engine = DiscoveryEngine(project_root=project_root)

    with mock.patch("bioimage_mcp.registry.engine.execute_tool") as mock_execute:
        mock_execute.return_value = (runtime_response, "", 0)

        # Initial call
        engine._runtime_list(manifest)
        assert mock_execute.call_count == 1

        # Change lockfile
        lockfile_path.write_text("lockfile-content-2")
        mock_execute.reset_mock()

        # Should miss cache and call execute_tool again
        engine._runtime_list(manifest)
        assert mock_execute.call_count == 1


def test_runtime_list_cache_invalidation_manifest(mock_home, project_root, manifest):
    lockfile_path = project_root / "envs" / "bioimage-mcp-test.lock.yml"
    lockfile_path.write_text("lockfile-content-1")

    runtime_response = {
        "ok": True,
        "result": {"functions": [{"id": "f1", "name": "n1", "summary": "s1"}]},
    }

    engine = DiscoveryEngine(project_root=project_root)

    with mock.patch("bioimage_mcp.registry.engine.execute_tool") as mock_execute:
        mock_execute.return_value = (runtime_response, "", 0)

        # Initial call
        engine._runtime_list(manifest)
        assert mock_execute.call_count == 1

        # Change manifest checksum
        manifest.manifest_checksum = "checksum-2"
        mock_execute.reset_mock()

        # Should miss cache and call execute_tool again
        engine._runtime_list(manifest)
        assert mock_execute.call_count == 1


def test_runtime_list_no_cache_no_lockfile(mock_home, project_root, manifest):
    # No lockfile created

    runtime_response = {
        "ok": True,
        "result": {"functions": [{"id": "f1", "name": "n1", "summary": "s1"}]},
    }

    engine = DiscoveryEngine(project_root=project_root)

    with mock.patch("bioimage_mcp.registry.engine.execute_tool") as mock_execute:
        mock_execute.return_value = (runtime_response, "", 0)

        # First call
        engine._runtime_list(manifest)
        assert mock_execute.call_count == 1

        # Second call: still miss because no lockfile
        mock_execute.reset_mock()
        engine._runtime_list(manifest)
        assert mock_execute.call_count == 1
