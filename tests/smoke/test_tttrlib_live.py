"""Smoke tests for tttrlib tool pack (Phase 6).

These tests run against a live MCP server with the tttrlib tool pack.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Dataset paths
TTTR_DATA_ROOT = Path(__file__).parents[2] / "datasets" / "tttr-data"
SPC_FILE = TTTR_DATA_ROOT / "bh" / "bh_spc132.spc"
PTU_FILE = TTTR_DATA_ROOT / "imaging" / "leica" / "sp5" / "LSM_1.ptu"
HDF_FILE = TTTR_DATA_ROOT / "hdf" / "1a_1b_Mix.hdf5"


def is_valid_dataset(path: Path) -> bool:
    """Check if a dataset file exists and has non-zero size.

    We check size > 0 because placeholder files in the repository
    might be 0 bytes, which would cause tttrlib to fail when reading.
    """
    return path.exists() and path.stat().st_size > 0


def assert_valid_artifact_ref(ref: dict, expected_type: str | None = None):
    """Validate that an artifact reference has required and non-empty fields."""
    assert isinstance(ref, dict), f"Expected dict, got {type(ref)}"
    assert "ref_id" in ref, f"Missing 'ref_id' in artifact ref: {ref}"
    assert isinstance(ref["ref_id"], str) and ref["ref_id"].strip(), (
        f"ref_id must be a non-empty string: {ref.get('ref_id')}"
    )
    assert "uri" in ref, f"Missing 'uri' in artifact ref: {ref}"
    assert isinstance(ref["uri"], str) and ref["uri"].strip(), (
        f"uri must be a non-empty string: {ref.get('uri')}"
    )
    if expected_type:
        assert ref.get("type") == expected_type, (
            f"Expected artifact type {expected_type}, got {ref.get('type')}"
        )


@pytest.mark.smoke_full
@pytest.mark.requires_env("bioimage-mcp-tttrlib")
class TestTTTRLibSmoke:
    """Smoke tests for tttrlib workflows."""

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(SPC_FILE), reason="SPC dataset not available or empty")
    async def test_fcs_workflow(self, live_server) -> None:
        """Smoke test 8.1: FCS workflow."""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(SPC_FILE.absolute()),
                    "container_type": "SPC-130",
                },
            },
        )
        assert open_result.get("status") == "success", f"Failed to open TTTR: {open_result}"
        tttr_ref = open_result["outputs"]["tttr"]
        assert_valid_artifact_ref(tttr_ref, "TTTRRef")

        # 2. Correlate
        correlate_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.Correlator",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "channels": [[0], [8]],
                    "n_bins": 7,
                    "n_casc": 27,
                },
            },
        )
        assert correlate_result.get("status") == "success", (
            f"Correlation failed: {correlate_result}"
        )
        curve_ref = correlate_result["outputs"]["curve"]
        assert_valid_artifact_ref(curve_ref, "TableRef")

        # Assertions on the curve
        uri = curve_ref["uri"]
        if uri.startswith("file://"):
            path = Path(uri[7:])
            assert path.exists()
            # Basic check: tau and correlation/g2 columns
            with open(path) as f:
                header = f.readline().lower()
                assert "tau" in header
                assert "g2" in header or "correlation" in header
                rows = f.readlines()
                assert len(rows) > 0

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    async def test_ics_workflow(self, live_server) -> None:
        """Smoke test 8.2: ICS workflow."""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(PTU_FILE.absolute()),
                    "container_type": "PTU",
                },
            },
        )
        assert open_result.get("status") == "success"
        tttr_ref = open_result["outputs"]["tttr"]

        # 2. Construct CLSMImage
        clsm_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                },
            },
        )
        assert clsm_result.get("status") == "success"
        clsm_ref = clsm_result["outputs"]["clsm"]
        assert_valid_artifact_ref(clsm_ref, "ObjectRef")

        # 3. Compute ICS
        ics_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.CLSMImage.compute_ics",
                "inputs": {"clsm": clsm_ref},
                "params": {
                    "subtract_average": "frame",
                },
            },
        )
        assert ics_result.get("status") == "success"
        ics_ref = ics_result["outputs"]["ics"]
        assert_valid_artifact_ref(ics_ref, "BioImageRef")

        # Assertion: file exists as OME-TIFF
        uri = ics_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists()
        assert path.suffix.lower() in [".tif", ".tiff"]

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(SPC_FILE), reason="SPC dataset not available or empty")
    async def test_burst_selection(self, live_server) -> None:
        """Smoke test 8.3: Single-molecule burst selection."""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(SPC_FILE.absolute()),
                    "container_type": "SPC-130",
                },
            },
        )
        assert open_result.get("status") == "success"
        tttr_ref = open_result["outputs"]["tttr"]

        # 2. Get time window ranges
        ranges_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.TTTR.get_time_window_ranges",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "minimum_window_length": 0.002,
                    "minimum_number_of_photons_in_time_window": 40,
                },
            },
        )
        assert ranges_result.get("status") == "success"
        ranges_ref = ranges_result["outputs"]["ranges"]
        assert_valid_artifact_ref(ranges_ref, "TableRef")

        # Assertions on ranges
        uri = ranges_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists()
        with open(path) as f:
            header = f.readline().lower()
            assert "start_index" in header and "stop_index" in header
            rows = f.readlines()
            assert len(rows) > 0

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(HDF_FILE), reason="HDF dataset not available or empty")
    async def test_photon_hdf5(self, live_server) -> None:
        """Smoke test 8.4: Photon-HDF5 import/export."""
        # 1. Open HDF
        open_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(HDF_FILE.absolute()),
                    "container_type": "HDF",
                },
            },
        )
        assert open_result.get("status") == "success"
        tttr_hdf_ref = open_result["outputs"]["tttr"]

        # 2. Get header
        header_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.TTTR.header",
                "inputs": {"tttr": tttr_hdf_ref},
            },
        )
        assert header_result.get("status") == "success"
        header_ref = header_result["outputs"]["header"]
        assert_valid_artifact_ref(header_ref, "NativeOutputRef")
        assert header_ref["format"] == "json"

        # 3. Export
        exported_path = "exported.h5"
        write_result = await live_server.call_tool(
            "run",
            {
                "fn_id": "tttrlib.TTTR.write",
                "inputs": {"tttr": tttr_hdf_ref},
                "params": {
                    "filename": exported_path,
                },
            },
        )
        assert write_result.get("status") == "success"
        exported_ref = write_result["outputs"]["tttr_out"]
        assert_valid_artifact_ref(exported_ref, "TTTRRef")

        # Final check on exported file
        uri = exported_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists()
        assert path.suffix.lower() in [".h5", ".hdf", ".hdf5"]
