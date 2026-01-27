from __future__ import annotations

import hashlib


def callable_fingerprint(source_text: str) -> str:
    """Returns sha256 hex digest of the source text; stable across runs."""
    if not source_text:
        return ""
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()
