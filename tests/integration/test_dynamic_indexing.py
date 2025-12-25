"""Test that dynamic functions are indexed with introspection_source."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.registry.manifest_schema import Function, Port, ToolManifest
from bioimage_mcp.storage.sqlite import init_schema


def test_dynamic_function_introspection_source_stored_in_db(tmp_path: Path) -> None:
    """Test that functions with introspection_source='dynamic' are indexed correctly.

    This follows the serve.py pattern of loading manifests and indexing functions.
    Since T007 (loader.py) now adds dynamic functions to manifest.functions,
    they should be indexed with their introspection_source field preserved.
    """
    # Setup: In-memory SQLite DB
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    service = DiscoveryService(conn)

    # Create a manifest with a dynamic function (simulating what loader.py does)
    manifest = ToolManifest(
        manifest_version="1.0",
        tool_id="test-dynamic-tool",
        tool_version="0.1.0",
        name="Test Dynamic Tool",
        description="Tool with dynamically discovered functions",
        env_id="bioimage-mcp-test",
        entrypoint="test_entry.py",
        functions=[
            Function(
                fn_id="test.dynamic_func",
                tool_id="test-dynamic-tool",
                name="dynamic_func",
                description="A dynamically discovered function",
                tags=["test", "dynamic"],
                inputs=[Port(name="input", artifact_type="BioImageRef")],
                outputs=[Port(name="output", artifact_type="BioImageRef")],
                params_schema={"type": "object", "properties": {}},
                introspection_source="dynamic",  # Key field for dynamic functions
            )
        ],
        manifest_path=tmp_path / "manifest.yaml",
        manifest_checksum="abc123",
    )

    # Simulate serve.py indexing logic (lines 34-54 in serve.py)
    service.upsert_tool(
        tool_id=manifest.tool_id,
        name=manifest.name,
        description=manifest.description,
        tool_version=manifest.tool_version,
        env_id=manifest.env_id,
        manifest_path=str(manifest.manifest_path),
        available=True,
        installed=True,
    )

    for fn in manifest.functions:
        # This is the actual call from serve.py (T007c added introspection_source)
        service.upsert_function(
            fn_id=fn.fn_id,
            tool_id=fn.tool_id,
            name=fn.name,
            description=fn.description,
            tags=fn.tags,
            inputs=[p.model_dump() for p in fn.inputs],
            outputs=[p.model_dump() for p in fn.outputs],
            params_schema=fn.params_schema,
            introspection_source=fn.introspection_source,
        )

    # Verify: Query DB directly to check introspection_source is stored
    row = conn.execute(
        "SELECT introspection_source FROM functions WHERE fn_id = ?",
        ("test.dynamic_func",),
    ).fetchone()

    assert row is not None, "Function should be in DB"

    # T007c passes introspection_source, so it should be stored correctly
    assert row["introspection_source"] == "dynamic", (
        "introspection_source should be 'dynamic' for dynamically discovered functions"
    )
