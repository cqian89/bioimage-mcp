from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import _MANIFEST_CACHE, load_manifests
from bioimage_mcp.storage.sqlite import connect

sys.path.append(str(Path(__file__).parent))

from mcp_test_client import MCPTestClient, MockExecutor

MockFn = Callable[[Path, dict, dict], tuple[dict[str, Any], str, int]]


@pytest.fixture
def mcp_services(tmp_path: Path):
    artifacts_root = tmp_path / "artifacts"
    tools_root = Path(__file__).parent.parent.parent / "tools"

    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    conn = connect(config)
    _MANIFEST_CACHE.pop(
        tuple(sorted(str(root.resolve()) for root in config.tool_manifest_roots)), None
    )
    manifests, _diagnostics = load_manifests(config.tool_manifest_roots)

    discovery = DiscoveryService(conn)
    for manifest in manifests:
        discovery.upsert_tool(
            tool_id=manifest.tool_id,
            name=manifest.name,
            description=manifest.description,
            tool_version=manifest.tool_version,
            env_id=manifest.env_id,
            manifest_path=str(manifest.manifest_path),
            available=True,
            installed=True,
        )
        for fn in manifest.functions:
            discovery.upsert_function(
                fn_id=fn.fn_id,
                tool_id=fn.tool_id,
                name=fn.name,
                description=fn.description,
                tags=fn.tags,
                inputs=[p.model_dump() for p in fn.inputs],
                outputs=[p.model_dump() for p in fn.outputs],
                params_schema=fn.params_schema,
            )

    artifact_store = ArtifactStore(config, conn=conn)
    execution = ExecutionService(config, artifact_store=artifact_store)

    yield {
        "config": config,
        "discovery": discovery,
        "execution": execution,
        "artifact_store": artifact_store,
        "tmp_path": tmp_path,
    }

    discovery.close()
    execution.close()
    artifact_store.close()


def test_mock_executor_default_returns_success(tmp_path: Path) -> None:
    executor = MockExecutor({})

    result, log, exit_code = executor.execute_step(
        fn_id="base.xarray.rename",
        work_dir=tmp_path,
        inputs={},
        params={},
    )

    assert result["ok"] is True
    assert result["outputs"] == {}
    assert log == "Mock execution successful"
    assert exit_code == 0


def test_mock_executor_registry_override(tmp_path: Path) -> None:
    def _mock_fn(work_dir: Path, inputs: dict, params: dict):
        output_path = work_dir / "mock.txt"
        output_path.write_text("ok")
        return (
            {
                "ok": True,
                "outputs": {
                    "output": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "path": str(output_path),
                    }
                },
            },
            "Mock ran",
            0,
        )

    executor = MockExecutor({"base.xarray.rename": _mock_fn})

    result, log, exit_code = executor.execute_step(
        fn_id="base.xarray.rename",
        work_dir=tmp_path,
        inputs={"image": {"type": "BioImageRef"}},
        params={"mapping": {"Z": "T"}},
    )

    assert result["ok"] is True
    assert "output" in result["outputs"]
    assert log == "Mock ran"
    assert exit_code == 0


def test_mcp_test_client_list_and_search(mcp_services) -> None:
    client = MCPTestClient(
        discovery=mcp_services["discovery"],
        execution=mcp_services["execution"],
    )

    tools_result = client.list_tools()
    assert tools_result["items"]

    search_result = client.search_functions("rename")
    fn_ids = [fn["id"] for fn in search_result["results"]]
    assert any("rename" in fn_id for fn_id in fn_ids)
    assert any(
        fn_id in {"base.xarray.DataArray.rename", "base.pandas.DataFrame.rename"}
        for fn_id in fn_ids
    )


def test_mcp_test_client_call_tool_uses_mock_and_tracks_context(mcp_services) -> None:
    def _mock_fn(work_dir: Path, inputs: dict, params: dict):
        output_path = work_dir / "relabeled.ome.tiff"
        output_path.write_text("mock")
        return (
            {
                "ok": True,
                "outputs": {
                    "output": {
                        "type": "BioImageRef",
                        "format": "OME-TIFF",
                        "path": str(output_path),
                    }
                },
            },
            "Mock relabel",
            0,
        )

    executor = MockExecutor({"base.xarray.rename": _mock_fn})
    client = MCPTestClient(
        discovery=mcp_services["discovery"],
        execution=mcp_services["execution"],
        mock_executor=executor,
    )

    client.activate_functions(["base.xarray.rename"])

    result = client.call_tool(
        fn_id="base.xarray.rename",
        inputs={"image": {"type": "BioImageRef", "uri": "file://mock"}},
        params={"mapping": {"Z": "T"}},
    )

    assert result["status"] == "success"
    assert "outputs" in result
    assert "output" in result["outputs"]
    assert "base.xarray.rename.output" in client.context
