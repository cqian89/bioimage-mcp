from __future__ import annotations

import unittest.mock as mock

import pytest

from bioimage_mcp.registry.engine import DiscoveryEngine
from bioimage_mcp.registry.manifest_schema import DynamicSource, Function, ToolManifest
from bioimage_mcp.registry.static.inspector import (
    StaticCallable,
    StaticModuleReport,
    StaticParameter,
)


@pytest.fixture
def manifest(tmp_path):
    manifest_path = tmp_path / "tool.yaml"
    manifest_path.write_text("tool_id: test.tool\nenv_id: bioimage-mcp-test")
    return ToolManifest(
        manifest_version="0.1.0",
        tool_id="test.tool",
        tool_version="1.0.0",
        env_id="bioimage-mcp-test",
        entrypoint="test_entry.py",
        manifest_path=manifest_path,
        manifest_checksum="abc",
        dynamic_sources=[DynamicSource(adapter="python", prefix="test", modules=["test_mod"])],
    )


def test_discovery_engine_ast_only(manifest):
    engine = DiscoveryEngine()

    # Mock griffe inspector
    mock_report = StaticModuleReport(
        module_name="test_mod",
        callables=[
            StaticCallable(
                name="func1",
                qualified_name="test_mod.func1",
                docstring="Doc 1",
                parameters=[StaticParameter(name="param1", annotation="int", default=None)],
                source="def func1(param1: int): pass",
            )
        ],
    )

    with mock.patch("bioimage_mcp.registry.engine.inspect_module", return_value=mock_report):
        with mock.patch("bioimage_mcp.registry.engine.execute_tool") as mock_execute:
            # Simulate runtime fallback failure or no-op
            mock_execute.return_value = ({}, "", 0)

            functions, warnings = engine.discover(manifest)

            assert len(functions) == 1
            fn = functions[0]
            assert fn.name == "func1"
            assert fn.introspection_source == "ast"
            assert fn.params_schema["properties"]["param1"]["type"] == "integer"
            assert "param1" in fn.params_schema["required"]


def test_discovery_engine_runtime_fallback(manifest):
    engine = DiscoveryEngine()

    # Mock griffe inspector with incomplete info
    mock_report = StaticModuleReport(
        module_name="test_mod",
        callables=[
            StaticCallable(
                name="func1",
                qualified_name="test_mod.func1",
                parameters=[],  # No params in AST
            )
        ],
    )

    # Mock runtime meta.describe result
    runtime_result = {
        "ok": True,
        "result": {
            "params_schema": {
                "type": "object",
                "properties": {"runtime_param": {"type": "string"}},
                "required": ["runtime_param"],
            },
            "tool_version": "1.0.0",
            "introspection_source": "python_api",
        },
    }

    with mock.patch("bioimage_mcp.registry.engine.inspect_module", return_value=mock_report):
        with mock.patch("bioimage_mcp.registry.engine.execute_tool") as mock_execute:
            mock_execute.return_value = (runtime_result, "", 0)

            functions, warnings = engine.discover(manifest)

            assert len(functions) == 1
            fn = functions[0]
            assert fn.introspection_source == "runtime:python_api"
            assert "runtime_param" in fn.params_schema["properties"]


def test_discovery_engine_skip_on_failure(manifest):
    engine = DiscoveryEngine()

    # Mock griffe inspector with no info
    mock_report = StaticModuleReport(
        module_name="test_mod",
        callables=[StaticCallable(name="func1", qualified_name="test_mod.func1", parameters=[])],
    )

    with mock.patch("bioimage_mcp.registry.engine.inspect_module", return_value=mock_report):
        with mock.patch("bioimage_mcp.registry.engine.execute_tool") as mock_execute:
            # Simulate runtime failure
            mock_execute.return_value = ({"ok": False}, "", 1)

            functions, warnings = engine.discover(manifest)

            # Should be skipped because AST was empty and runtime failed
            assert len(functions) == 0


def test_discovery_engine_normalization(manifest):
    engine = DiscoveryEngine()

    # Static function in manifest
    manifest.tool_id = "tools.test"
    manifest.functions = [
        Function(
            fn_id="func_static",
            tool_id="tools.test",
            name="func_static",
            description="Static",
            params_schema={
                "type": "object",
                "properties": {"b": {"type": "int"}, "a": {"type": "int"}},
            },
        )
    ]

    with mock.patch("bioimage_mcp.registry.engine.inspect_module") as mock_inspect:
        mock_inspect.return_value = StaticModuleReport(module_name="test_mod", callables=[])

        functions, warnings = engine.discover(manifest)

        assert len(functions) == 1
        fn = functions[0]
        # fn_id should be prefixed with env name (test)
        assert fn.fn_id == "test.func_static"
        # params_schema should be normalized (sorted keys)
        assert list(fn.params_schema["properties"].keys()) == ["a", "b"]
