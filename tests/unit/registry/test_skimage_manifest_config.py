"""
Unit tests for SkimageAdapter manifest configuration.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from bioimage_mcp.registry.loader import load_manifest_file


def test_skimage_adapter_discovery_via_manifest(tmp_path):
    """Test that SkimageAdapter is used when configured in manifest."""
    # Create temp manifest
    manifest_path = tmp_path / "manifest.yaml"
    manifest_data = {
        "manifest_version": "0.0",
        "tool_id": "test.tool",
        "tool_version": "0.1.0",
        "name": "Test Tool",
        "description": "Test Tool",
        "env_id": "bioimage-mcp-test",
        "entrypoint": "test_entrypoint",
        "dynamic_sources": [
            {
                "adapter": "skimage",
                "prefix": "skimage",
                "modules": ["skimage.filters"],
            }
        ],
    }
    manifest_path.write_text(yaml.dump(manifest_data))

    # Mock importlib to simulate skimage installed
    mock_module = MagicMock()
    # Add a dummy function to the mock module
    mock_gaussian = MagicMock()
    mock_gaussian.__name__ = "gaussian"
    # Ensure introspector can read signature (or mock introspector)
    # But adapter uses introspector. simpler to mock introspection?
    # Let's mock importlib.import_module to return our mock

    with patch("importlib.import_module", return_value=mock_module) as mock_import:
        # We need dir(module) to return ['gaussian']
        mock_module.__dir__ = MagicMock(return_value=["gaussian"])
        # And getattr(module, 'gaussian') -> mock_gaussian
        mock_module.gaussian = mock_gaussian

        # We also need to ensure 'skimage' adapter is in registry.
        # Since it is NOT, discovery should fail/skip (and we verify that failure).
        # Actually, loader.py catches exceptions.
        # But if adapter is missing, it raises ValueError in discovery.py?
        # Check discovery.py:
        # if source.adapter not in adapter_registry: raise ValueError
        # loader.py catches Exception and continues.
        # So manifest loading succeeds, but NO functions discovered.

        manifest, diag = load_manifest_file(manifest_path)

        assert manifest is not None
        assert diag is None

        # Check for discovered function
        function_ids = [f.fn_id for f in manifest.functions]

        # Since adapter is not registered, this list should NOT contain skimage.filters.gaussian
        # Wait, the task is to write a failing test?
        # If I assert it IS present, it will fail. That's the goal.

        assert "skimage.filters.gaussian" in function_ids
