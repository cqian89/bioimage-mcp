import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from bioimage_mcp.api.execution import execute_step
from bioimage_mcp.config.schema import Config, MicrosamDevice
from bioimage_mcp.registry import loader


@pytest.fixture(autouse=True)
def clear_manifest_cache():
    loader._MANIFEST_CACHE.clear()


@pytest.fixture
def microsam_manifest(tmp_path):
    manifest_dir = tmp_path / "tools" / "microsam"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "manifest.yaml"

    content = {
        "manifest_version": "0.1",
        "tool_id": "tools.micro_sam",
        "tool_version": "0.1.0",
        "env_id": "bioimage-mcp-microsam",
        "entrypoint": "entrypoint.py",
        "functions": [
            {
                "fn_id": "meta.describe",
                "tool_id": "tools.micro_sam",
                "name": "describe",
                "description": "Describe tools",
                "params_schema": {"type": "object", "properties": {}},
            }
        ],
    }

    with open(manifest_path, "w") as f:
        yaml.dump(content, f)

    (manifest_dir / "entrypoint.py").touch()

    return manifest_dir.parent


def test_microsam_tool_config_wiring(microsam_manifest, tmp_path):
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[microsam_manifest],
        microsam={"device": MicrosamDevice.CUDA},
    )

    # Verify manifest is loaded
    manifests, diagnostics = loader.load_manifests(config.tool_manifest_roots)
    assert len(manifests) == 1
    assert manifests[0].tool_id == "tools.micro_sam"

    captured_request = {}

    def mock_execute_tool(entrypoint, request, env_id, timeout_seconds):
        nonlocal captured_request
        captured_request = request
        return {"ok": True}, "log", 0

    with patch("bioimage_mcp.api.execution.execute_tool", side_effect=mock_execute_tool):
        execute_step(
            config=config,
            fn_id="meta.describe",
            params={},
            inputs={},
            work_dir=tmp_path / "work",
            timeout_seconds=60,
        )

    assert "tool_config" in captured_request
    assert captured_request["tool_config"]["microsam"]["device"] == "cuda"


def test_non_microsam_tool_config_no_wiring(tmp_path):
    manifest_dir = tmp_path / "tools" / "other"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "manifest.yaml"

    content = {
        "manifest_version": "0.1",
        "tool_id": "tools.other",
        "tool_version": "0.1.0",
        "env_id": "bioimage-mcp-other",
        "entrypoint": "entrypoint.py",
        "functions": [
            {
                "fn_id": "test",
                "tool_id": "tools.other",
                "name": "test",
                "description": "test",
                "params_schema": {"type": "object", "properties": {}},
            }
        ],
    }

    with open(manifest_path, "w") as f:
        yaml.dump(content, f)

    (manifest_dir / "entrypoint.py").touch()

    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()

    config = Config(
        artifact_store_root=artifact_root,
        tool_manifest_roots=[manifest_dir.parent],
    )

    captured_request = {}

    def mock_execute_tool(entrypoint, request, env_id, timeout_seconds):
        nonlocal captured_request
        captured_request = request
        return {"ok": True}, "log", 0

    with patch("bioimage_mcp.api.execution.execute_tool", side_effect=mock_execute_tool):
        execute_step(
            config=config,
            fn_id="test",
            params={},
            inputs={},
            work_dir=tmp_path / "work",
            timeout_seconds=60,
        )

    assert "tool_config" not in captured_request
