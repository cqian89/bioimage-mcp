"""Contract test validating tttrlib tool manifest schema (Phase 1)."""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from bioimage_mcp.registry.manifest_schema import ToolManifest

TTTRLIB_MANIFEST_PATH = Path(__file__).parents[2] / "tools" / "tttrlib" / "manifest.yaml"


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
        fn_ids = [f.get("fn_id") for f in functions]

        expected_functions = [
            "tttrlib.TTTR",
            "tttrlib.TTTR.header",
            "tttrlib.TTTR.get_time_window_ranges",
            "tttrlib.Correlator",
            "tttrlib.CLSMImage",
            "tttrlib.CLSMImage.compute_ics",
            "tttrlib.CLSMImage.get_intensity",
            "tttrlib.TTTR.write",
        ]

        for fn_id in expected_functions:
            assert fn_id in fn_ids, f"Manifest must define {fn_id} function"

    def test_tttr_constructor_schema(self) -> None:
        """Test that tttrlib.TTTR has correct input/output schema."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.skip("tttrlib manifest not yet created")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        tttr_fn = next(f for f in raw["functions"] if f["fn_id"] == "tttrlib.TTTR")

        # Inputs: filename (str or path) -> we'll use a string for the URI
        # Output: TTTRRef (tttrlib.TTTR)
        assert any(o["artifact_type"] == "TTTRRef" for o in tttr_fn["outputs"])

    def test_clsm_image_schema(self) -> None:
        """Test that tttrlib.CLSMImage has correct input/output schema."""
        if not TTTRLIB_MANIFEST_PATH.exists():
            pytest.skip("tttrlib manifest not yet created")

        with open(TTTRLIB_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        clsm_fn = next(f for f in raw["functions"] if f["fn_id"] == "tttrlib.CLSMImage")

        # Inputs: tttr (TTTRRef)
        # Outputs: ObjectRef (tttrlib.CLSMImage)
        input_types = [i["artifact_type"] for i in clsm_fn.get("inputs", [])]
        output_types = [o["artifact_type"] for o in clsm_fn.get("outputs", [])]

        assert "TTTRRef" in input_types
        assert "ObjectRef" in output_types
