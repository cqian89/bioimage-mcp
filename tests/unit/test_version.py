from __future__ import annotations

from bioimage_mcp import __version__
from bioimage_mcp.version import get_version


def test_version_retrieval() -> None:
    """Test that version is retrieved correctly."""
    version = get_version()
    assert isinstance(version, str)
    assert version == __version__
    # Since we are likely in an editable install or running tests from source,
    # it might return '0.0.0-dev' if not installed, or the actual version if installed.
    # In this environment, let's just ensure it's not empty.
    assert len(version) > 0


def test_version_consistency() -> None:
    """Test that __version__ is consistent."""
    assert __version__ == get_version()
