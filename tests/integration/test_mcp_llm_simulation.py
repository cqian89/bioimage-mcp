"""Test script simulating an LLM interacting with the bioimage-mcp server.

This script demonstrates and tests the MCP protocol for:
1. Loading images from the FLUTE_FLIM_data_tif dataset
2. Querying MCP for cellpose functions
3. Running cellpose segmentation
4. Exporting outputs (OME-TIFF and native outputs)

Note: FLIM data typically requires conversion to intensity images before
segmentation. This test uses the raw TIFF data as-is since the current
v0.1 spec does not include a FLIM-to-intensity conversion tool.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import connect

# Path to the FLUTE FLIM dataset
FLUTE_DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "FLUTE_FLIM_data_tif"


def _path_to_uri(path: Path) -> str:
    """Convert a filesystem path to a file:// URI."""
    return f"file://{quote(str(path.absolute()), safe='/:')}"


def _mock_execute_step(
    *,
    config: Config,
    fn_id: str,
    params: dict,
    inputs: dict,
    work_dir: Path,
    timeout_seconds: int | None,
    **kwargs,
) -> tuple[dict[str, Any], str, int]:
    """Mock execute_step that simulates successful Cellpose segmentation.

    This mock is used when the cellpose environment is not available.
    """
    # Create mock output files
    labels_path = work_dir / "labels.ome.tiff"
    labels_path.write_bytes(b"FAKE_LABEL_IMAGE")

    bundle_path = work_dir / "cellpose_seg.npy"
    bundle_path.write_bytes(b"FAKE_NPY_BUNDLE")

    return (
        {
            "ok": True,
            "outputs": {
                "labels": {
                    "type": "LabelImageRef",
                    "format": "OME-TIFF",
                    "path": str(labels_path),
                },
                "cellpose_bundle": {
                    "type": "NativeOutputRef",
                    "format": "cellpose-seg-npy",
                    "path": str(bundle_path),
                },
            },
            "log": f"Cellpose segmentation completed on {inputs.get('x', {}).get('uri', 'unknown')}",
        },
        "Segmentation log: processed input image",
        0,
    )


class TestMCPLLMSimulation:
    """Simulate an LLM interacting with the bioimage-mcp server.

    This test class demonstrates the MCP tool calling flow that an LLM
    would use to perform cell segmentation on microscopy images.
    """

    @pytest.fixture
    def mcp_environment(self, tmp_path: Path, monkeypatch):
        """Set up a complete MCP environment with discovery and execution services."""
        artifacts_root = tmp_path / "artifacts"
        tools_root = Path(__file__).parent.parent.parent / "tools"

        config = Config(
            artifact_store_root=artifacts_root,
            tool_manifest_roots=[tools_root],
            fs_allowlist_read=[tmp_path, FLUTE_DATASET_PATH, tools_root],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        # Set up database connection
        conn = connect(config)

        # Load tool manifests
        manifests, diagnostics = load_manifests(config.tool_manifest_roots)

        # Set up discovery service
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

        # Mock the execute_step to avoid requiring cellpose installation
        monkeypatch.setattr(
            "bioimage_mcp.api.execution.execute_step",
            _mock_execute_step,
        )

        # Set up execution and artifacts services
        artifact_store = ArtifactStore(config, conn=conn)
        execution = ExecutionService(config, artifact_store=artifact_store)
        artifacts = ArtifactsService(artifact_store)

        yield {
            "config": config,
            "discovery": discovery,
            "execution": execution,
            "artifacts": artifacts,
            "artifact_store": artifact_store,
            "tmp_path": tmp_path,
        }

        # Cleanup
        discovery.close()
        execution.close()
        artifact_store.close()

    def test_step1_load_images_from_dataset(self, mcp_environment):
        """
        Step 1: LLM loads images from the FLUTE_FLIM_data_tif dataset.

        Simulates the LLM identifying available images and creating
        artifact references for them.
        """
        # Check that the dataset exists
        assert FLUTE_DATASET_PATH.exists(), f"Dataset not found at {FLUTE_DATASET_PATH}"

        # List available images (LLM would do this to discover data)
        tiff_files = list(FLUTE_DATASET_PATH.glob("*.tif"))
        assert len(tiff_files) > 0, "No TIFF files found in dataset"

        # Create artifact references for images
        # Note: In actual MCP flow, these would be imported via artifact store
        image_refs = []
        for tiff_file in tiff_files[:2]:  # Use first 2 images for test
            image_ref = {
                "type": "BioImageRef",
                "format": "TIFF",
                "uri": _path_to_uri(tiff_file),
            }
            image_refs.append(image_ref)

        assert len(image_refs) == 2
        assert all(ref["type"] == "BioImageRef" for ref in image_refs)

    def test_step2_query_cellpose_functions(self, mcp_environment):
        """
        Step 2: LLM queries MCP for cellpose segmentation functions.

        Demonstrates using search_functions to find available
        segmentation capabilities.
        """
        discovery = mcp_environment["discovery"]

        # Search for segmentation functions
        result = discovery.search_functions(
            query="cellpose",
            tags=["segmentation"],
            limit=10,
            cursor=None,
        )

        functions = result["results"]
        assert len(functions) > 0, "No cellpose functions found"

        # Find the cellpose.models.CellposeModel.eval function
        eval_fn = None
        for fn in functions:
            if fn["id"] == "cellpose.models.CellposeModel.eval":
                eval_fn = fn
                break

        assert eval_fn is not None, "cellpose.models.CellposeModel.eval function not found"
        assert "segmentation" in eval_fn["tags"]

    def test_step3_describe_cellpose_function(self, mcp_environment):
        """
        Step 3: LLM gets detailed description of the cellpose.models.CellposeModel.eval function.

        Uses describe_function to get the parameter schema for calling
        the segmentation function.

        Note: Per NFR-001 (payload discipline), discovery responses are
        summary-only. Input/output schemas are not returned in listings.
        The describe_function returns the params_schema on-demand.
        """
        discovery = mcp_environment["discovery"]

        # Search should find the cellpose.models.CellposeModel.eval function
        search_result = discovery.search_functions(
            query="cellpose.models.CellposeModel.eval",
            limit=1,
            cursor=None,
        )
        assert len(search_result["results"]) > 0
        fn_summary = search_result["results"][0]

        # Summary contains key info per NFR-001
        assert fn_summary["id"] == "cellpose.models.CellposeModel.eval"
        assert "segmentation" in fn_summary["tags"]

        # Get parameter schema via describe_function
        fn_details = discovery.describe_function(id="cellpose.models.CellposeModel.eval")

        assert fn_details is not None
        assert fn_details["id"] == "cellpose.models.CellposeModel.eval"
        assert "params_schema" in fn_details  # params_schema

    def test_step4_run_cellpose_segmentation(self, mcp_environment):
        """
        Step 4: LLM runs cellpose segmentation on an image.

        Executes the segmentation workflow and receives output artifact
        references.
        """
        execution = mcp_environment["execution"]
        mcp_environment["tmp_path"]

        # Get an image from the dataset
        tiff_files = list(FLUTE_DATASET_PATH.glob("*.tif"))
        assert len(tiff_files) > 0

        # Use hMSC-ZOOM.tif as it's smaller
        image_file = None
        for f in tiff_files:
            if "ZOOM" in f.name:
                image_file = f
                break
        if image_file is None:
            image_file = tiff_files[0]

        # Build the workflow
        workflow = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {
                        "x": {
                            "type": "BioImageRef",
                            "format": "TIFF",
                            "uri": _path_to_uri(image_file),
                        }
                    },
                    "params": {
                        "model_type": "cyto3",
                        "diameter": 30.0,
                    },
                }
            ]
        }

        # Run the workflow (skip validation since we're using mock)
        result = execution.run_workflow(workflow, skip_validation=True)

        assert result["status"] in ("success", "running", "queued")
        assert "run_id" in result

        # Get run status
        status = execution.get_run_status(result["run_id"])

        assert "outputs" in status
        outputs = status["outputs"]

        # Verify LabelImageRef output
        assert "labels" in outputs
        assert outputs["labels"]["type"] == "LabelImageRef"

        # Verify NativeOutputRef (cellpose bundle)
        assert "cellpose_bundle" in outputs
        assert outputs["cellpose_bundle"]["type"] == "NativeOutputRef"
        assert outputs["cellpose_bundle"]["format"] == "cellpose-seg-npy"

        # Verify workflow record for replay capability
        assert "workflow_record" in outputs
        assert outputs["workflow_record"]["format"] == "workflow-record-json"

    def test_step5_export_outputs(self, mcp_environment):
        """
        Step 5: LLM exports the segmentation outputs to local files.

        Demonstrates exporting artifacts to user-specified paths.
        """
        execution = mcp_environment["execution"]
        mcp_environment["artifacts"]
        artifact_store = mcp_environment["artifact_store"]
        tmp_path = mcp_environment["tmp_path"]

        # First run a segmentation (reusing step 4 logic)
        tiff_files = list(FLUTE_DATASET_PATH.glob("*.tif"))
        image_file = tiff_files[0]

        workflow = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {
                        "x": {
                            "type": "BioImageRef",
                            "format": "TIFF",
                            "uri": _path_to_uri(image_file),
                        }
                    },
                    "params": {"model_type": "cyto3", "diameter": 30.0},
                }
            ]
        }

        result = execution.run_workflow(workflow, skip_validation=True)
        status = execution.get_run_status(result["run_id"])
        outputs = status["outputs"]

        # Export the label image (OME-TIFF)
        labels_ref = outputs["labels"]
        labels_export_path = tmp_path / "exported_labels.ome.tiff"

        exported = artifact_store.export(labels_ref["ref_id"], labels_export_path)

        assert labels_export_path.exists(), "Exported labels file not found"
        assert str(exported) == str(labels_export_path)

        # Export the native output (cellpose bundle)
        bundle_ref = outputs["cellpose_bundle"]
        bundle_export_path = tmp_path / "exported_bundle.npy"

        exported = artifact_store.export(bundle_ref["ref_id"], bundle_export_path)

        assert bundle_export_path.exists(), "Exported bundle file not found"
        assert str(exported) == str(bundle_export_path)

    def test_full_llm_workflow_simulation(self, mcp_environment):
        """
        Complete end-to-end test simulating an LLM's interaction with
        the bioimage-mcp server.

        This test demonstrates the full flow:
        1. Query available functions
        2. Get function details
        3. Run segmentation
        4. Export results
        """
        discovery = mcp_environment["discovery"]
        execution = mcp_environment["execution"]
        mcp_environment["artifacts"]
        tmp_path = mcp_environment["tmp_path"]

        # === LLM Step 1: Query for segmentation capabilities ===
        print("\n[LLM] Searching for cell segmentation tools...")
        search_result = discovery.search_functions(
            query="cellpose",
            tags=None,
            io_in="BioImageRef",
            io_out="LabelImageRef",
            limit=5,
            cursor=None,
        )

        assert len(search_result["results"]) > 0
        print(f"[LLM] Found {len(search_result['results'])} segmentation functions")

        # === LLM Step 2: Get details on cellpose.models.CellposeModel.eval ===
        print("\n[LLM] Getting details for cellpose.models.CellposeModel.eval...")

        # Get input/output info from search results (per NFR-001 payload discipline)
        fn_summary = [
            f for f in search_result["results"] if f["id"] == "cellpose.models.CellposeModel.eval"
        ][0]
        print(f"[LLM] Function requires inputs: {fn_summary.get('io', {}).get('inputs', [])}")
        print(f"[LLM] Function produces outputs: {fn_summary.get('io', {}).get('outputs', [])}")

        # Get parameter schema via describe_function
        fn_details = discovery.describe_function(id="cellpose.models.CellposeModel.eval")
        print(f"[LLM] Parameter schema: {fn_details.get('params_schema', {})}")

        # === LLM Step 3: Prepare input image ===
        print("\n[LLM] Preparing input image from dataset...")
        tiff_files = list(FLUTE_DATASET_PATH.glob("*.tif"))
        # Use smallest file for faster test
        smallest_file = min(tiff_files, key=lambda f: f.stat().st_size)
        print(f"[LLM] Selected image: {smallest_file.name}")

        # === LLM Step 4: Run segmentation workflow ===
        print("\n[LLM] Running cellpose segmentation workflow...")
        workflow = {
            "steps": [
                {
                    "id": "cellpose.models.CellposeModel.eval",
                    "inputs": {
                        "image": {
                            "type": "BioImageRef",
                            "format": "TIFF",
                            "uri": _path_to_uri(smallest_file),
                        }
                    },
                    "params": {
                        "model_type": "cyto3",
                        "diameter": 30.0,
                    },
                }
            ]
        }

        result = execution.run_workflow(workflow, skip_validation=True)
        print(f"[LLM] Workflow started with run_id: {result['run_id']}")
        print(f"[LLM] Status: {result['status']}")

        # Get final status
        status = execution.get_run_status(result["run_id"])
        print(f"[LLM] Final status: {status['status']}")

        # === LLM Step 5: Export outputs ===
        print("\n[LLM] Exporting outputs...")
        outputs = status["outputs"]
        artifact_store = mcp_environment["artifact_store"]

        # Export OME-TIFF labels
        labels_path = tmp_path / "segmentation_labels.ome.tiff"
        artifact_store.export(outputs["labels"]["ref_id"], labels_path)
        print(f"[LLM] Exported labels to: {labels_path}")

        # Export native bundle
        bundle_path = tmp_path / "cellpose_bundle.npy"
        artifact_store.export(outputs["cellpose_bundle"]["ref_id"], bundle_path)
        print(f"[LLM] Exported native bundle to: {bundle_path}")

        # Verify outputs exist
        assert labels_path.exists(), "Labels file was not exported"
        assert bundle_path.exists(), "Bundle file was not exported"

        print("\n[LLM] Segmentation workflow completed successfully!")
        print(f"[LLM] Outputs saved to: {tmp_path}")


class TestMCPToolsAvailability:
    """Tests to verify MCP tools are properly registered and accessible."""

    @pytest.fixture
    def discovery_service(self, tmp_path: Path):
        """Set up discovery service with tool manifests."""
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
        manifests, _ = load_manifests(config.tool_manifest_roots)

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

        yield discovery
        discovery.close()

    def test_list_tools_returns_cellpose(self, discovery_service):
        """Verify cellpose tool pack is registered."""
        result = discovery_service.list_tools(limit=20, cursor=None)

        tool_paths = [t["id"] for t in result["items"]]
        assert "cellpose" in tool_paths, "Cellpose environment not found"

    def test_search_functions_finds_cellpose_eval(self, discovery_service):
        """Verify cellpose.models.CellposeModel.eval function is discoverable."""
        result = discovery_service.search_functions(
            query="cellpose",
            limit=10,
            cursor=None,
        )

        fn_ids = [f["id"] for f in result["results"]]
        assert "cellpose.models.CellposeModel.eval" in fn_ids, (
            "cellpose.models.CellposeModel.eval function not found"
        )

    def test_describe_function_returns_cellpose_schema(self, discovery_service):
        """Verify cellpose.models.CellposeModel.eval function details are complete.

        Per NFR-001, describe_function returns the params_schema on-demand.
        Summary fields are available from search_functions.
        """
        # Get parameter schema via describe_function
        fn = discovery_service.describe_function(id="cellpose.models.CellposeModel.eval")

        assert fn["id"] == "cellpose.models.CellposeModel.eval"
        assert "params_schema" in fn  # params_schema (per NFR-001)

        # Verify summary fields are available from search_functions
        result = discovery_service.search_functions(
            query="cellpose.models.CellposeModel.eval",
            limit=1,
            cursor=None,
        )
        fn_summary = result["results"][0]
        assert "tags" in fn_summary
        assert "segmentation" in fn_summary["tags"]
        assert "summary" in fn_summary
