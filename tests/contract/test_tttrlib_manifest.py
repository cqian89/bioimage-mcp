"""Contract test validating tttrlib tool manifest schema (Phase 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from bioimage_mcp.registry.manifest_schema import ToolManifest

TTTRLIB_MANIFEST_PATH = Path(__file__).parents[2] / "tools" / "tttrlib" / "manifest.yaml"
TTTRLIB_COVERAGE_PATH = (
    Path(__file__).parents[2] / "tools" / "tttrlib" / "schema" / "tttrlib_coverage.json"
)


class TestTTTRLibManifestContract:
    """Contract tests for tttrlib tool manifest."""

    def test_manifest_exists(self) -> None:
        """Test that the tttrlib manifest file exists."""
        assert TTTRLIB_MANIFEST_PATH.exists(), (
            f"tttrlib manifest not found at {TTTRLIB_MANIFEST_PATH}"
        )

    def test_manifest_valid_schema(self) -> None:
        """Test that manifest conforms to ToolManifest schema."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.fail("tttrlib manifest does not exist")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        # Add required fields that are computed at load time in the real registry
        raw["manifest_path"] = TTTRLIB_MANIFEST_PATH
        raw["manifest_checksum"] = "test-checksum"

        # Should not raise validation error
        manifest = ToolManifest(**raw)
        assert manifest.tool_id == "tools.tttrlib"
        assert manifest.env_id == "bioimage-mcp-tttrlib"

    def test_manifest_curated_api_functions(self) -> None:
        """Test that the manifest defines the expected Curated API functions."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.skip("tttrlib manifest not yet created")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        functions = raw.get("functions", [])
        fn_ids = [f.get("id") for f in functions]

        expected_functions = [
            "tttrlib.TTTR",
            "tttrlib.TTTR.header",
            "tttrlib.TTTR.get_count_rate",
            "tttrlib.TTTR.get_intensity_trace",
            "tttrlib.TTTR.get_selection_by_channel",
            "tttrlib.TTTR.get_selection_by_count_rate",
            "tttrlib.TTTR.get_tttr_by_selection",
            "tttrlib.TTTR.get_time_window_ranges",
            "tttrlib.Correlator",
            "tttrlib.CLSMImage",
            "tttrlib.CLSMImage.compute_ics",
            "tttrlib.CLSMImage.get_intensity",
            "tttrlib.CLSMImage.get_phasor",
            "tttrlib.CLSMImage.get_fluorescence_decay",
            "tttrlib.CLSMImage.get_mean_lifetime",
            "tttrlib.TTTR.write",
        ]

        for fn_id in expected_functions:
            assert fn_id in fn_ids, f"Manifest must define {fn_id} function"

    def test_removed_tttr_export_methods_stay_out_of_discovery(self) -> None:
        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        fn_ids = {f.get("id") for f in raw.get("functions", [])}

        removed_export_ids = {
            "tttrlib.TTTR.write_header",
            "tttrlib.TTTR.write_hht3v2_events",
            "tttrlib.TTTR.write_spc132_events",
        }

        assert removed_export_ids.isdisjoint(fn_ids)

    def test_removed_tttr_export_methods_have_unsupported_coverage_entries(self) -> None:
        with open(TTTRLIB_COVERAGE_PATH) as f:
            coverage = json.load(f)["coverage"]

        assert coverage["tttrlib.TTTR.write_header"]["status"] in {"deferred", "denied"}
        assert coverage["tttrlib.TTTR.write_hht3v2_events"]["status"] in {"deferred", "denied"}
        assert coverage["tttrlib.TTTR.write_spc132_events"]["status"] in {"deferred", "denied"}

    def test_tttr_constructor_schema(self) -> None:
        """Test that tttrlib.TTTR has correct input/output schema."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.skip("tttrlib manifest not yet created")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        tttr_fn = next(f for f in raw["functions"] if f["id"] == "tttrlib.TTTR")

        # Inputs: filename (str or path) -> we'll use a string for the URI
        # Output: TTTRRef (tttrlib.TTTR)
        assert any(o["artifact_type"] == "TTTRRef" for o in tttr_fn["outputs"])

    def test_clsm_image_schema(self) -> None:
        """Test that tttrlib.CLSMImage has correct input/output schema."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.skip("tttrlib manifest not yet created")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        clsm_fn = next(f for f in raw["functions"] if f["id"] == "tttrlib.CLSMImage")

        # Inputs: tttr (TTTRRef)
        # Outputs: ObjectRef (tttrlib.CLSMImage)
        input_types = [i["artifact_type"] for i in clsm_fn.get("inputs", [])]
        output_types = [o["artifact_type"] for o in clsm_fn.get("outputs", [])]

        assert "TTTRRef" in input_types
        assert "ObjectRef" in output_types

    def test_clsm_image_reading_routine_supports_bh_spc130(self) -> None:
        """Test that BH_SPC130 is advertised for CLSMImage reading_routine."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.skip("tttrlib manifest not yet created")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        clsm_fn = next(f for f in raw["functions"] if f["id"] == "tttrlib.CLSMImage")
        enum_values = clsm_fn["params_schema"]["properties"]["reading_routine"].get("enum") or []

        assert "BH_SPC130" in enum_values

    def test_decay_output_format_is_ome_zarr(self) -> None:
        """Test that get_fluorescence_decay output declares OME-Zarr format (spec 026)."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.skip("tttrlib manifest not yet created")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        decay_fn = next(
            f for f in raw["functions"] if f["id"] == "tttrlib.CLSMImage.get_fluorescence_decay"
        )

        # Find the decay output
        decay_output = next(o for o in decay_fn["outputs"] if o["name"] == "decay")

        assert decay_output["format"] == "OME-Zarr", (
            f"Decay output must be OME-Zarr per spec 026, got {decay_output.get('format')}"
        )

    def test_tttr_live_signature_params_are_advertised(self) -> None:
        """TTTR getter/selection manifest params should match live tttrlib shapes."""
        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        intensity_fn = next(
            f for f in raw["functions"] if f["id"] == "tttrlib.TTTR.get_intensity_trace"
        )
        intensity_props = intensity_fn["params_schema"]["properties"]
        assert "time_window_length" in intensity_props
        assert "time_window" not in intensity_props

        channel_fn = next(
            f for f in raw["functions"] if f["id"] == "tttrlib.TTTR.get_selection_by_channel"
        )
        channel_props = channel_fn["params_schema"]["properties"]
        assert set(channel_props) == {"input"}

        count_rate_fn = next(
            f for f in raw["functions"] if f["id"] == "tttrlib.TTTR.get_selection_by_count_rate"
        )
        count_rate_props = count_rate_fn["params_schema"]["properties"]
        assert "time_window" in count_rate_props
        assert "n_ph_max" in count_rate_props
        assert "invert" in count_rate_props
        assert "minimum_window_length" not in count_rate_props
        assert "minimum_number_of_photons_in_time_window" not in count_rate_props
        assert "make_mask" not in count_rate_props
