from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import connect
from bioimage_mcp.test_harness import WorkflowTestCase

sys.path.append(str(Path(__file__).parent))

from mcp_test_client import MCPTestClient, MockExecutor

WORKFLOW_CASES_DIR = Path(__file__).parent / "workflow_cases"


class AsyncMCPTestClient:
    """Sync wrapper around MCPTestClient for integration tests."""

    def __init__(self, client: MCPTestClient) -> None:
        self._client = client

    @property
    def context(self) -> dict[str, Any]:
        return self._client.context

    def list_tools(
        self,
        *,
        path: str | None = None,
        paths: list[str] | None = None,
        flatten: bool | None = None,
        limit: int | None = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self._client.list_tools(
            path=path,
            paths=paths,
            flatten=flatten,
            limit=limit,
            cursor=cursor,
        )

    def search_functions(
        self,
        query: str,
        *,
        tags: list[str] | None = None,
        io_in: str | None = None,
        io_out: str | None = None,
        limit: int | None = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return self._client.search_functions(
            query,
            tags=tags,
            io_in=io_in,
            io_out=io_out,
            limit=limit,
            cursor=cursor,
        )

    def activate_functions(self, fn_ids: list[str]) -> dict[str, Any]:
        return self._client.activate_functions(fn_ids)

    def describe_function(self, fn_id: str) -> dict[str, Any]:
        return self._client.describe_function(fn_id)

    def call_tool(self, fn_id: str, inputs: dict, params: dict) -> dict[str, Any]:
        return self._client.call_tool(fn_id, inputs, params)


@pytest.fixture
def mcp_services(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    tools_root = repo_root / "tools"
    datasets_root = repo_root / "datasets"

    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path, tools_root, datasets_root],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )

    conn = connect(config)
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
    conn.close()


def _resolve_input_path(inputs: dict[str, Any], repo_root: Path) -> Path | None:
    for value in inputs.values():
        if isinstance(value, dict):
            uri = value.get("uri")
            if isinstance(uri, str):
                if uri.startswith("file://"):
                    return Path(uri.replace("file://", ""))
                candidate = Path(uri)
                if candidate.is_absolute():
                    return candidate
                return (repo_root / candidate).resolve()
        if isinstance(value, str):
            if value.startswith("file://"):
                return Path(value.replace("file://", ""))
            candidate = Path(value)
            if candidate.is_absolute():
                return candidate
            return (repo_root / candidate).resolve()
    return None


def _default_mock_image(repo_root: Path) -> Path:
    candidate = repo_root / "datasets" / "synthetic" / "test.tif"
    if candidate.exists():
        return candidate
    return repo_root / "datasets" / "FLUTE_FLIM_data_tif" / "Embryo.tif"


@pytest.fixture
def mock_executor() -> MockExecutor:
    repo_root = Path(__file__).resolve().parents[2]
    default_image = _default_mock_image(repo_root)

    def _mock_output(path: Path) -> dict[str, Any]:
        return {"type": "BioImageRef", "format": "OME-TIFF", "path": str(path)}

    def _mock_relabel_axes(work_dir: Path, inputs: dict, params: dict):
        output_path = _resolve_input_path(inputs, repo_root) or default_image
        return {"ok": True, "outputs": {"output": _mock_output(output_path)}}, "Mock relabel", 0

    def _mock_phasor_from_flim(work_dir: Path, inputs: dict, params: dict):
        output_path = _resolve_input_path(inputs, repo_root) or default_image
        outputs = {
            "g_image": _mock_output(output_path),
            "s_image": _mock_output(output_path),
            "intensity_image": _mock_output(output_path),
        }
        return {"ok": True, "outputs": outputs}, "Mock phasor", 0

    def _mock_expand_dims(work_dir: Path, inputs: dict, params: dict):
        output_path = _resolve_input_path(inputs, repo_root) or default_image
        return {"ok": True, "outputs": {"output": _mock_output(output_path)}}, "Mock expand", 0

    def _mock_squeeze(work_dir: Path, inputs: dict, params: dict):
        output_path = _resolve_input_path(inputs, repo_root) or default_image
        return {"ok": True, "outputs": {"output": _mock_output(output_path)}}, "Mock squeeze", 0

    def _mock_swap_axes(work_dir: Path, inputs: dict, params: dict):
        output_path = _resolve_input_path(inputs, repo_root) or default_image
        return {"ok": True, "outputs": {"output": _mock_output(output_path)}}, "Mock swap", 0

    registry = {
        "base.xarray.rename": _mock_relabel_axes,
        "base.bioimage_mcp_base.transforms.phasor_from_flim": _mock_phasor_from_flim,
        "base.xarray.expand_dims": _mock_expand_dims,
        "base.xarray.squeeze": _mock_squeeze,
        "base.xarray.transpose": _mock_swap_axes,
    }

    return MockExecutor(registry)


@pytest.fixture
def mcp_test_client(mcp_services, mock_executor, request) -> AsyncMCPTestClient:
    use_mock = request.node.get_closest_marker("mock_execution") is not None
    client = MCPTestClient(
        discovery=mcp_services["discovery"],
        execution=mcp_services["execution"],
        mock_executor=mock_executor if use_mock else None,
    )
    return AsyncMCPTestClient(client)


@pytest.fixture
def sample_flim_image() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    sample_path = repo_root / "datasets" / "FLUTE_FLIM_data_tif" / "Embryo.tif"
    return {
        "type": "BioImageRef",
        "uri": f"file://{sample_path.absolute()}",
        "metadata": {
            "axes": "TCZYX",
            "shape": [1, 1, 56, 512, 512],
        },
    }


def _iter_case_payloads(case_path: Path, data: Any) -> Iterable[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise AssertionError(f"Workflow case file must be a mapping or list: {case_path}")


def load_workflow_cases() -> list[WorkflowTestCase]:
    cases: list[WorkflowTestCase] = []
    case_files = sorted(WORKFLOW_CASES_DIR.glob("*.yaml"))
    for case_path in case_files:
        raw = yaml.safe_load(case_path.read_text())
        for payload in _iter_case_payloads(case_path, raw):
            cases.append(WorkflowTestCase.model_validate(payload))
    return cases


@pytest.fixture(scope="session")
def workflow_test_cases() -> list[WorkflowTestCase]:
    return load_workflow_cases()
