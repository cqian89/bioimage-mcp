# Artifact Store Retention Design

**Date**: 2026-01-09  
**Status**: Approved  
**Problem**: The artifact store in `~/.bioimage-mcp/artifacts` grows unbounded because artifacts are persisted after each run with no automatic cleanup.

## Overview

This design introduces session-level retention policies and storage quotas to automatically manage artifact store growth while preserving user control.

### Key Decisions

- **Session-scoped retention**: All artifacts belong to a session; cleanup happens at session granularity
- **Single TTL tier**: Completed sessions are prunable after a configurable retention period (default: 7 days)
- **Hybrid cleanup model**: On-demand `prune` command + automatic quota enforcement
- **CLI-only interface**: No MCP tool surface expansion (per constitution)

## Data Model

### Session Metadata (SQLite)

New columns on the `sessions` table:

```sql
ALTER TABLE sessions ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE;
ALTER TABLE sessions ADD COLUMN completed_at TIMESTAMP;  -- NULL if still active
ALTER TABLE sessions ADD COLUMN total_size_bytes INTEGER DEFAULT 0;
```

- `completed_at` is set when a session ends (success or failure)
- TTL countdown starts from `completed_at`, not `created_at`
- `is_pinned = TRUE` exempts session from expiration
- `total_size_bytes` is updated incrementally as artifacts are added

### Artifact → Session Link

The existing `artifacts` table already has `session_id`. Cascade cleanup:

```sql
DELETE FROM artifacts WHERE session_id = 'abc-123';
```

### Orphan Detection

Files in `objects/` with no matching `artifacts` row:

```python
disk_files = set(os.listdir(objects_dir))
indexed_files = set(row['filename'] for row in db.query("SELECT uri FROM artifacts"))
orphans = disk_files - indexed_files
```

## Storage Quota & Tracking

### Incremental Size Tracking

```python
def register_artifact(ref_id, session_id, file_path):
    size_bytes = os.path.getsize(file_path)
    db.execute("""
        INSERT INTO artifacts (ref_id, session_id, size_bytes, ...)
        VALUES (?, ?, ?, ...)
    """, (ref_id, session_id, size_bytes, ...))
    
    db.execute("""
        UPDATE sessions 
        SET total_size_bytes = total_size_bytes + ?
        WHERE session_id = ?
    """, (size_bytes, session_id))
```

### Quota Enforcement

Checked at run start:

```python
def check_quota_before_run():
    current_usage = db.query("SELECT SUM(total_size_bytes) FROM sessions")[0]
    max_bytes = config.max_store_size_bytes
    
    if current_usage >= max_bytes * 0.95:
        raise StorageQuotaExceeded(
            f"Artifact store is {current_usage/max_bytes:.0%} full. "
            f"Run 'bioimage-mcp prune' to free space."
        )
    elif current_usage >= max_bytes * 0.80:
        logger.warning(f"Artifact store is {current_usage/max_bytes:.0%} full")
```

### Fast Status Query

```sql
SELECT 
    CASE 
        WHEN is_pinned THEN 'pinned'
        WHEN completed_at IS NULL THEN 'active'
        WHEN completed_at < datetime('now', '-7 days') THEN 'expired'
        ELSE 'retained'
    END as status,
    COUNT(*) as session_count,
    SUM(total_size_bytes) as total_bytes
FROM sessions
GROUP BY status;
```

## Prune Command

### Core Logic

```python
def prune(dry_run: bool = False, force: bool = False):
    retention_days = config.session_retention_days
    
    # Pass 1: Find expired sessions
    expired_sessions = db.query("""
        SELECT session_id, total_size_bytes 
        FROM sessions
        WHERE is_pinned = FALSE
          AND completed_at IS NOT NULL
          AND completed_at < datetime('now', ? || ' days')
    """, (-retention_days,))
    
    # Pass 2: Find orphaned files
    disk_files = {f.name: f.path for f in os.scandir(objects_dir)}
    indexed_uris = {row['uri'] for row in db.query("SELECT uri FROM artifacts")}
    orphans = [(name, path) for name, path in disk_files.items() 
               if f"objects/{name}" not in indexed_uris]
    
    if dry_run:
        print_dry_run_report(expired_sessions, orphans)
        return
    
    if not force and (expired_sessions or orphans):
        confirm = prompt(f"Delete {len(expired_sessions)} sessions and {len(orphans)} orphans?")
        if not confirm:
            return
    
    for session in expired_sessions:
        delete_session(session['session_id'])
    for name, path in orphans:
        os.remove(path)
```

### Session Deletion

```python
def delete_session(session_id: str):
    artifacts = db.query(
        "SELECT uri FROM artifacts WHERE session_id = ?", (session_id,)
    )
    
    for artifact in artifacts:
        file_path = uri_to_path(artifact['uri'])
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
    
    db.execute("DELETE FROM artifacts WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
```

### CLI Output Example

```
$ bioimage-mcp prune --dry-run

Artifact Store Prune (dry run)
==============================
Retention policy: 7 days

Expired sessions (3):
  ses_a1b2c3  completed 12 days ago   2.3 GB
  ses_d4e5f6  completed 9 days ago    1.1 GB  
  ses_g7h8i9  completed 8 days ago    0.5 GB

Orphaned files (2):
  objects/abc123.tif     450 MB
  objects/def456.ome.zarr/  1.2 GB

Total reclaimable: 5.55 GB

Run without --dry-run to delete.
```

## Session Management Commands

### Session List

```
$ bioimage-mcp session list

Session ID                          Status              Size
──────────────────────────────────────────────────────────────
ses_abc123def456                    active              1.2 GB
ses_789xyz012abc                    retained (2d)       3.4 GB
ses_mno345pqr678                    retained (5d)       0.8 GB
ses_stu901vwx234                    expired (12d)       2.1 GB
ses_important_run                   pinned              5.0 GB
                                                    ──────────
                                    Total:             12.5 GB
```

### Pin / Unpin

```bash
$ bioimage-mcp session pin ses_important_run
Session ses_important_run pinned (exempt from auto-cleanup)

$ bioimage-mcp session unpin ses_important_run  
Session ses_important_run unpinned (subject to retention policy)
```

## Configuration

### Config File

```yaml
artifact_store:
  root: ~/.bioimage-mcp/artifacts
  retention:
    session_retention_days: 7
  quota:
    max_size: "50GB"
    warn_threshold: 0.80
    critical_threshold: 0.95
```

### Pydantic Schema

```python
class RetentionConfig(BaseModel):
    session_retention_days: int = Field(
        default=7,
        ge=1,
        description="Days to retain completed sessions before they become prunable"
    )

class QuotaConfig(BaseModel):
    max_size: str | None = Field(
        default="50GB",
        description="Maximum store size (e.g., '50GB', '100MB'), null for unlimited"
    )
    warn_threshold: float = Field(default=0.80, ge=0, le=1)
    critical_threshold: float = Field(default=0.95, ge=0, le=1)

class ArtifactStoreConfig(BaseModel):
    root: Path = Field(default=Path("~/.bioimage-mcp/artifacts"))
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    quota: QuotaConfig = Field(default_factory=QuotaConfig)
```

### Environment Overrides

```bash
BIOIMAGE_MCP_RETENTION_DAYS=1
BIOIMAGE_MCP_QUOTA_MAX_SIZE=10GB
BIOIMAGE_MCP_QUOTA_ENABLED=false
```

## Error Handling

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Prune during active session | Never delete sessions with `completed_at IS NULL` |
| File already deleted | Log warning, continue (idempotent) |
| Directory artifact (`.ome.zarr`) | Use `shutil.rmtree()` |
| DB entry but file missing | Remove DB entry, log as "stale reference" |
| Concurrent prune commands | SQLite transaction + file locking |
| Prune interrupted | Next prune catches remaining files |

### Error Types

```python
class StorageError(Exception):
    """Base class for storage-related errors"""

class StorageQuotaExceeded(StorageError):
    """Raised when artifact store exceeds critical threshold"""

class SessionNotFound(StorageError):
    """Raised when referencing a non-existent session"""

class PruneConflict(StorageError):
    """Raised when prune cannot acquire lock"""
```

## Integration Points

### New Files

```
src/bioimage_mcp/
├── storage/
│   ├── retention.py      # Prune logic, session cleanup
│   ├── quota.py          # Quota checking, size tracking
│   └── errors.py         # StorageQuotaExceeded, etc.
├── cli/
│   ├── prune.py          # bioimage-mcp prune
│   ├── storage.py        # bioimage-mcp storage status
│   └── session.py        # bioimage-mcp session list/pin/unpin
```

### Modified Files

```
src/bioimage_mcp/
├── config/schema.py      # Add RetentionConfig, QuotaConfig
├── storage/sqlite.py     # Add migration for new columns
├── artifacts/store.py    # Hook size tracking on artifact creation
├── api/runs.py           # Add quota check before run execution
└── cli/__init__.py       # Register new CLI commands
```

### Hook Points

1. **Artifact Creation → Size Tracking**: Update `total_size_bytes` in session
2. **Run Start → Quota Check**: Raise `StorageQuotaExceeded` if over 95%
3. **Session End → Set `completed_at`**: Start retention countdown

### Database Migration

```python
def upgrade(db):
    db.execute("ALTER TABLE sessions ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE")
    db.execute("ALTER TABLE sessions ADD COLUMN completed_at TIMESTAMP")
    db.execute("ALTER TABLE sessions ADD COLUMN total_size_bytes INTEGER DEFAULT 0")
    
    # Backfill existing sessions
    db.execute("UPDATE sessions SET completed_at = created_at WHERE completed_at IS NULL")
```

## Implementation Order

1. Schema changes — DB migration, config schema
2. Size tracking — Hook artifact creation
3. Quota enforcement — Check before runs
4. Prune logic — Core deletion implementation
5. CLI commands — User-facing interface
6. Tests — Unit + integration coverage

## CLI Reference

```bash
bioimage-mcp prune [--dry-run] [--force]
bioimage-mcp storage status
bioimage-mcp session list
bioimage-mcp session pin <session_id>
bioimage-mcp session unpin <session_id>
```

## Configuration Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| `session_retention_days` | 7 | Days before session becomes prunable |
| `max_size` | 50GB | Maximum store size |
| `warn_threshold` | 0.80 | Log warning at this usage |
| `critical_threshold` | 0.95 | Block runs at this usage |
