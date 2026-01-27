from __future__ import annotations

import pathlib
import tempfile
import textwrap

import pytest

from bioimage_mcp.registry.static import (
    callable_fingerprint,
    inspect_module,
    normalize_json_schema,
)


def test_callable_fingerprint_stability():
    source = "def foo(x): return x + 1"
    fp1 = callable_fingerprint(source)
    fp2 = callable_fingerprint(source)
    assert fp1 == fp2
    assert len(fp1) == 64  # sha256 hex length

    source_changed = "def foo(x): return x + 2"
    fp3 = callable_fingerprint(source_changed)
    assert fp1 != fp3


def test_normalize_json_schema_ordering():
    schema = {
        "type": "object",
        "required": ["b", "a"],
        "properties": {
            "z": {"type": "string"},
            "y": {"type": "integer"},
        },
    }
    normalized = normalize_json_schema(schema)

    # Check key ordering in properties
    keys = list(normalized["properties"].keys())
    assert keys == ["y", "z"]

    # Check 'required' list ordering
    assert normalized["required"] == ["a", "b"]

    # Check top-level keys
    assert list(normalized.keys()) == ["properties", "required", "type"]


def test_inspect_module_no_import():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        module_path = tmp_path / "my_tool.py"
        module_path.write_text(
            textwrap.dedent(
                """
            def add_numbers(a: int, b: int = 0) -> int:
                \"\"\"Adds two numbers.\"\"\"
                return a + b
            
            class MyClass:
                def method(self):
                    pass
            """
            )
        )

        # Ensure we can find the module in the temp dir
        report = inspect_module("my_tool", search_paths=[tmp_path])

        assert report.module_name == "my_tool"
        # Find add_numbers
        add_fn = next((c for c in report.callables if c.name == "add_numbers"), None)
        assert add_fn is not None
        assert add_fn.qualified_name == "my_tool.add_numbers"
        assert "Adds two numbers." in add_fn.docstring

        # Check parameters
        params = {p.name: p for p in add_fn.parameters}
        assert "a" in params
        assert params["a"].annotation == "int"
        assert params["a"].default is None

        assert "b" in params
        assert params["b"].annotation == "int"
        assert params["b"].default == "0"

        # Verify it didn't actually import it into sys.modules
        import sys

        assert "my_tool" not in sys.modules
