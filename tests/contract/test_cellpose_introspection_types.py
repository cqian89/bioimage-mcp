"""Contract tests for cellpose parameter introspection type fields.

These tests verify that dynamically introspected cellpose parameters
include proper JSON Schema 'type' fields, not just descriptions.

Addresses the bug where _introspect_cellpose_fn() was extracting parameters
but not setting the 'type' field, making schemas effectively invalid.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add tools path for direct import testing
TOOLS_PATH = Path(__file__).parent.parent.parent / "tools" / "cellpose"

# Clear any cached bioimage_mcp_cellpose imports to ensure fresh import
for mod_name in list(sys.modules.keys()):
    if "bioimage_mcp_cellpose" in mod_name:
        del sys.modules[mod_name]

# Ensure tools path is at the front
if str(TOOLS_PATH) in sys.path:
    sys.path.remove(str(TOOLS_PATH))
sys.path.insert(0, str(TOOLS_PATH))


def _is_fallback_schema(schema: dict) -> bool:
    """Check if the schema is the hardcoded fallback (cellpose not importable)."""
    props = schema.get("properties", {})
    # The fallback has n_epochs default=10, real cellpose has 2000
    n_epochs = props.get("n_epochs", {})
    return n_epochs.get("default") == 10


class TestInferJsonType:
    """Tests for the _infer_json_type helper function."""

    @pytest.fixture
    def infer_json_type(self):
        """Import the helper function."""
        from bioimage_mcp_cellpose.entrypoint import _infer_json_type

        return _infer_json_type

    def test_infer_boolean(self, infer_json_type):
        """Boolean values should map to 'boolean'."""
        assert infer_json_type(True) == "boolean"
        assert infer_json_type(False) == "boolean"

    def test_infer_integer(self, infer_json_type):
        """Integer values should map to 'integer'."""
        assert infer_json_type(0) == "integer"
        assert infer_json_type(100) == "integer"
        assert infer_json_type(-42) == "integer"

    def test_infer_number(self, infer_json_type):
        """Float values should map to 'number'."""
        assert infer_json_type(0.5) == "number"
        assert infer_json_type(3.14159) == "number"
        assert infer_json_type(-1e-5) == "number"

    def test_infer_string(self, infer_json_type):
        """String values should map to 'string'."""
        assert infer_json_type("") == "string"
        assert infer_json_type("hello") == "string"
        assert infer_json_type("cyto3") == "string"

    def test_infer_array(self, infer_json_type):
        """List/tuple values should map to 'array'."""
        assert infer_json_type([]) == "array"
        assert infer_json_type([1, 2, 3]) == "array"
        assert infer_json_type((0, 0)) == "array"


class TestTrainSegIntrospection:
    """Tests for cellpose.train.train_seg parameter introspection."""

    @pytest.fixture
    def introspect_fn(self):
        """Import the introspection function."""
        from bioimage_mcp_cellpose.entrypoint import _introspect_cellpose_fn

        return _introspect_cellpose_fn

    def test_train_seg_params_have_type_field(self, introspect_fn):
        """All train_seg parameters MUST have 'type' field."""
        schema = introspect_fn("cellpose.train.train_seg")

        properties = schema.get("properties", {})
        assert len(properties) > 0, "train_seg should have parameters"

        for name, spec in properties.items():
            assert "type" in spec, f"Parameter '{name}' missing 'type' field"
            assert spec["type"] in ["string", "number", "integer", "boolean", "array", "object"], (
                f"Parameter '{name}' has invalid type: {spec.get('type')}"
            )

    def test_train_seg_key_params_exposed(self, introspect_fn):
        """Critical training parameters must be exposed."""
        schema = introspect_fn("cellpose.train.train_seg")

        if _is_fallback_schema(schema):
            pytest.skip("Cellpose not importable - using fallback schema")

        properties = schema.get("properties", {})

        # These are essential training parameters
        key_params = ["n_epochs", "learning_rate", "batch_size", "save_path"]

        for param in key_params:
            assert param in properties, f"Missing key training param: {param}"

    def test_train_seg_n_epochs_correct_type(self, introspect_fn):
        """n_epochs should be integer type."""
        schema = introspect_fn("cellpose.train.train_seg")
        properties = schema.get("properties", {})

        assert "n_epochs" in properties
        assert properties["n_epochs"].get("type") == "integer"
        assert "default" in properties["n_epochs"]

    def test_train_seg_learning_rate_correct_type(self, introspect_fn):
        """learning_rate should be number type."""
        schema = introspect_fn("cellpose.train.train_seg")
        properties = schema.get("properties", {})

        assert "learning_rate" in properties
        assert properties["learning_rate"].get("type") == "number"

    def test_train_seg_normalize_correct_type(self, introspect_fn):
        """normalize should be boolean type."""
        schema = introspect_fn("cellpose.train.train_seg")

        if _is_fallback_schema(schema):
            pytest.skip("Cellpose not importable - using fallback schema")

        properties = schema.get("properties", {})

        assert "normalize" in properties
        assert properties["normalize"].get("type") == "boolean"


class TestCellposeModelEvalIntrospection:
    """Tests for cellpose.models.CellposeModel.eval parameter introspection."""

    @pytest.fixture
    def introspect_fn(self):
        """Import the introspection function."""
        from bioimage_mcp_cellpose.entrypoint import _introspect_cellpose_fn

        return _introspect_cellpose_fn

    def test_eval_params_have_type_field(self, introspect_fn):
        """All CellposeModel.eval parameters MUST have 'type' field."""
        schema = introspect_fn("cellpose.models.CellposeModel.eval")

        properties = schema.get("properties", {})
        assert len(properties) > 0, "CellposeModel.eval should have parameters"

        for name, spec in properties.items():
            assert "type" in spec, f"Parameter '{name}' missing 'type' field"

    def test_eval_diameter_correct_type(self, introspect_fn):
        """diameter should have type field (likely number or string for None)."""
        schema = introspect_fn("cellpose.models.CellposeModel.eval")

        if _is_fallback_schema(schema):
            pytest.skip("Cellpose not importable - using fallback schema")

        properties = schema.get("properties", {})

        assert "diameter" in properties
        # diameter can have None default, so type might be string
        assert "type" in properties["diameter"]

    def test_eval_flow_threshold_correct_type(self, introspect_fn):
        """flow_threshold should be number type."""
        schema = introspect_fn("cellpose.models.CellposeModel.eval")

        if _is_fallback_schema(schema):
            pytest.skip("Cellpose not importable - using fallback schema")

        properties = schema.get("properties", {})

        assert "flow_threshold" in properties
        assert properties["flow_threshold"].get("type") == "number"
        assert properties["flow_threshold"].get("default") == 0.4


class TestDescriptionsUpdated:
    """Tests verifying training descriptions are included."""

    def test_training_descriptions_merged(self):
        """Training descriptions should be merged into SEGMENT_DESCRIPTIONS."""
        from bioimage_mcp_cellpose.descriptions import SEGMENT_DESCRIPTIONS

        training_params = [
            "n_epochs",
            "learning_rate",
            "weight_decay",
            "save_path",
            "model_name",
            "momentum",
            "save_every",
        ]

        for param in training_params:
            assert param in SEGMENT_DESCRIPTIONS, f"Missing training description: {param}"
            # Should not be a generic fallback
            desc = SEGMENT_DESCRIPTIONS[param]
            assert "See Cellpose documentation" not in desc, (
                f"Training param '{param}' has generic description"
            )
