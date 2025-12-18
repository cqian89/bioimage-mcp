from __future__ import annotations

from collections.abc import Iterable


def any_tag_matches(function_tags: Iterable[str], required_tags: list[str] | None) -> bool:
    if not required_tags:
        return True
    tag_set = set(function_tags)
    return any(tag in tag_set for tag in required_tags)


def io_type_matches(ports: Iterable[dict], artifact_type: str | None) -> bool:
    if not artifact_type:
        return True
    return any(p.get("artifact_type") == artifact_type for p in ports)
