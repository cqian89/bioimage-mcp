from __future__ import annotations

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.api.server import create_server
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.runs.store import RunStore
from bioimage_mcp.storage.sqlite import connect


def serve(*, stdio: bool) -> int:
    """Start the MCP server using stdio transport."""

    if not stdio:
        raise ValueError("v0.0 supports only --stdio")

    config = load_config()
    conn = connect(config)

    service = DiscoveryService(conn)

    manifests, diagnostics = load_manifests(config.tool_manifest_roots)
    service.clear_diagnostics()
    for diag in diagnostics:
        service.record_diagnostic(diag)

    for manifest in manifests:
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
            service.upsert_function(
                fn_id=fn.fn_id,
                tool_id=fn.tool_id,
                name=fn.name,
                description=fn.description,
                tags=fn.tags,
                inputs=[p.model_dump() for p in fn.inputs],
                outputs=[p.model_dump() for p in fn.outputs],
                params_schema=fn.params_schema,
            )

    artifact_store = ArtifactStore(config, conn=conn)
    run_store = RunStore(config, conn=conn)
    execution = ExecutionService(config, artifact_store=artifact_store, run_store=run_store)
    artifacts = ArtifactsService(artifact_store)

    mcp = create_server(service, execution=execution, artifacts=artifacts)
    mcp.run(transport="stdio")
    return 0
