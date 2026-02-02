from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class StoragePolicy(BaseModel):
    """Configuration for storage retention and quota policies."""

    retention_days: int = Field(default=14, ge=1)
    quota_bytes: int = Field(default=100 * 1024**3, ge=1)

    # Thresholds
    warn_fraction: float = Field(default=0.8, gt=0, le=1.0)
    trigger_fraction: float = Field(default=1.0, gt=0, le=1.0)
    target_fraction: float = Field(default=0.8, gt=0, le=1.0)

    # Scheduling
    check_interval_seconds: int = Field(default=900, ge=1)
    cooldown_seconds: int = Field(default=900, ge=1)

    # Safety
    protect_recent_sessions: int = Field(default=1, ge=1)
    ignore_fs_newer_than_seconds: int = Field(default=300, ge=1)

    # Behavior
    delete_order: Literal["oldest_first"] = "oldest_first"

    @model_validator(mode="after")
    def _validate_thresholds(self) -> StoragePolicy:
        if not (0 < self.warn_fraction < self.trigger_fraction <= 1.0):
            raise ValueError(
                f"Thresholds must satisfy 0 < warn_fraction ({self.warn_fraction}) < "
                f"trigger_fraction ({self.trigger_fraction}) <= 1.0"
            )
        if not (0 < self.target_fraction <= self.warn_fraction):
            raise ValueError(
                f"Target fraction must satisfy 0 < target_fraction ({self.target_fraction}) <= "
                f"warn_fraction ({self.warn_fraction})"
            )
        return self
