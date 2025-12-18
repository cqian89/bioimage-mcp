from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class Port(BaseModel):
    name: str
    artifact_type: str
    format: str | None = None
    required: bool = True


class Function(BaseModel):
    fn_id: str
    tool_id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    inputs: list[Port] = Field(default_factory=list)
    outputs: list[Port] = Field(default_factory=list)
    params_schema: dict = Field(default_factory=dict)
    resource_hints: dict | None = None


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

    manifest_path: Path
    manifest_checksum: str

    @field_validator("env_id")
    @classmethod
    def _validate_env_id(cls, value: str) -> str:
        if not value.startswith("bioimage-mcp-"):
            raise ValueError("env_id must start with 'bioimage-mcp-'")
        return value

    @model_validator(mode="after")
    def _fill_defaults(self) -> ToolManifest:
        if not self.name:
            self.name = self.tool_id
        if not self.description:
            self.description = self.tool_id
        return self
