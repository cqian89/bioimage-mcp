from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field


class StepAssertion(BaseModel):
    """Assertion for a workflow step output."""

    type: Literal["artifact_exists", "output_type", "metadata_check"]
    key: str | None = None
    value: Any = None


class WorkflowStep(BaseModel):
    """Single step in a workflow test case."""

    step_id: str = Field(..., pattern=r"^[a-z_][a-z0-9_]*$")
    id: str = Field(
        validation_alias=AliasChoices("id", "fn_id"),
        serialization_alias="id",
        pattern=r"^[a-z_]+(\.[a-z0-9_]+)+$",
    )
    inputs: dict[str, str | dict] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    assertions: list[StepAssertion] = Field(default_factory=list)


class WorkflowTestCase(BaseModel):
    """Workflow test case definition loaded from YAML."""

    test_name: str = Field(..., pattern=r"^[a-z_][a-z0-9_]*$")
    description: str
    mock_mode: bool = False
    steps: list[WorkflowStep]


class StepContext(BaseModel):
    """Runtime context tracking step outputs."""

    outputs: dict[str, dict] = Field(default_factory=dict)

    def resolve_reference(self, ref: str) -> dict:
        """Resolve a {step_id.output} reference to an artifact ref."""
        if not ref.startswith("{") or not ref.endswith("}"):
            return {"uri": f"file://{ref}"}
        inner = ref[1:-1]
        step_id, _ = inner.rsplit(".", 1)
        return self.outputs[step_id]
