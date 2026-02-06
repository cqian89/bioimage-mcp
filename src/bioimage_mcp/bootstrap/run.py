from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config


def run(
    tool_id: str,
    params: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    session_id: str = "cli-session",
    json_output: bool = False,
) -> int:
    """Run a tool via the ExecutionService."""
    config = Config.load()
    params = params or {}
    inputs = inputs or {}

    # Process inputs: if they look like file paths, wrap them in BioImageRef
    processed_inputs = {}
    for k, v in inputs.items():
        if isinstance(v, str) and (v.startswith("file://") or Path(v).exists()):
            path = Path(v.replace("file://", ""))
            # Basic BioImageRef wrapper for CLI convenience
            processed_inputs[k] = {
                "type": "BioImageRef",
                "uri": path.absolute().as_uri(),
                "format": "OME-TIFF" if path.suffix.lower() in [".tif", ".tiff"] else "OME-Zarr",
            }
        else:
            processed_inputs[k] = v

    spec = {
        "steps": [
            {
                "id": tool_id,
                "params": params,
                "inputs": processed_inputs,
            }
        ]
    }

    try:
        with ExecutionService(config) as service:
            result = service.run_workflow(spec, session_id=session_id)

            if json_output:
                print(json.dumps(result, indent=2, default=str))
            else:
                if result.get("status") == "succeeded":
                    print(f"Run succeeded: {result.get('run_id')}")
                    outputs = result.get("outputs", {})
                    if outputs:
                        print("\nOutputs:")
                        for name, out in outputs.items():
                            print(f"  {name}: {out.get('ref_id')} ({out.get('type')})")
                else:
                    print(f"Run failed: {result.get('status')}", file=sys.stderr)
                    error = result.get("error")
                    if error:
                        print(f"Error: {error.get('message')}", file=sys.stderr)
                        if error.get("details"):
                            print(f"Details: {error.get('details')}", file=sys.stderr)
                    return 1

            return 0
    except Exception as e:
        if json_output:
            print(json.dumps({"ok": False, "error": str(e)}))
        else:
            print(f"Error executing tool: {e}", file=sys.stderr)
        return 1
