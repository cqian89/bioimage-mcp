from __future__ import annotations

import builtins
import importlib
import sys


def test_engine_import_does_not_require_griffe(monkeypatch) -> None:
    original_import = builtins.__import__

    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "griffe":
            raise ModuleNotFoundError("No module named 'griffe'")
        return original_import(name, globals, locals, fromlist, level)

    sys.modules.pop("bioimage_mcp.registry.engine", None)
    sys.modules.pop("bioimage_mcp.registry.static.inspector", None)
    monkeypatch.setattr(builtins, "__import__", _guarded_import)

    engine = importlib.import_module("bioimage_mcp.registry.engine")

    assert engine.DiscoveryEngine.parameters_to_json_schema({}) == {
        "type": "object",
        "properties": {},
    }
