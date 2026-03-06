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
    """Check if a dataset file looks usable."""
    print(f"Checking path: {path} (exists: {path.exists()})")
    if not path.exists():
        return False

    size = path.stat().st_size
    if size <= 0:
        return False

    # Git LFS pointer files are small text files (typically < 1KB)
    if size < 1024:
        try:
            first_line = path.read_text(errors="ignore").splitlines()[:1]
            if first_line and first_line[0].startswith(
                "version https://git-lfs.github.com/spec/v1"
            ):
                return False
        except OSError:
            return False

    return True


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


@pytest.mark.smoke_extended
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
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(SPC_FILE.absolute()),
                    "container_type": "SPC-130",
                },
            },
        )
        assert open_result.get("status") == "success", f"Failed to open TTTR: {open_result}"
        assert "outputs" in open_result, f"open_result missing 'outputs': {open_result}"
        tttr_ref = open_result["outputs"]["tttr"]
        assert_valid_artifact_ref(tttr_ref, "TTTRRef")

        # 2. Correlate
        correlate_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.Correlator",
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
    @pytest.mark.skipif(not is_valid_dataset(SPC_FILE), reason="SPC dataset not available or empty")
    async def test_correlator_method_family(self, live_server) -> None:
        """Smoke test: representative Correlator method-family IDs."""
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(SPC_FILE.absolute()),
                    "container_type": "SPC-130",
                },
            },
        )
        assert open_result.get("status") == "success"
        tttr_ref = open_result["outputs"]["tttr"]

        curve_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.Correlator.get_curve",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "channels": [[0], [8]],
                    "n_bins": 7,
                    "n_casc": 27,
                },
            },
        )
        assert curve_result.get("status") == "success", (
            f"Correlator.get_curve failed: {curve_result}"
        )
        curve_ref = curve_result["outputs"]["curve"]
        assert_valid_artifact_ref(curve_ref, "TableRef")

        x_axis_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.Correlator.get_x_axis",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "channels": [[0], [8]],
                    "n_bins": 7,
                    "n_casc": 27,
                },
            },
        )
        assert x_axis_result.get("status") == "success", (
            f"Correlator.get_x_axis failed: {x_axis_result}"
        )
        tau_ref = x_axis_result["outputs"]["tau"]
        assert_valid_artifact_ref(tau_ref, "TableRef")

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    async def test_clsm_metadata_methods(self, live_server) -> None:
        """Smoke test: representative CLSMImage metadata method-family IDs."""
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(PTU_FILE.absolute()),
                    "container_type": "PTU",
                },
            },
        )
        assert open_result.get("status") == "success"
        tttr_ref = open_result["outputs"]["tttr"]

        clsm_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                    "marker_frame_start": [4],
                    "marker_line_start": 2,
                    "marker_line_stop": 3,
                },
            },
        )
        assert clsm_result.get("status") == "success"
        clsm_ref = clsm_result["outputs"]["clsm"]

        image_info_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_image_info",
                "inputs": {"clsm": clsm_ref},
            },
        )
        assert image_info_result.get("status") == "success", (
            f"CLSMImage.get_image_info failed: {image_info_result}"
        )
        image_info_ref = image_info_result["outputs"]["image_info"]
        assert_valid_artifact_ref(image_info_ref, "NativeOutputRef")

        settings_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_settings",
                "inputs": {"clsm": clsm_ref},
            },
        )
        assert settings_result.get("status") == "success", (
            f"CLSMImage.get_settings failed: {settings_result}"
        )
        settings_ref = settings_result["outputs"]["settings"]
        assert_valid_artifact_ref(settings_ref, "NativeOutputRef")

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    async def test_ics_workflow(self, live_server) -> None:
        """Smoke test 8.2: ICS workflow."""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(PTU_FILE.absolute()),
                    "container_type": "PTU",
                },
            },
        )
        assert open_result.get("status") == "success"
        assert "outputs" in open_result, f"open_result missing 'outputs': {open_result}"
        tttr_ref = open_result["outputs"]["tttr"]

        # 2. Construct CLSMImage
        clsm_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                    "marker_frame_start": [4],
                    "marker_line_start": 2,
                    "marker_line_stop": 3,
                },
            },
        )
        assert clsm_result.get("status") == "success", f"CLSMImage failed: {clsm_result}"
        clsm_ref = clsm_result["outputs"]["clsm"]
        assert_valid_artifact_ref(clsm_ref, "ObjectRef")

        # 3. Compute ICS
        ics_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.compute_ics",
                "inputs": {"clsm": clsm_ref},
                "params": {
                    "subtract_average": "frame",
                },
            },
        )
        assert ics_result.get("status") == "success", f"ICS failed: {ics_result}"
        ics_ref = ics_result["outputs"]["ics"]
        assert_valid_artifact_ref(ics_ref, "BioImageRef")

        # Assertion: file exists as OME-Zarr
        uri = ics_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists()
        assert path.is_dir()
        assert str(path).lower().endswith((".ome.zarr", ".zarr"))
        assert ics_ref.get("format") == "OME-Zarr"

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    async def test_intensity_extraction(self, live_server) -> None:
        """Smoke test: TTTR → CLSMImage → intensity → BioImageRef"""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
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
                "id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                    "marker_frame_start": [4],
                    "marker_line_start": 2,
                    "marker_line_stop": 3,
                },
            },
        )
        assert clsm_result.get("status") == "success"
        clsm_ref = clsm_result["outputs"]["clsm"]

        # 3. Get intensity image
        intensity_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_intensity",
                "inputs": {"clsm": clsm_ref},
                "params": {"stack_frames": True},
            },
        )
        assert intensity_result.get("status") == "success"
        intensity_ref = intensity_result["outputs"]["intensity"]
        assert_valid_artifact_ref(intensity_ref, "BioImageRef")

        # Verify output file exists
        uri = intensity_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists()
        assert path.is_dir()
        assert str(path).lower().endswith((".ome.zarr", ".zarr"))
        assert intensity_ref.get("format") == "OME-Zarr"

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    async def test_phasor_extraction(self, live_server) -> None:
        """Smoke test: TTTR → CLSMImage → phasor → BioImageRef (Pathway A)"""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
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
                "id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                    "marker_frame_start": [4],
                    "marker_line_start": 2,
                    "marker_line_stop": 3,
                },
            },
        )
        assert clsm_result.get("status") == "success"
        clsm_ref = clsm_result["outputs"]["clsm"]

        # 3. Get phasor image
        phasor_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_phasor",
                "inputs": {"clsm": clsm_ref, "tttr_data": tttr_ref},
                "params": {"frequency": 80.0, "stack_frames": True},
                "verbosity": "full",
            },
        )
        if phasor_result.get("status") == "success":
            print(f"PHASOR OUTPUT: {phasor_result['outputs']['phasor']}")
        assert phasor_result.get("status") == "success", f"Phasor failed: {phasor_result}"
        phasor_ref = phasor_result["outputs"]["phasor"]
        assert_valid_artifact_ref(phasor_ref, "BioImageRef")

        # Verify output file exists and has g,s channels
        uri = phasor_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists()
        assert path.is_dir()
        assert str(path).lower().endswith((".ome.zarr", ".zarr"))
        assert phasor_ref.get("format") == "OME-Zarr"

        # Check metadata indicates 2 channels (g, s)
        metadata = phasor_ref.get("metadata", {})
        axes = metadata.get("axes", "")
        shape = metadata.get("shape", [])
        assert isinstance(axes, str) and "C" in axes, f"Expected channel axis in axes: {axes}"
        assert shape, f"Expected shape in metadata: {metadata}"
        c_index = axes.index("C")
        assert shape[c_index] == 2, f"Expected 2 channels, got shape={shape} axes={axes}"

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    async def test_fluorescence_decay_extraction(self, live_server) -> None:
        """Smoke test: TTTR → CLSMImage → decay → BioImageRef (Pathway B)"""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
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
                "id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                    "marker_frame_start": [4],
                    "marker_line_start": 2,
                    "marker_line_stop": 3,
                },
            },
        )
        assert clsm_result.get("status") == "success"
        clsm_ref = clsm_result["outputs"]["clsm"]

        # 3. Get fluorescence decay
        decay_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_fluorescence_decay",
                "inputs": {"clsm": clsm_ref, "tttr_data": tttr_ref},
                "params": {"micro_time_coarsening": 4, "stack_frames": True},
                "verbosity": "full",
            },
        )
        assert decay_result.get("status") == "success", f"Decay failed: {decay_result}"
        decay_ref = decay_result["outputs"]["decay"]
        assert_valid_artifact_ref(decay_ref, "BioImageRef")

        # Verify output is OME-Zarr directory (spec 026)
        uri = decay_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists(), f"Decay output not found: {path}"
        assert path.is_dir(), f"OME-Zarr output must be a directory: {path}"
        assert str(path).lower().endswith((".ome.zarr", ".zarr")), (
            f"Expected .ome.zarr or .zarr directory, got {path}"
        )

        # Verify format is OME-Zarr
        assert decay_ref.get("format") == "OME-Zarr", (
            f"Expected format='OME-Zarr', got {decay_ref.get('format')}"
        )

        # Verify metadata uses 'bins' axis for microtime bins (spec 026)
        metadata = decay_ref.get("metadata", {})
        dims = metadata.get("dims", [])
        assert "bins" in dims, f"Expected 'bins' in dims for microtime bins, got {dims}"

        # Verify axis roles
        axis_roles = metadata.get("axis_roles", {})
        assert axis_roles.get("bins") == "microtime_histogram", (
            f"Expected axis_roles['bins']='microtime_histogram', got {axis_roles}"
        )

        # Verify microtime bins count
        assert isinstance(metadata.get("n_microtime_bins"), int)
        assert metadata["n_microtime_bins"] > 0

        # Verify microtime_axis is NOT present (legacy field removed)
        assert "microtime_axis" not in metadata, (
            f"Legacy 'microtime_axis' field should be removed, got {metadata}"
        )

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    async def test_mean_lifetime_extraction(self, live_server) -> None:
        """Smoke test: TTTR → CLSMImage → lifetime → BioImageRef"""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
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
                "id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                    "marker_frame_start": [4],
                    "marker_line_start": 2,
                    "marker_line_stop": 3,
                },
            },
        )
        assert clsm_result.get("status") == "success"
        clsm_ref = clsm_result["outputs"]["clsm"]

        # 3. Get mean lifetime
        lifetime_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_mean_lifetime",
                "inputs": {"clsm": clsm_ref, "tttr_data": tttr_ref},
                "params": {"stack_frames": True},
                "verbosity": "full",
            },
        )
        if lifetime_result.get("status") != "success":
            print(f"LIFETIME SERVER STDERR:\n{live_server.get_stderr()}")
        assert lifetime_result.get("status") == "success", f"Lifetime failed: {lifetime_result}"
        lifetime_ref = lifetime_result["outputs"]["lifetime"]
        assert_valid_artifact_ref(lifetime_ref, "BioImageRef")

        # Verify output file exists
        uri = lifetime_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists()
        assert path.is_dir()
        assert str(path).lower().endswith((".ome.zarr", ".zarr"))
        assert lifetime_ref.get("format") == "OME-Zarr"

        # Check metadata indicates nanoseconds unit
        metadata = lifetime_ref.get("metadata", {})
        assert metadata.get("unit") == "nanoseconds"

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(SPC_FILE), reason="SPC dataset not available or empty")
    async def test_burst_selection(self, live_server) -> None:
        """Smoke test 8.3: Single-molecule burst selection."""
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(SPC_FILE.absolute()),
                    "container_type": "SPC-130",
                },
            },
        )
        assert open_result.get("status") == "success"
        assert "outputs" in open_result, f"open_result missing 'outputs': {open_result}"
        tttr_ref = open_result["outputs"]["tttr"]

        # 2. Get time window ranges
        ranges_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR.get_time_window_ranges",
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
    @pytest.mark.skipif(not is_valid_dataset(SPC_FILE), reason="SPC dataset not available or empty")
    async def test_specialized_spc_export(self, live_server) -> None:
        """Smoke test: specialized SPC export succeeds inside the run sandbox."""
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(SPC_FILE.absolute()),
                    "container_type": "SPC-130",
                },
            },
        )
        assert open_result.get("status") == "success", f"Failed to open TTTR: {open_result}"
        tttr_ref = open_result["outputs"]["tttr"]

        export_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR.write_spc132_events",
                "inputs": {"tttr": tttr_ref},
                "params": {"filename": "exports/m1_copy.spc"},
            },
        )
        assert export_result.get("status") == "success", f"SPC export failed: {export_result}"

        exported_ref = export_result["outputs"]["tttr_out"]
        assert_valid_artifact_ref(exported_ref, "TTTRRef")
        assert exported_ref.get("format") == "SPC"
        uri = exported_ref["uri"]
        assert uri.startswith("file://")
        path = Path(uri[7:])
        assert path.exists(), f"Exported SPC file missing: {path}"
        assert path.suffix.lower() == ".spc"

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(HDF_FILE), reason="HDF dataset not available or empty")
    async def test_photon_hdf5(self, live_server) -> None:
        """Smoke test 8.4: Photon-HDF5 opening and header extraction."""
        # 1. Open HDF
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(HDF_FILE.absolute()),
                    "container_type": "PHOTON-HDF5",
                },
            },
        )
        assert open_result.get("status") == "success"
        tttr_hdf_ref = open_result["outputs"]["tttr"]

        # 2. Get header
        header_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR.header",
                "inputs": {"tttr": tttr_hdf_ref},
            },
        )
        assert header_result.get("status") == "success"
        header_ref = header_result["outputs"]["header"]
        assert_valid_artifact_ref(header_ref, "NativeOutputRef")
        assert header_ref["format"] == "json"

        # NOTE: tttrlib can READ Photon-HDF5 but it CANNOT WRITE to it
        # (It throws "combination of container and record does not make sense")
        # So we skip testing tttrlib.TTTR.write with Photon-HDF5 containers.

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_valid_dataset(PTU_FILE), reason="PTU dataset not available or empty")
    @pytest.mark.requires_env("bioimage-mcp-cellpose")
    async def test_tttr_to_cellpose_workflow(self, live_server) -> None:
        """Smoke test: TTTR → intensity → Cellpose → per-cell lifetime analysis.

        This test demonstrates cross-tool interoperability:
        1. Open TTTR data (tttrlib)
        2. Construct CLSMImage (tttrlib)
        3. Extract intensity image (tttrlib)
        4. Segment cells with Cellpose (cellpose)
        5. Extract lifetime image (tttrlib)
        6. Combine segmentation with lifetime for per-cell analysis
        """
        # 1. Open TTTR
        open_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.TTTR",
                "inputs": {},
                "params": {
                    "filename": str(PTU_FILE.absolute()),
                    "container_type": "PTU",
                },
            },
        )
        assert open_result.get("status") == "success", f"Failed to open TTTR: {open_result}"
        tttr_ref = open_result["outputs"]["tttr"]

        # 2. Construct CLSMImage
        clsm_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage",
                "inputs": {"tttr": tttr_ref},
                "params": {
                    "reading_routine": "SP5",
                    "channels": [0],
                    "marker_frame_start": [4],
                    "marker_line_start": 2,
                    "marker_line_stop": 3,
                },
            },
        )
        assert clsm_result.get("status") == "success", f"CLSMImage failed: {clsm_result}"
        clsm_ref = clsm_result["outputs"]["clsm"]

        # 3. Get intensity image (stacked for 2D Cellpose input)
        intensity_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_intensity",
                "inputs": {"clsm": clsm_ref},
                "params": {"stack_frames": True},
            },
        )
        assert intensity_result.get("status") == "success", f"Intensity failed: {intensity_result}"
        intensity_ref = intensity_result["outputs"]["intensity"]
        assert_valid_artifact_ref(intensity_ref, "BioImageRef")

        # 4. Initialize Cellpose model
        model_result = await live_server.call_tool(
            "run",
            {
                "id": "cellpose.models.CellposeModel",
                "inputs": {},
                "params": {"model_type": "cyto3"},
            },
        )
        assert model_result.get("status") == "success", f"Model init failed: {model_result}"
        model_ref = model_result["outputs"]["model"]
        assert_valid_artifact_ref(model_ref, "ObjectRef")

        # 5. Segment with Cellpose
        seg_result = await live_server.call_tool(
            "run",
            {
                "id": "cellpose.models.CellposeModel.eval",
                "inputs": {"model": model_ref, "x": intensity_ref},
                "params": {"diameter": 30.0},
            },
        )
        assert seg_result.get("status") == "success", f"Segmentation failed: {seg_result}"
        labels_ref = seg_result["outputs"]["labels"]
        assert_valid_artifact_ref(labels_ref, "LabelImageRef")

        # 6. Get mean lifetime (stacked for matching shape)
        lifetime_result = await live_server.call_tool(
            "run",
            {
                "id": "tttrlib.CLSMImage.get_mean_lifetime",
                "inputs": {"clsm": clsm_ref, "tttr_data": tttr_ref},
                "params": {"stack_frames": True},
            },
        )
        assert lifetime_result.get("status") == "success", f"Lifetime failed: {lifetime_result}"
        lifetime_ref = lifetime_result["outputs"]["lifetime"]
        assert_valid_artifact_ref(lifetime_ref, "BioImageRef")

        # Verify both outputs exist
        for ref in [labels_ref, lifetime_ref]:
            uri = ref["uri"]
            assert uri.startswith("file://")
            path = Path(uri[7:])
            assert path.exists(), f"Output file not found: {path}"
            assert path.is_dir(), f"Output should be OME-Zarr directory: {path}"
            assert ref.get("format") == "OME-Zarr"
