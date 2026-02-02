from __future__ import annotations

import json

from bioimage_mcp.config.loader import load_config
from bioimage_mcp.storage.cleanup import maybe_cleanup, run_cleanup
from bioimage_mcp.storage.sqlite import connect


def cleanup(*, dry_run: bool, json_output: bool, force: bool) -> int:
    config = load_config()
    conn = connect(config)

    if dry_run or force:
        # Override cooldown and lock by calling run_cleanup directly for dry-runs or forced runs
        summary = run_cleanup(config, conn, reason="manual", dry_run=dry_run)
    else:
        # maybe_cleanup respects cooldown and lock unless we're forced
        summary = maybe_cleanup(config, conn, reason="manual", force=False)
        if summary is None:
            # maybe_cleanup returned None because of cooldown or lock
            if json_output:
                print(json.dumps({"status": "skipped", "reason": "cooldown_or_locked"}))
            else:
                print(
                    "Cleanup skipped (cooldown active or another cleanup running). Use --force to override."
                )
            return 0

    # If we reached here, a cleanup (real or dry-run) actually ran
    if json_output:
        print(json.dumps(summary, indent=2))
        return 0

    print("Cleanup Summary:")
    print(f"  Reason: {summary['reason']}")
    print(f"  Dry Run: {summary['dry_run']}")
    print(f"  Deleted: {summary['deleted_count']} artifacts")
    print(f"  Freed: {summary['freed_bytes'] / (1024**2):.2f} MB")
    print(
        f"  Storage: {summary['before_bytes'] / (1024**3):.2f} GB -> {summary['after_bytes'] / (1024**3):.2f} GB"
    )

    if summary["notes"]:
        print("\nNotes:")
        for note in summary["notes"]:
            print(f"  - {note}")

    return 0
