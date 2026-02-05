from __future__ import annotations

import importlib
import pkgutil
import types
from unittest.mock import MagicMock

from bioimage_mcp.registry.dynamic.adapters.microsam import MicrosamAdapter
from bioimage_mcp.registry.dynamic.models import IOPattern


def test_microsam_adapter_discovery_filtering(monkeypatch):
    """Test that MicrosamAdapter discovers relevant functions and filters out excluded ones."""

    # Define a stub function with docstring
    def segment_from_points(image, points):
        """Segment from points.

        Parameters
        ----------
        image : ndarray
            The input image.
        points : list
            The points.
        """
        pass

    segment_from_points.__module__ = "micro_sam.prompt_based_segmentation"
    segment_from_points.__name__ = "segment_from_points"

    def some_ui_func():
        """UI function that should be excluded."""
        pass

    some_ui_func.__module__ = "micro_sam.sam_annotator"
    some_ui_func.__name__ = "some_ui_func"

    # Mock modules using types.ModuleType so dir() works naturally
    mock_prompt = types.ModuleType("micro_sam.prompt_based_segmentation")
    mock_prompt.segment_from_points = segment_from_points

    mock_annotator = types.ModuleType("micro_sam.sam_annotator")
    mock_annotator.some_ui_func = some_ui_func

    def mock_import(name):
        if name == "micro_sam":
            root = MagicMock()
            root.__name__ = "micro_sam"
            root.__path__ = ["/fake/path"]
            return root
        if name == "micro_sam.prompt_based_segmentation":
            return mock_prompt
        if name == "micro_sam.sam_annotator":
            return mock_annotator
        raise ImportError(f"No module named {name}")

    monkeypatch.setattr(importlib, "import_module", mock_import)

    # Mock walk_packages
    # Returns (importer, name, ispkg)
    mock_walk = [
        (None, "micro_sam.prompt_based_segmentation", False),
        (None, "micro_sam.sam_annotator", True),
    ]
    monkeypatch.setattr(pkgutil, "walk_packages", lambda path, prefix: mock_walk)

    adapter = MicrosamAdapter()
    results = adapter.discover({"prefix": "micro_sam"})

    # Assertions
    fn_ids = [r.fn_id for r in results]

    # Should include prompt_based_segmentation.segment_from_points
    assert "micro_sam.prompt_based_segmentation.segment_from_points" in fn_ids

    # Should EXCLUDE sam_annotator.*
    for fid in fn_ids:
        assert "sam_annotator" not in fid

    # Verify metadata content
    for r in results:
        if r.fn_id == "micro_sam.prompt_based_segmentation.segment_from_points":
            assert r.io_pattern == IOPattern.IMAGE_TO_LABELS
            assert r.description == "Segment from points."
            assert "points" in r.parameters
            assert r.fn_id.startswith("micro_sam.")


def test_microsam_io_pattern_resolution():
    """Test that MicrosamAdapter resolves I/O patterns correctly."""
    adapter = MicrosamAdapter()

    assert (
        adapter.resolve_io_pattern("micro_sam.prompt_based_segmentation.something", None)
        == IOPattern.IMAGE_TO_LABELS
    )
    assert (
        adapter.resolve_io_pattern("micro_sam.instance_segmentation.something", None)
        == IOPattern.IMAGE_TO_LABELS
    )
    assert adapter.resolve_io_pattern("micro_sam.util.something", None) == IOPattern.GENERIC
