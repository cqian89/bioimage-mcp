#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

ARTIFACTS_DIR="$WORK_DIR/artifacts"
EXPORTS_DIR="$WORK_DIR/exports"
DATA_DIR="$WORK_DIR/data"

mkdir -p "$ARTIFACTS_DIR" "$EXPORTS_DIR" "$DATA_DIR" "$WORK_DIR/.bioimage-mcp"

TOOL_ROOT="$REPO_ROOT/tools/builtin"
if [[ ! -d "$TOOL_ROOT" ]]; then
  echo "Expected builtin tool directory at $TOOL_ROOT" >&2
  exit 1
fi

SAMPLE_IMAGE="${BIOIMAGE_MCP_SAMPLE_IMAGE:-}"
SAMPLE_PARENT=""
if [[ -n "$SAMPLE_IMAGE" ]]; then
  if [[ ! -f "$SAMPLE_IMAGE" ]]; then
    echo "BIOIMAGE_MCP_SAMPLE_IMAGE is not a file: $SAMPLE_IMAGE" >&2
    exit 1
  fi
  SAMPLE_PARENT="$(cd "$(dirname "$SAMPLE_IMAGE")" && pwd)"
fi

cat >"$WORK_DIR/.bioimage-mcp/config.yaml" <<EOF
artifact_store_root: $ARTIFACTS_DIR
tool_manifest_roots:
  - $TOOL_ROOT
fs_allowlist_read:
  - $DATA_DIR
EOF

if [[ -n "$SAMPLE_PARENT" ]]; then
  cat >>"$WORK_DIR/.bioimage-mcp/config.yaml" <<EOF
  - $SAMPLE_PARENT
EOF
fi

cat >>"$WORK_DIR/.bioimage-mcp/config.yaml" <<EOF
fs_allowlist_write:
  - $ARTIFACTS_DIR
  - $EXPORTS_DIR
fs_denylist:
  - /etc
  - /proc
EOF

echo "Workspace: $WORK_DIR"
echo "Config: $WORK_DIR/.bioimage-mcp/config.yaml"

echo "---"
echo "1) doctor"
set +e
(
  cd "$WORK_DIR"
  python -m bioimage_mcp doctor
)
DOCTOR_EXIT=$?
set -e
if [[ $DOCTOR_EXIT -ne 0 ]]; then
  echo "doctor reported NOT READY (exit=$DOCTOR_EXIT); continuing validation" >&2
fi

echo "---"
echo "2) discovery (list/search/describe)"
(
  cd "$WORK_DIR"
  python - <<'PY'
from __future__ import annotations

from bioimage_mcp.api.discovery import DiscoveryService
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.storage.sqlite import connect

config = load_config()
conn = connect(config)
service = DiscoveryService(conn)

manifests, diagnostics = load_manifests(config.tool_manifest_roots)
service.clear_diagnostics()
for d in diagnostics:
    service.record_diagnostic(d)

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

tools_page = service.list_tools(limit=20, cursor=None)
assert tools_page["tools"], "expected at least one tool"

search_page = service.search_functions(query="blur", limit=20, cursor=None)
assert search_page["functions"], "expected at least one matching function"

fn_id = search_page["functions"][0]["fn_id"]
described = service.describe_function(fn_id)
assert described.get("fn_id") == fn_id
assert described.get("schema")

print("discovery ok")
PY
)

echo "---"
echo "3) execution (optional)"
if [[ -z "$SAMPLE_IMAGE" ]]; then
  echo "Skipping execution: set BIOIMAGE_MCP_SAMPLE_IMAGE=/absolute/path/to/image" >&2
  exit 0
fi

(
  cd "$WORK_DIR"
  python - <<PY
from __future__ import annotations

from pathlib import Path

from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.runs.store import RunStore
from bioimage_mcp.storage.sqlite import connect

config = load_config()
conn = connect(config)
store = ArtifactStore(config, conn=conn)
runs = RunStore(config, conn=conn)
execution = ExecutionService(config, artifact_store=store, run_store=runs)
artifacts = ArtifactsService(store)

sample = Path("$SAMPLE_IMAGE").absolute()
image_ref = {
    "type": "BioImageRef",
    "uri": sample.as_uri(),
    "format": "unknown",
    "mime_type": "application/octet-stream",
    "size_bytes": sample.stat().st_size,
    "checksums": [],
    "created_at": "",
    "metadata": {},
}

convert = execution.run_workflow(
    {
        "steps": [{"fn_id": "builtin.convert_to_ome_zarr", "params": {}, "inputs": {"image": image_ref}}],
        "run_opts": {},
    }
)
status = execution.get_run_status(convert["run_id"])
assert status["status"] == "succeeded", status
out_ref = status["outputs"]["image"]

meta = artifacts.get_artifact(out_ref["ref_id"])  # metadata-only
assert meta["ref"]["checksums"], meta

export_dest = Path("$EXPORTS_DIR") / "converted.ome.zarr"
artifacts.export_artifact(out_ref["ref_id"], str(export_dest))
assert export_dest.exists()

print("execution ok")
PY
)
