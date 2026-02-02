from __future__ import annotations

import json
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.storage.sqlite import connect
from bioimage_mcp.storage.manager import StorageManager


def status(*, json_output: bool) -> int:
    config = load_config()
    conn = connect(config)
    manager = StorageManager(config, conn)

    total_bytes = manager.get_total_bytes()
    quota_bytes = manager.get_quota_bytes()
    usage_fraction = manager.get_usage_fraction()
    usage_percent = usage_fraction * 100

    warn_threshold = 0.8
    is_warning = usage_fraction >= warn_threshold

    # Get last cleanup event
    last_event_row = conn.execute(
        "SELECT * FROM cleanup_events ORDER BY ended_at DESC LIMIT 1"
    ).fetchone()

    last_event = None
    if last_event_row:
        last_event = dict(last_event_row)
        if last_event["notes_json"]:
            last_event["notes"] = json.loads(last_event["notes_json"])
            del last_event["notes_json"]
        last_event["dry_run"] = bool(last_event["dry_run"])

    data = {
        "total_bytes": total_bytes,
        "quota_bytes": quota_bytes,
        "usage_fraction": usage_fraction,
        "usage_percent": usage_percent,
        "warn_threshold": warn_threshold,
        "is_warning": is_warning,
        "retention_days": config.storage.retention_days,
        "last_cleanup": last_event,
    }

    if json_output:
        print(json.dumps(data, indent=2))
        return 0

    print("Storage Status:")
    print(
        f"  Usage: {total_bytes / (1024**3):.2f} GB / {quota_bytes / (1024**3):.2f} GB ({usage_percent:.1f}%)"
    )
    if is_warning:
        print(f"  WARNING: Storage usage is above {warn_threshold * 100:.0f}% threshold!")
    print(f"  Retention Policy: {config.storage.retention_days} days")

    if last_event:
        print("\nLast Cleanup Event:")
        print(f"  Time: {last_event['ended_at']}")
        print(f"  Reason: {last_event['reason']}")
        print(f"  Deleted: {last_event['deleted_count']} artifacts")
        print(f"  Freed: {last_event['freed_bytes'] / (1024**2):.2f} MB")
        if last_event["dry_run"]:
            print("  (Dry Run - no files actually deleted)")
    else:
        print("\nLast Cleanup Event: None")

    return 0
