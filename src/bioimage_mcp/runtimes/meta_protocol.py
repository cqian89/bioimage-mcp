from __future__ import annotations

import logging
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class MetaListFunction(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(validation_alias=AliasChoices("id", "fn_id"))
    name: str
    summary: str
    module: str | None = None
    io_pattern: str | None = "generic"


class MetaListResult(BaseModel):
    functions: list[MetaListFunction]
    tool_version: str | None = None
    introspection_source: str | None = None


class MetaListSuccess(BaseModel):
    ok: bool = True
    result: MetaListResult


class MetaDescribeResult(BaseModel):
    params_schema: dict[str, Any]
    tool_version: str
    introspection_source: str
    callable_fingerprint: str | None = None


class MetaDescribeSuccess(BaseModel):
    ok: bool = True
    result: MetaDescribeResult


def extract_result_payload(response: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the result payload from both direct and worker-shaped responses.

    Direct: {ok: true, result: {...}}
    Worker: {command: execute_result, ok: true, outputs: {result: {...}}}
    """
    if not response.get("ok"):
        return None

    # Try direct shape
    result = response.get("result")
    if isinstance(result, dict):
        return result

    # Try worker shape
    outputs = response.get("outputs")
    if isinstance(outputs, dict):
        result = outputs.get("result")
        if isinstance(result, dict):
            return result

    return None


def parse_meta_list_result(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse meta.list response and return normalized function entries.

    Skips invalid entries but does not raise.
    """
    payload = extract_result_payload(response)
    if not payload:
        return []

    functions_raw = payload.get("functions")
    if not isinstance(functions_raw, list):
        return []

    normalized = []
    for entry in functions_raw:
        if not isinstance(entry, dict):
            continue
        try:
            # Validate required fields
            model = MetaListFunction.model_validate(entry)
            data = model.model_dump()
            data.pop("fn_id", None)
            # Propagate top-level source to individual entries if they don't have one (T13.08)
            if "introspection_source" not in data and payload.get("introspection_source"):
                data["introspection_source"] = payload["introspection_source"]
            normalized.append(data)
        except Exception as e:
            logger.warning("Skipping invalid meta.list function entry %s: %s", entry, e)
            continue

    return normalized


def parse_meta_describe_result(response: dict[str, Any]) -> dict[str, Any] | None:
    """Parse meta.describe response and return normalized result.

    Returns {params_schema, tool_version, introspection_source} or None.
    """
    payload = extract_result_payload(response)
    if not payload:
        return None

    try:
        model = MetaDescribeResult.model_validate(payload)
        return model.model_dump()
    except Exception as e:
        logger.warning("Invalid meta.describe payload: %s", e)
        return None
