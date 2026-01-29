from __future__ import annotations


def summarize_docstring(docstring: str | None) -> str:
    if not docstring:
        return ""
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped:
            return " ".join(stripped.split())
    return ""
