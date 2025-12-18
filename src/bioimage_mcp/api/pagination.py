from __future__ import annotations

import base64
import json
from typing import Any

from bioimage_mcp.config.schema import Config


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid cursor") from exc
    if not isinstance(obj, dict):
        raise ValueError("Invalid cursor")
    return obj


def resolve_limit(limit: int | None, config: Config) -> int:
    if limit is None:
        return config.default_pagination_limit
    if limit < 1:
        return 1
    return min(limit, config.max_pagination_limit)
