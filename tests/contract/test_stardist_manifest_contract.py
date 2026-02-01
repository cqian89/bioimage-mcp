"""Contract test validating StarDist tool manifest schema.

Validates that the StarDist manifest conforms to the ToolManifest schema
and includes required fields like env_id.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioimage_mcp.registry.manifest_schema import ToolManifest

STARDIST_MANIFEST_PATH = Path(__file__).parents[2] / "tools" / "stardist" / "manifest.yaml"


class TestStarDistManifestContract:
    """Contract tests for StarDist tool manifest."""

    def test_manifest_exists(self) -> None:
        """Test that the StarDist manifest file exists."""
        assert STARDIST_MANIFEST_PATH.exists(), (
            f"StarDist manifest not found at {STARDIST_MANIFEST_PATH}"
        )

    def test_manifest_valid_schema(self) -> None:
        """Test that manifest conforms to ToolManifest schema."""
        if not STARDIST_MANIFEST_PATH.exists():
            pytest.skip("StarDist manifest not yet created")

        with open(STARDIST_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        # Add required fields that are computed at load time
        raw["manifest_path"] = STARDIST_MANIFEST_PATH
        raw["manifest_checksum"] = "test"

        # Should not raise validation error
        manifest = ToolManifest(**raw)
        assert manifest.tool_id == "tools.stardist"

    def test_manifest_env_id_prefix(self) -> None:
        """Test that env_id starts with bioimage-mcp-."""
        if not STARDIST_MANIFEST_PATH.exists():
            pytest.skip("StarDist manifest not yet created")

        with open(STARDIST_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        env_id = raw.get("env_id", "")
        assert env_id.startswith("bioimage-mcp-"), (
            f"env_id must start with 'bioimage-mcp-', got: {env_id}"
        )

    def test_manifest_has_stardist_env_id(self) -> None:
        """Test that env_id is specifically bioimage-mcp-stardist."""
        if not STARDIST_MANIFEST_PATH.exists():
            pytest.skip("StarDist manifest not yet created")

        with open(STARDIST_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        assert raw.get("env_id") == "bioimage-mcp-stardist", (
            "env_id must be 'bioimage-mcp-stardist'"
        )

    def test_manifest_has_required_functions(self) -> None:
        """Test that manifest defines expected functions."""
        if not STARDIST_MANIFEST_PATH.exists():
            pytest.skip("StarDist manifest not yet created")

        with open(STARDIST_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        functions = raw.get("functions", [])
        fn_ids = [f.get("id") for f in functions]

        assert "stardist.models.StarDist2D.from_pretrained" in fn_ids
        assert "stardist.models.StarDist2D.predict_instances" in fn_ids
        assert "meta.describe" in fn_ids

    def test_predict_instances_io_ports(self) -> None:
        """Test that StarDist2D.predict_instances has correct I/O ports."""
        if not STARDIST_MANIFEST_PATH.exists():
            pytest.skip("StarDist manifest not yet created")

        with open(STARDIST_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        functions = raw.get("functions", [])
        predict_fn = next(
            (f for f in functions if f.get("id") == "stardist.models.StarDist2D.predict_instances"),
            None,
        )

        assert predict_fn is not None

        # Check inputs
        inputs = predict_fn.get("inputs", [])
        input_names = [i.get("name") for i in inputs]
        assert "model" in input_names
        assert "image" in input_names

        # Check outputs
        outputs = predict_fn.get("outputs", [])
        output_names = [o.get("name") for o in outputs]
        assert "labels" in output_names
        assert "details" in output_names
