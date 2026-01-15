"""Implementation of tttrlib operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import tttrlib


def get_tttr_metadata(tttr: tttrlib.TTTR) -> dict[str, Any]:
    """Extract metadata from a TTTR object."""
    metadata = {
        "n_events": tttr.n_events,
        "n_valid_events": tttr.n_valid_events if hasattr(tttr, "n_valid_events") else None,
    }
    return metadata
