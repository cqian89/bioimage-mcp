"""Contract test validating Cellpose tool manifest schema (T003a).

Validates that the Cellpose manifest conforms to the ToolManifest schema
and includes required fields like env_id.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioimage_mcp.registry.manifest_schema import ToolManifest

CELLPOSE_MANIFEST_PATH = Path(__file__).parents[2] / "tools" / "cellpose" / "manifest.yaml"


class TestCellposeManifestContract:
    """Contract tests for Cellpose tool manifest."""

    def test_manifest_exists(self) -> None:
        """Test that the Cellpose manifest file exists."""
        assert CELLPOSE_MANIFEST_PATH.exists(), (
            f"Cellpose manifest not found at {CELLPOSE_MANIFEST_PATH}"
        )

    def test_manifest_valid_schema(self) -> None:
        """Test that manifest conforms to ToolManifest schema."""
        if not CELLPOSE_MANIFEST_PATH.exists():
            pytest.skip("Cellpose manifest not yet created")

        with open(CELLPOSE_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        # Add required fields that are computed at load time
        raw["manifest_path"] = CELLPOSE_MANIFEST_PATH
        raw["manifest_checksum"] = "test"

        # Should not raise validation error
        manifest = ToolManifest(**raw)
        assert manifest.tool_id is not None

    def test_manifest_env_id_prefix(self) -> None:
        """Test that env_id starts with bioimage-mcp-."""
        if not CELLPOSE_MANIFEST_PATH.exists():
            pytest.skip("Cellpose manifest not yet created")

        with open(CELLPOSE_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        env_id = raw.get("env_id", "")
        assert env_id.startswith("bioimage-mcp-"), (
            f"env_id must start with 'bioimage-mcp-', got: {env_id}"
        )

    def test_manifest_has_cellpose_env_id(self) -> None:
        """Test that env_id is specifically bioimage-mcp-cellpose."""
        if not CELLPOSE_MANIFEST_PATH.exists():
            pytest.skip("Cellpose manifest not yet created")

        with open(CELLPOSE_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        assert raw.get("env_id") == "bioimage-mcp-cellpose", (
            "env_id must be 'bioimage-mcp-cellpose'"
        )

    def test_manifest_has_eval_function(self) -> None:
        """Test that manifest defines a cellpose.models.CellposeModel.eval function."""
        if not CELLPOSE_MANIFEST_PATH.exists():
            pytest.skip("Cellpose manifest not yet created")

        with open(CELLPOSE_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        functions = raw.get("functions", [])
        fn_ids = [f.get("fn_id") for f in functions]

        assert "cellpose.models.CellposeModel.eval" in fn_ids, (
            "Manifest must define cellpose.models.CellposeModel.eval function"
        )

    def test_manifest_has_meta_describe_function(self) -> None:
        """Test that manifest defines a meta.describe function."""
        if not CELLPOSE_MANIFEST_PATH.exists():
            pytest.skip("Cellpose manifest not yet created")

        with open(CELLPOSE_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        functions = raw.get("functions", [])
        fn_ids = [f.get("fn_id") for f in functions]

        assert "meta.describe" in fn_ids, (
            "Manifest must define meta.describe function for dynamic schema"
        )

    def test_eval_function_io_ports(self) -> None:
        """Test that cellpose.models.CellposeModel.eval has correct I/O ports."""
        if not CELLPOSE_MANIFEST_PATH.exists():
            pytest.skip("Cellpose manifest not yet created")

        with open(CELLPOSE_MANIFEST_PATH) as f:
            raw = yaml.safe_load(f)

        functions = raw.get("functions", [])
        eval_fn = next(
            (f for f in functions if f.get("fn_id") == "cellpose.models.CellposeModel.eval"),
            None,
        )

        assert eval_fn is not None, "cellpose.models.CellposeModel.eval function not found"

        # Check inputs
        inputs = eval_fn.get("inputs", [])
        input_names = [i.get("name") for i in inputs]
        assert "x" in input_names, "cellpose.models.CellposeModel.eval must have 'x' input"

        # Check outputs
        outputs = eval_fn.get("outputs", [])
        output_names = [o.get("name") for o in outputs]
        assert "labels" in output_names, (
            "cellpose.models.CellposeModel.eval must have 'labels' output"
        )
