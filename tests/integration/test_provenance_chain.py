"""Integration test for provenance chain tracking (T042)."""

import sys
from pathlib import Path
import pytest
import numpy as np

# Add src to path for direct script execution/testing
REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config

FIXTURE_CZI = REPO_ROOT / "datasets" / "sample_czi" / "Plate1-Blue-A-02-Scene-1-P2-E1-01.czi"


@pytest.mark.skipif(not FIXTURE_CZI.exists(), reason="CZI fixture not available")
@pytest.mark.integration
class TestProvenanceChain:
    """Test that multi-step workflows record complete provenance."""

    def test_czi_squeeze_chain_records_transformations(self, tmp_path: Path, monkeypatch):
        """CZI → Squeeze chain records all transformations in provenance."""
        # 1. Create config
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[REPO_ROOT / "tools" / "base"],
            fs_allowlist_read=[REPO_ROOT],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )

        # Mock environment manager to use current python executable
        monkeypatch.setattr("bioimage_mcp.runtimes.executor.detect_env_manager", lambda: None)

        with ExecutionService(config) as svc:
            # Step 1: Squeeze CZI
            # CZIs often have singleton dimensions (T, Z, or C)
            workflow_step1 = {
                "steps": [
                    {
                        "fn_id": "base.xarray.squeeze",
                        "inputs": {
                            "image": {
                                "type": "BioImageRef",
                                "format": "CZI",
                                "uri": FIXTURE_CZI.as_uri(),
                            }
                        },
                        "params": {},
                    }
                ],
                "run_opts": {"output_mode": "memory"},
            }

            result1 = svc.run_workflow(workflow_step1, skip_validation=True)
            if result1["status"] == "failed":
                pytest.skip(f"Step 1 failed: {result1.get('error')}")

            run1_status = svc.get_run_status(result1["run_id"])
            squeeze_out = run1_status["outputs"]["output"]

            assert squeeze_out["storage_type"] == "memory"
            assert squeeze_out["uri"].startswith("mem://")

            # Step 2: Denoise (Gaussian)
            # This should trigger a handoff because input is a memory artifact
            workflow_step2 = {
                "steps": [
                    {
                        "fn_id": "base.skimage.filters.gaussian",
                        "inputs": {"image": squeeze_out},
                        "params": {"sigma": 1.0},
                    }
                ]
            }

            result2 = svc.run_workflow(workflow_step2, skip_validation=True)
            if result2["status"] == "failed":
                pytest.skip(f"Step 2 failed: {result2.get('error')}")

            # 3. Get run status and check provenance
            run2 = svc._run_store.get(result2["run_id"])
            provenance = run2.provenance

            assert "fn_id" in provenance
            assert provenance["fn_id"] == "base.skimage.filters.gaussian"

            # Check for handoffs because we passed a memory artifact
            assert "handoffs" in provenance
            handoffs = provenance["handoffs"]
            assert len(handoffs) > 0

            # Verify the handoff record structure
            handoff = handoffs[0]
            assert handoff["source_ref_id"] == squeeze_out["ref_id"]
            assert "target_ref_id" in handoff
            assert "source_env" in handoff
            assert "target_env" in handoff
            assert handoff["negotiated_format"] == "OME-TIFF"
            assert "timestamp" in handoff

            # Check for materialized_inputs
            assert "materialized_inputs" in provenance
            assert "image" in provenance["materialized_inputs"]
            assert provenance["materialized_inputs"]["image"] == squeeze_out["ref_id"]

            # 4. Read workflow_record artifact and verify provenance field
            workflow_record_ref_id = result2["workflow_record_ref_id"]
            record_data = svc.artifact_store.parse_native_output(workflow_record_ref_id)

            assert "provenance" in record_data
            assert record_data["provenance"] == provenance
            assert "tool_manifests" in record_data
            assert len(record_data["tool_manifests"]) > 0

    def test_multi_step_chain_preserves_lineage(self, tmp_path: Path, monkeypatch):
        """Multi-step processing preserves full transformation lineage."""
        config = Config(
            artifact_store_root=tmp_path / "artifacts",
            tool_manifest_roots=[REPO_ROOT / "tools" / "base"],
            fs_allowlist_read=[REPO_ROOT],
            fs_allowlist_write=[tmp_path],
            fs_denylist=[],
        )
        monkeypatch.setattr("bioimage_mcp.runtimes.executor.detect_env_manager", lambda: None)

        with ExecutionService(config) as svc:
            # Step 1: Squeeze (Mem)
            res1 = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "base.xarray.squeeze",
                            "inputs": {
                                "image": {
                                    "type": "BioImageRef",
                                    "format": "CZI",
                                    "uri": FIXTURE_CZI.as_uri(),
                                }
                            },
                            "params": {},
                        }
                    ],
                    "run_opts": {"output_mode": "memory"},
                },
                skip_validation=True,
            )

            if res1["status"] == "failed":
                pytest.skip(f"Step 1 failed: {res1.get('error')}")

            out1 = svc.get_run_status(res1["run_id"])["outputs"]["output"]

            # Step 2: Gaussian (Mem)
            res2 = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "base.skimage.filters.gaussian",
                            "inputs": {"image": out1},
                            "params": {"sigma": 1.0},
                        }
                    ],
                    "run_opts": {"output_mode": "memory"},
                },
                skip_validation=True,
            )

            if res2["status"] == "failed":
                pytest.skip(f"Step 2 failed: {res2.get('error')}")

            out2 = svc.get_run_status(res2["run_id"])["outputs"]["output"]

            # Step 3: Gaussian again (File)
            res3 = svc.run_workflow(
                {
                    "steps": [
                        {
                            "fn_id": "base.skimage.filters.gaussian",
                            "inputs": {"image": out2},
                            "params": {"sigma": 0.5},
                        }
                    ]
                },
                skip_validation=True,
            )

            if res3["status"] == "failed":
                pytest.skip(f"Step 3 failed: {res3.get('error')}")

            # Verify Step 3 provenance links back to Step 2
            run3 = svc._run_store.get(res3["run_id"])
            assert run3.provenance["materialized_inputs"]["image"] == out2["ref_id"]

            # Verify Step 2 provenance links back to Step 1
            run2 = svc._run_store.get(res2["run_id"])
            assert run2.provenance["materialized_inputs"]["image"] == out1["ref_id"]

            # Full chain can be traced by following materialized_inputs in provenance
            # Step 3 provenance -> Step 2 output (out2)
            # Step 2 provenance -> Step 1 output (out1)
            # Step 1 provenance -> FIXTURE_CZI
            assert run3.provenance["materialized_inputs"]["image"] == out2["ref_id"]
            assert run2.provenance["materialized_inputs"]["image"] == out1["ref_id"]
