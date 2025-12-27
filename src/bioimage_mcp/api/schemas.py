from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

AxisName = Annotated[str, Field(pattern="^[A-Z]$")]
ArtifactType = Literal[
    "BioImageRef",
    "LabelImageRef",
    "TableRef",
    "LogRef",
    "NativeOutputRef",
]
StorageType = Literal["file", "zarr-temp"]


class InputRequirement(BaseModel):
    """Schema for a single input requirement."""

    type: ArtifactType
    required: bool = True
    description: str
    expected_axes: list[AxisName] | None = None
    preprocessing_hint: str | None = None
    supported_storage_types: list[StorageType] | None = None


class OutputDescription(BaseModel):
    """Schema for a single output description."""

    type: ArtifactType
    description: str


class NextStepHint(BaseModel):
    """Suggested next step in workflow."""

    fn_id: str
    reason: str
    required_inputs: list[str] | None = None


class SuggestedFix(BaseModel):
    """Suggested fix for an error."""

    fn_id: str
    params: dict
    explanation: str


class SuccessHints(BaseModel):
    """Hints returned on successful execution."""

    next_steps: list[NextStepHint] = Field(default_factory=list)
    common_issues: list[str] = Field(default_factory=list)


class ErrorHints(BaseModel):
    """Hints returned on error."""

    diagnosis: str | None = None
    suggested_fix: SuggestedFix | None = None
    related_metadata: dict | None = None


class FunctionHints(BaseModel):
    """Hints defined per-function in manifest.yaml."""

    inputs: dict[str, InputRequirement] = Field(default_factory=dict)
    outputs: dict[str, OutputDescription] = Field(default_factory=dict)
    success_hints: SuccessHints | None = None
    error_hints: dict[str, ErrorHints] = Field(default_factory=dict)


class LLMHints(FunctionHints):
    """Structured hints for LLM workflow guidance."""
