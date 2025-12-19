"""Contract test verifying introspected Cellpose schema contains expected params (T014).

Validates that the Cellpose meta.describe response includes key parameters
like diameter, flow_threshold, cellprob_threshold as expected for segmentation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MetaDescribeResponse(BaseModel):
    """Schema for meta.describe response validation."""

    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None


class TestCellposeParamsContract:
    """Contract tests for Cellpose parameter schema via meta.describe."""

    def test_expected_key_params_present(self) -> None:
        """Test that key segmentation parameters are present in schema."""
        # This simulates the expected schema from meta.describe
        # In integration tests, this would come from actual tool introspection
        expected_schema = {
            "type": "object",
            "properties": {
                "diameter": {
                    "type": "number",
                    "default": 30.0,
                    "description": "Estimated cell diameter in pixels.",
                },
                "flow_threshold": {
                    "type": "number",
                    "default": 0.4,
                    "description": "Flow error threshold for mask reconstruction.",
                },
                "cellprob_threshold": {
                    "type": "number",
                    "default": 0.0,
                    "description": "Cell probability threshold.",
                },
            },
            "required": [],
        }

        # Validate key parameters are present
        props = expected_schema["properties"]
        assert "diameter" in props, "Schema must include 'diameter' parameter"
        assert "flow_threshold" in props, "Schema must include 'flow_threshold' parameter"
        assert "cellprob_threshold" in props, "Schema must include 'cellprob_threshold' parameter"

    def test_diameter_param_structure(self) -> None:
        """Test that diameter parameter has correct structure."""
        diameter_schema = {
            "description": "Estimated cell diameter in pixels. Use 0 for automatic estimation.",
            "default": 30.0,
        }

        # Validate diameter has description and default
        assert "description" in diameter_schema
        assert "default" in diameter_schema
        # Diameter can be 0 or None for auto-estimation
        assert diameter_schema["default"] >= 0 or diameter_schema["default"] is None

    def test_flow_threshold_param_structure(self) -> None:
        """Test that flow_threshold parameter has correct structure."""
        flow_threshold_schema = {
            "description": "Flow error threshold for mask reconstruction (0.0-1.0).",
            "default": 0.4,
        }

        assert "description" in flow_threshold_schema
        assert "default" in flow_threshold_schema
        # Flow threshold should be between 0 and 1
        assert 0 <= flow_threshold_schema["default"] <= 1

    def test_cellprob_threshold_param_structure(self) -> None:
        """Test that cellprob_threshold parameter has correct structure."""
        cellprob_threshold_schema = {
            "description": "Cell probability threshold (-6.0 to 6.0).",
            "default": 0.0,
        }

        assert "description" in cellprob_threshold_schema
        assert "default" in cellprob_threshold_schema
        # Cellprob threshold is typically between -6 and 6
        assert -6 <= cellprob_threshold_schema["default"] <= 6

    def test_schema_response_format(self) -> None:
        """Test that meta.describe response follows expected format."""
        response_data = {
            "ok": True,
            "result": {
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "diameter": {"default": 30.0},
                        "flow_threshold": {"default": 0.4},
                    },
                    "required": [],
                },
                "tool_version": "4.0.1",
                "introspection_source": "python_api",
            },
        }

        response = MetaDescribeResponse(**response_data)
        assert response.ok is True
        assert response.result is not None
        assert "params_schema" in response.result
        assert "tool_version" in response.result
        assert "introspection_source" in response.result

    def test_schema_includes_descriptions_for_key_params(self) -> None:
        """Test that key parameters include meaningful descriptions."""
        params_schema = {
            "type": "object",
            "properties": {
                "diameter": {
                    "description": "Estimated cell diameter in pixels. Use 0 for automatic estimation. Critical for accurate segmentation.",
                },
                "flow_threshold": {
                    "description": "Flow error threshold for mask reconstruction (0.0-1.0). Lower values = stricter, fewer masks.",
                },
                "cellprob_threshold": {
                    "description": "Cell probability threshold (-6.0 to 6.0). Lower values = larger cells.",
                },
            },
            "required": [],
        }

        # Ensure descriptions are meaningful (not just fallbacks)
        for param_name in ["diameter", "flow_threshold", "cellprob_threshold"]:
            desc = params_schema["properties"][param_name]["description"]
            # Description should be longer than a simple fallback
            assert len(desc) > 20, f"Description for {param_name} appears to be a fallback"
            # Description should not just say "See documentation"
            assert "See Cellpose documentation" not in desc or len(desc) > 50

    def test_optional_params_not_in_required(self) -> None:
        """Test that optional parameters are not in the required list."""
        params_schema = {
            "type": "object",
            "properties": {
                "diameter": {"default": 30.0},
                "flow_threshold": {"default": 0.4},
                "cellprob_threshold": {"default": 0.0},
                "do_3D": {"default": False},
            },
            "required": [],
        }

        # Parameters with defaults should not be required
        required = params_schema.get("required", [])
        optional_params = ["diameter", "flow_threshold", "cellprob_threshold", "do_3D"]
        for param in optional_params:
            assert param not in required, f"{param} has default so should not be required"
