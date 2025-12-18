from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


def _to_abs_path(value: str | Path) -> Path:
    path = value if isinstance(value, Path) else Path(value)
    path = path.expanduser()
    if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {value}")
    return path


class Config(BaseModel):
    config_version: str = "0.0"

    artifact_store_root: Path
    tool_manifest_roots: list[Path]

    fs_allowlist_read: list[Path] = Field(default_factory=list)
    fs_allowlist_write: list[Path] = Field(default_factory=list)
    fs_denylist: list[Path] = Field(default_factory=list)

    default_pagination_limit: int = 20
    max_pagination_limit: int = 200

    @field_validator(
        "artifact_store_root",
        "tool_manifest_roots",
        "fs_allowlist_read",
        "fs_allowlist_write",
        "fs_denylist",
        mode="before",
    )
    @classmethod
    def _coerce_paths(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            return [_to_abs_path(item) for item in value]
        return _to_abs_path(value)

    @model_validator(mode="after")
    def _validate_limits(self) -> Config:
        if self.default_pagination_limit < 1:
            raise ValueError("default_pagination_limit must be >= 1")
        if self.max_pagination_limit < 1:
            raise ValueError("max_pagination_limit must be >= 1")
        if self.default_pagination_limit > self.max_pagination_limit:
            raise ValueError("default_pagination_limit must be <= max_pagination_limit")
        return self
