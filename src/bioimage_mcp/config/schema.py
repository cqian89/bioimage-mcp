from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


def _to_abs_path(value: str | Path) -> Path:
    path = value if isinstance(value, Path) else Path(value)
    path = path.expanduser()
    if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {value}")
    return path


class PermissionMode(str, Enum):
    """How to interpret file access permissions."""

    EXPLICIT = "explicit"
    INHERIT = "inherit"
    HYBRID = "hybrid"


class OverwritePolicy(str, Enum):
    """How to handle overwriting existing files."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionSettings(BaseModel):
    """Configuration for file access behavior."""

    mode: PermissionMode = PermissionMode.INHERIT
    on_overwrite: OverwritePolicy = OverwritePolicy.ASK


class AgentGuidance(BaseModel):
    """Configuration for agent-facing guidance."""

    warn_unactivated: bool = True


class Config(BaseModel):
    config_version: str = "0.0"

    artifact_store_root: Path
    tool_manifest_roots: list[Path]
    schema_cache_path: Path | None = None

    fs_allowlist_read: list[Path] = Field(default_factory=list)
    fs_allowlist_write: list[Path] = Field(default_factory=list)
    fs_denylist: list[Path] = Field(default_factory=list)

    permissions: PermissionSettings = Field(default_factory=PermissionSettings)
    agent_guidance: AgentGuidance = Field(default_factory=AgentGuidance)

    default_pagination_limit: int = 20
    max_pagination_limit: int = 200
    session_ttl_hours: int = 24

    # Worker process settings
    worker_timeout_seconds: int = 600  # Maximum time for a single operation
    max_workers: int = 8  # Maximum number of concurrent worker processes
    session_timeout_seconds: int = 1800  # Idle timeout before worker shutdown (30 min)

    @field_validator(
        "artifact_store_root",
        "tool_manifest_roots",
        "schema_cache_path",
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
        if self.session_ttl_hours < 1:
            raise ValueError("session_ttl_hours must be >= 1")
        if self.worker_timeout_seconds < 1:
            raise ValueError("worker_timeout_seconds must be >= 1")
        if self.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if self.session_timeout_seconds < 1:
            raise ValueError("session_timeout_seconds must be >= 1")
        return self
