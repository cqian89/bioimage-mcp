from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from bioimage_mcp.api.schemas import FunctionHints
from bioimage_mcp.registry.dynamic.models import IOPattern


class InterchangeFormat(StrEnum):
    """Canonical interchange formats for bioimaging data."""

    OME_TIFF = "OME-TIFF"
    OME_ZARR = "OME-Zarr"


def validate_interchange_format(value: str | None, artifact_type: str | None = None) -> str | None:
    """Validate and canonicalize interchange format.

    If artifact_type is provided, validation only applies to image types.
    """
    if value is None:
        return None

    # Only validate format for image artifact types if artifact_type is known
    if artifact_type is not None and artifact_type not in (
        "BioImageRef",
        "LabelImageRef",
    ):
        return value

    try:
        # Validate against InterchangeFormat enum
        return InterchangeFormat(value).value
    except ValueError:
        valid_values = [f.value for f in InterchangeFormat]
        suffix = f" for artifact_type '{artifact_type}'" if artifact_type else ""
        raise ValueError(
            f"Invalid format '{value}'{suffix}. Must be one of: {', '.join(valid_values)}"
        ) from None


class Port(BaseModel):
    name: str
    artifact_type: str
    description: str | None = None
    format: str | None = None
    required: bool = True

    @model_validator(mode="after")
    def _validate_format_for_image_types(self) -> Port:
        """Only validate format for image artifact types."""
        self.format = validate_interchange_format(self.format, self.artifact_type)
        return self


class Function(BaseModel):
    """Function definition within a tool manifest.

    The params_schema can be minimal in the manifest; full schema is
    fetched on-demand via the meta.describe protocol.
    """

    fn_id: str
    tool_id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    inputs: list[Port] = Field(default_factory=list)
    outputs: list[Port] = Field(default_factory=list)
    params_schema: dict = Field(default_factory=dict)
    hints: FunctionHints | None = None
    resource_hints: dict | None = None
    introspection_source: str | None = Field(
        default=None,
        description=(
            "How params_schema was derived: "
            "'python_api', 'argparse', 'manual', or None if from manifest"
        ),
    )
    input_mode: Literal["path", "numpy", "xarray"] = Field(
        default="numpy",
        description=(
            "How input artifacts should be resolved: "
            "'path' (file path), 'numpy' (numpy array via BioImage.data), "
            "or 'xarray' (xarray.DataArray via BioImage.xarray_data)"
        ),
    )


class FunctionOverlay(BaseModel):
    """Override/supplement fields for a dynamically discovered function."""

    fn_id: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    io_pattern: IOPattern | None = None
    hints: FunctionHints | None = None
    params_override: dict[str, dict[str, Any]] | None = None


class DynamicSource(BaseModel):
    """Configuration for dynamically discovering functions from a library."""

    adapter: str
    prefix: str
    modules: list[str]
    include_patterns: list[str] = Field(default_factory=lambda: ["*"])
    exclude_patterns: list[str] = Field(default_factory=lambda: ["_*", "test_*"])


class ToolManifest(BaseModel):
    manifest_version: str
    tool_id: str
    tool_version: str
    name: str = ""
    description: str = ""

    env_id: str
    entrypoint: str
    python_version: str | None = None
    platforms_supported: list[str] = Field(default_factory=list)
    functions: list[Function] = Field(default_factory=list)
    dynamic_sources: list[DynamicSource] = Field(default_factory=list)
    function_overlays: dict[str, FunctionOverlay] = Field(default_factory=dict)

    manifest_path: Path
    manifest_checksum: str

    @field_validator("env_id")
    @classmethod
    def _validate_env_id(cls, value: str) -> str:
        if not value.startswith("bioimage-mcp-"):
            raise ValueError("env_id must start with 'bioimage-mcp-'")
        return value

    @model_validator(mode="before")
    @classmethod
    def _fill_overlay_fn_ids(cls, data: Any) -> Any:
        """Fill fn_id in function_overlays from dict keys if missing."""
        if isinstance(data, dict) and "function_overlays" in data:
            overlays = data["function_overlays"]
            if isinstance(overlays, dict):
                for fn_id, overlay in overlays.items():
                    if isinstance(overlay, dict) and "fn_id" not in overlay:
                        overlay["fn_id"] = fn_id
        return data

    @model_validator(mode="after")
    def _validate_unique_prefixes(self) -> ToolManifest:
        """Ensure dynamic_sources have unique prefixes."""
        if self.dynamic_sources:
            prefixes = [ds.prefix for ds in self.dynamic_sources]
            seen = set()
            duplicates = set()
            for prefix in prefixes:
                if prefix in seen:
                    duplicates.add(prefix)
                seen.add(prefix)
            if duplicates:
                raise ValueError(
                    f"Dynamic source prefixes must be unique. "
                    f"Duplicate prefix(es): {', '.join(sorted(duplicates))}"
                )
        return self

    @model_validator(mode="after")
    def _fill_defaults(self) -> ToolManifest:
        if not self.name:
            self.name = self.tool_id
        if not self.description:
            self.description = self.tool_id
        return self


class FunctionResponse(BaseModel):
    """Function details returned to clients via describe_function."""

    model_config = {"populate_by_name": True}
    fn_id: str
    params_schema: dict = Field(alias="schema")
    introspection_source: str | None = None
    inputs: dict | None = None
    outputs: dict | None = None
    hints: dict | None = None

    @model_validator(mode="after")
    def _validate_schema(self) -> FunctionResponse:
        schema = self.params_schema or {}
        if not isinstance(schema, dict) or schema.get("type") != "object":
            raise ValueError("schema must be a JSON object schema")
        return self
