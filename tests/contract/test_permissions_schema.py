from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from bioimage_mcp.api import schemas


class PermissionModeModel(BaseModel):
    mode: schemas.PermissionMode = schemas.PermissionMode.INHERIT


class OverwritePolicyModel(BaseModel):
    policy: schemas.OverwritePolicy = schemas.OverwritePolicy.ASK


def test_permission_mode_schema_values_and_default() -> None:
    schema = PermissionModeModel.model_json_schema()
    mode_schema = schema["properties"]["mode"]
    defs = schema["$defs"]

    assert defs["PermissionMode"]["enum"] == ["explicit", "inherit", "hybrid"]
    assert mode_schema["default"] == "inherit"


def test_overwrite_policy_schema_values_and_default() -> None:
    schema = OverwritePolicyModel.model_json_schema()
    policy_schema = schema["properties"]["policy"]
    defs = schema["$defs"]

    assert defs["OverwritePolicy"]["enum"] == ["allow", "deny", "ask"]
    assert policy_schema["default"] == "ask"


def test_permission_decision_required_fields_and_types() -> None:
    schema = schemas.PermissionDecision.model_json_schema()
    required = set(schema["required"])

    assert required == {"operation", "path", "decision", "timestamp"}
    assert schema["properties"]["operation"]["enum"] == ["read", "write"]
    assert schema["properties"]["path"]["type"] == "string"
    assert schema["properties"]["decision"]["enum"] == ["ALLOWED", "DENIED", "ASK"]
    assert schema["properties"]["timestamp"]["format"] == "date-time"

    decision = schemas.PermissionDecision(
        operation="read",
        path="/tmp/example.txt",
        decision="ALLOWED",
        timestamp=datetime.now(tz=timezone.utc),
    )

    assert decision.operation == "read"
    assert decision.path == "/tmp/example.txt"
    assert decision.decision == "ALLOWED"
    assert isinstance(decision.timestamp, datetime)
