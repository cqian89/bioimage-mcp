from __future__ import annotations

import json
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.storage.sqlite import connect


def pin(ref_id: str, *, unpin: bool, json_output: bool) -> int:
    config = load_config()
    conn = connect(config)

    # Check if artifact exists
    row = conn.execute(
        "SELECT ref_id, pinned FROM artifacts WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if not row:
        if json_output:
            print(json.dumps({"error": "NOT_FOUND", "ref_id": ref_id}))
        else:
            print(f"Error: Artifact {ref_id} not found.")
        return 1

    pinned_val = 0 if unpin else 1
    conn.execute("UPDATE artifacts SET pinned = ? WHERE ref_id = ?", (pinned_val, ref_id))
    conn.commit()

    status = "unpinned" if unpin else "pinned"
    if json_output:
        print(json.dumps({"status": status, "ref_id": ref_id}))
    else:
        print(f"Artifact {ref_id} {status} successfully.")

    return 0
