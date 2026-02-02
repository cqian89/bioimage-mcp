# Phase 18: Implement artifact store retention and quota management - Research

**Researched:** 2026-02-02
**Domain:** Storage Management, Retention Policies, SQLite Quota Enforcement
**Confidence:** HIGH

## Summary

This research investigates strategies for implementing artifact retention and quota management in the `bioimage-mcp` ecosystem. The core requirement is to prevent unbounded storage growth by implementing time-based deletion and global storage quotas while preserving active session data and pinned artifacts.

The standard approach for this domain involves a combination of:
1. **Metadata-driven cleanup**: Using SQLite to track artifact age, size, and session affinity.
2. **Quota enforcement**: Using SQLite triggers or application-level checks to monitor aggregate usage against limits.
3. **Background tasks**: Implementing non-blocking cleanup loops within the server process or as standalone scheduled jobs.
4. **Safety mechanisms**: Implementing "dry-run" capabilities and "in-use" detection to prevent accidental data loss.

**Primary recommendation:** Extend the `artifacts` table with `session_id` and `last_accessed_at`, implement a `StorageManager` service that calculates usage via SQLite aggregate queries, and use a background thread in the `serve` command to periodically trigger cleanup logic.

## Standard Stack

The established libraries/tools for this domain in the current project:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | Built-in | Metadata and usage tracking | Already used for tool registry and session store. |
| `pathlib` | Built-in | File system operations | Modern, safer alternative to `os.path`. |
| `asyncio` | Built-in | Background task management | Native support for non-blocking execution in the server. |
| `argparse` | Built-in | CLI commands | Used for the existing `bioimage-mcp` CLI. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `shutil` | Built-in | Bulk file deletion | Used for `rmtree` on directory artifacts. |
| `pydantic` | >= 2.0 | Policy configuration | Used for defining retention and quota schemas. |

**Installation:**
No new packages are strictly required as the built-in libraries are sufficient for these tasks.

## Architecture Patterns

### Recommended Project Structure
```
src/bioimage_mcp/
├── storage/
│   ├── manager.py      # Core StorageManager service
│   ├── policy.py       # Retention and Quota policy models
│   ├── cleanup.py      # Deletion logic and dry-run wrapper
│   └── sqlite.py       # Updated schema with triggers
```

### Pattern 1: SQLite-based Quota Tracking
Instead of calculating directory sizes on every request, track total usage in a dedicated `storage_metrics` table or a `registry_state` key.

**Implementation (Triggers):**
```sql
-- Source: Standard SQLite Trigger Pattern
CREATE TRIGGER IF NOT EXISTS trg_update_usage_after_insert
AFTER INSERT ON artifacts
BEGIN
    INSERT INTO registry_state (key, value, updated_at)
    VALUES ('total_artifact_bytes', NEW.size_bytes, datetime('now'))
    ON CONFLICT(key) DO UPDATE SET
        value = CAST(value AS INTEGER) + NEW.size_bytes,
        updated_at = datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS trg_update_usage_after_delete
AFTER DELETE ON artifacts
BEGIN
    UPDATE registry_state 
    SET value = CAST(value AS INTEGER) - OLD.size_bytes,
        updated_at = datetime('now')
    WHERE key = 'total_artifact_bytes';
END;
```

### Pattern 2: "In-Use" Detection (Active Reference Check)
To satisfy the requirement "Skip in-use artifacts (those with active references)", the system must check the `sessions` table status.

**Strategy:**
An artifact is considered "in-use" if:
1. It belongs to a session with status `active`.
2. It belongs to the `N` most recent sessions (e.g., the last 1).
3. (Optional) It has been accessed within the last `M` hours.

### Anti-Patterns to Avoid
- **Synchronous Cleanup on Run**: Never block a tool execution to perform storage cleanup. Use a background thread or a separate process.
- **Recursive Directory Walk for Size**: `os.walk` or `rglob` are slow on large artifact stores. Trust the `size_bytes` stored in the database during import.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directory Size | Manual walk | `du -sh`-like logic or DB tracking | Performance on deep Zarr trees. |
| Scheduling | Custom cron parser | `asyncio.sleep` loop | Simple enough for internal background tasks. |
| Lock Management | File locks | SQLite WAL Mode + Transactions | Built-in, reliable concurrency. |

## Common Pitfalls

### Pitfall 1: Directory Artifact Partial Deletion
**What goes wrong:** A deletion task is interrupted, leaving a partially deleted `.zarr` or `.ome.zarr` directory.
**How to avoid:** Rename the directory to a `.deleted` suffix before calling `shutil.rmtree`. If the process restarts, clean up all `.deleted` directories first.

### Pitfall 2: Race Condition during Import
**What goes wrong:** Cleanup triggers while an artifact is being imported but before it is registered in the DB.
**How to avoid:** The cleanup task should ignore files in `objects/` that are newer than e.g., 5 minutes, even if they aren't in the DB yet.

## Code Examples

### Dry-Run Implementation (Strategy Pattern)
```python
# Source: Python Dry-Run Patterns
from typing import Protocol
import pathlib
import shutil

class DeletionExecutor(Protocol):
    def delete(self, path: pathlib.Path) -> None: ...

class RealDeletionExecutor:
    def delete(self, path: pathlib.Path):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

class DryRunDeletionExecutor:
    def delete(self, path: pathlib.Path):
        print(f"[DRY-RUN] Would delete: {path}")

def perform_cleanup(candidates: list[pathlib.Path], executor: DeletionExecutor):
    for path in candidates:
        executor.delete(path)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Session TTL | Artifact Age TTL | 2026-02 (Current) | Decouples artifact lifecycle from session persistence. |
| Hard Quotas | Soft Thresholds | 2026-02 (Current) | Aggressive cleanup at 100%, warning at 80%. |

## Open Questions

1. **S3 Backend Support**: Requirements mention S3 support (Phase 17). How do we enforce quotas on S3 efficiently? 
   - *Recommendation*: Use the same SQLite tracking; trust the DB for S3 sizes rather than querying AWS S3 `ListObjects`.
2. **Multi-process concurrency**: If multiple `bioimage-mcp serve` instances run against the same SQLite DB, how is cleanup coordinated?
   - *Recommendation*: Use a "cleanup_lock" key in `registry_state` with an expiration.

## Sources

### Primary (HIGH confidence)
- SQLite Documentation - Triggers and JSON support
- Python `asyncio` Documentation - Background tasks and event loops
- Pydantic v2 Documentation - Schema validation

### Secondary (MEDIUM confidence)
- Standard patterns for data retention in object stores (S3 Lifecycle policies)
- POSIX file system cleanup best practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Core Python libraries are sufficient.
- Architecture: HIGH - SQLite-based tracking is a proven pattern.
- Pitfalls: MEDIUM - Concurrency and partial deletions need careful implementation.

**Research date:** 2026-02-02
**Valid until:** 2026-03-04
