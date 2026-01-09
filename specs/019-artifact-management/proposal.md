# Feature Specification: Artifact Store Retention & Quota Management

**Feature Branch**: `019-artifact-management`  
**Created**: 2026-01-09  
**Status**: Draft  
**Input**: Address unbounded growth of artifact store in `~/.bioimage-mcp/artifacts` by implementing session-level retention policies and storage quotas.

## Executive Summary

The artifact store in `~/.bioimage-mcp/artifacts` grows unbounded because artifacts are persisted after each run with no automatic cleanup. This causes disk space exhaustion on developer machines and in CI environments.

This specification introduces:
1. **Session-Level Retention**: All artifacts belong to a session; cleanup happens at session granularity with a configurable TTL (default: 7 days).
2. **Storage Quotas**: Configurable maximum store size with warning (80%) and critical (95%) thresholds.
3. **CLI-Only Management**: Prune and session management commands via CLI, with no MCP tool surface expansion (per constitution).
4. **Orphan Detection**: Automatic identification and cleanup of files not referenced in the SQLite index.

## Current State Analysis

### Existing Storage Architecture

The artifact store uses a hybrid system:
- **Object Store**: Files in `~/.bioimage-mcp/artifacts/objects/` named by UUID
- **SQLite Index**: Metadata in `~/.bioimage-mcp/artifacts/state/bioimage_mcp.sqlite3`
- **Memory Store**: Transient `mem://` and `obj://` references for in-session objects

### The Problem

| Aspect | Current State | Impact |
|--------|---------------|--------|
| TTL/Expiration | None | Store grows indefinitely |
| Session Cleanup | `session_ttl_hours` only marks sessions as expired in DB | Files remain on disk |
| Orphan Detection | None | Crashed runs leave dangling files |
| Quota Enforcement | None | Disk can fill completely |
| Manual Cleanup | No `delete(ref_id)` method | Users must manually `rm` files |

### Research: Industry Best Practices

Research into similar systems (DVC, MLflow, GitHub Actions, Galaxy Project, Docker) revealed common patterns:

| System | Pattern | Key Insight |
|--------|---------|-------------|
| **DVC** | Reference Counting + `gc` | Only delete data not referenced by any commit/workspace |
| **GitHub Actions** | TTL-based | 90-day default, configurable per-workflow |
| **Docker** | Prune orphans | `docker system prune` removes dangling objects |
| **Galaxy Project** | Delete vs Purge | Two-stage deletion prevents accidental data loss |

## Gap Analysis

| What We Have | What We Need | Risk |
|--------------|--------------|------|
| Session metadata in SQLite | Completion timestamp, size tracking | Can't determine age or space usage |
| Artifact → session link | Cascade delete support | Manual cleanup only |
| No quota system | Configurable limits with thresholds | Disk exhaustion |
| No CLI commands | Prune, status, session management | No user control |

## Proposed Architecture

### 1. Session-Level Retention Model

**Key Decision**: All retention operates at session granularity, not per-artifact.

- All artifacts belong to a session
- Sessions have a single TTL (default: 7 days after completion)
- Prune deletes entire sessions that have expired
- Sessions can be pinned to exempt from auto-cleanup

This simplifies the mental model and avoids the complexity of per-artifact TTLs or tiered retention.

### 2. Data Model Changes

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

### 3. Storage Quota System

Incremental size tracking avoids expensive disk scans:

```python
def register_artifact(ref_id, session_id, file_path):
    size_bytes = os.path.getsize(file_path)
    db.execute("INSERT INTO artifacts (..., size_bytes) VALUES (..., ?)", (size_bytes,))
    db.execute("UPDATE sessions SET total_size_bytes = total_size_bytes + ? WHERE session_id = ?", 
               (size_bytes, session_id))
```

Quota enforcement at run start:

```python
def check_quota_before_run():
    current_usage = db.query("SELECT SUM(total_size_bytes) FROM sessions")[0]
    max_bytes = config.quota.max_size_bytes
    
    if current_usage >= max_bytes * 0.95:
        raise StorageQuotaExceeded(
            f"Artifact store is {current_usage/max_bytes:.0%} full. "
            f"Run 'bioimage-mcp prune' to free space."
        )
    elif current_usage >= max_bytes * 0.80:
        logger.warning(f"Artifact store is {current_usage/max_bytes:.0%} full")
```

### 4. Prune Command

Two-pass cleanup:

1. **Expired Sessions**: Sessions where `is_pinned = FALSE` and `completed_at < now - retention_days`
2. **Orphaned Files**: Files in `objects/` with no matching `artifacts` row

```python
def prune(dry_run: bool = False, force: bool = False):
    retention_days = config.retention.session_retention_days
    
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

### 5. Session Deletion (Cascade)

```python
def delete_session(session_id: str):
    with db.transaction():
        artifacts = db.query("SELECT uri FROM artifacts WHERE session_id = ?", (session_id,))
        file_paths = [uri_to_path(a['uri']) for a in artifacts]
        
        db.execute("DELETE FROM artifacts WHERE session_id = ?", (session_id,))
        db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    
    # Delete files after transaction commits (best-effort)
    for path in file_paths:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as e:
            logger.warning(f"Failed to delete {path}: {e}")
```

## User Scenarios & Testing

### User Story 1: Developer Reclaims Disk Space (Priority: P0)

**Given** a developer has been using bioimage-mcp for several weeks,  
**When** they run `bioimage-mcp storage status`,  
**Then** they see a breakdown of usage by session age and can identify reclaimable space.

**When** they run `bioimage-mcp prune --dry-run`,  
**Then** they see exactly what would be deleted without any data loss.

**When** they run `bioimage-mcp prune`,  
**Then** expired sessions and orphaned files are removed, freeing disk space.

### User Story 2: CI Environment Stays Clean (Priority: P0)

**Given** a CI pipeline that runs bioimage-mcp tests,  
**When** the pipeline completes,  
**Then** artifacts from sessions older than `session_retention_days` are automatically prunable.

**When** the next CI run starts and storage exceeds 95%,  
**Then** the run is blocked with a clear error message directing the operator to run `prune`.

### User Story 3: Protecting Important Results (Priority: P1)

**Given** a user has a session with important validated results,  
**When** they run `bioimage-mcp session pin <session_id>`,  
**Then** that session is exempt from automatic pruning regardless of age.

**When** they later run `bioimage-mcp session unpin <session_id>`,  
**Then** the session becomes subject to normal retention policy.

### User Story 4: Understanding Storage Usage (Priority: P1)

**Given** a user wants to understand what's consuming space,  
**When** they run `bioimage-mcp session list`,  
**Then** they see all sessions with their status (active/retained/expired/pinned) and size.

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Prune during active session | Never delete sessions with `completed_at IS NULL` |
| File already deleted | Log warning, continue (idempotent cleanup) |
| Directory artifact (`.ome.zarr`) | Use `shutil.rmtree()` instead of `os.remove()` |
| DB entry but file missing | Remove DB entry, log as "stale reference" |
| Concurrent prune commands | Use SQLite transaction + file locking |
| Prune interrupted mid-session | Next prune catches remaining files (orphan pass) |
| Quota check with no sessions | Return 0 usage, allow run |

## Requirements

### Constitution Constraints

#### 1. Stable MCP Surface (Anti-Context-Bloat)
**Compliance**: No new MCP tools. All management is via CLI commands, keeping the MCP surface focused on bioimage analysis.

#### 2. Isolated Tool Execution
**Compliance**: Quota checks happen in the core server before dispatching to tool subprocesses. No changes to tool isolation model.

#### 3. Artifact References Only
**Compliance**: This feature manages the lifecycle of artifacts but does not change how they are referenced or accessed.

#### 4. Reproducibility & Provenance
**Compliance**: Prune respects pinned sessions. Workflow exports remain unaffected. Deleted sessions cannot be replayed (by design).

#### 5. Safety & Observability
**Compliance**: 
- `--dry-run` mode for safe preview
- Confirmation prompt before destructive operations
- Structured logging of all deletions
- Never delete active sessions

#### 6. Test-Driven Development
**Compliance**: Tests written first for prune logic, quota enforcement, and CLI commands.

### Functional Requirements

- **FR-001**: System MUST track `completed_at` timestamp when sessions end
- **FR-002**: System MUST track `total_size_bytes` per session, updated incrementally
- **FR-003**: System MUST support `is_pinned` flag to exempt sessions from cleanup
- **FR-004**: `prune` command MUST delete expired sessions and orphaned files
- **FR-005**: `prune --dry-run` MUST show what would be deleted without deleting
- **FR-006**: `prune --force` MUST skip confirmation prompt
- **FR-007**: `storage status` MUST show usage breakdown by session state
- **FR-008**: `session list` MUST show all sessions with status, age, and size
- **FR-009**: `session pin/unpin` MUST toggle the `is_pinned` flag
- **FR-010**: Quota check MUST run before each `run` call
- **FR-011**: Quota check MUST raise `StorageQuotaExceeded` at 95% usage
- **FR-012**: Quota check MUST log warning at 80% usage
- **FR-013**: Session deletion MUST cascade to all artifacts and files

### Non-Functional Requirements

- **NFR-001**: `storage status` MUST complete in <1 second (uses SQLite aggregation)
- **NFR-002**: Quota check MUST add <10ms overhead to run calls
- **NFR-003**: Prune of 100 sessions MUST complete in <30 seconds
- **NFR-004**: Database migrations MUST be backward-compatible

## Configuration

### Config File Structure

```yaml
# ~/.bioimage-mcp/config.yaml
artifact_store:
  root: ~/.bioimage-mcp/artifacts
  
  retention:
    session_retention_days: 7    # Sessions older than this are prunable
    
  quota:
    max_size: "50GB"             # Optional; null = unlimited
    warn_threshold: 0.80         # Log warning at 80%
    critical_threshold: 0.95     # Block runs at 95%
```

### Pydantic Schema

```python
class RetentionConfig(BaseModel):
    session_retention_days: int = Field(
        default=7, ge=1,
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

### Environment Variable Overrides

```bash
BIOIMAGE_MCP_RETENTION_DAYS=1        # Short retention for CI
BIOIMAGE_MCP_QUOTA_MAX_SIZE=10GB     # Small quota for testing
BIOIMAGE_MCP_QUOTA_ENABLED=false     # Disable quota entirely
```

## Error Types

```python
class StorageError(Exception):
    """Base class for storage-related errors"""

class StorageQuotaExceeded(StorageError):
    """Raised when artifact store exceeds critical threshold"""
    def __init__(self, usage_pct: float, max_size: str):
        self.usage_pct = usage_pct
        super().__init__(
            f"Artifact store is {usage_pct:.0%} full (limit: {max_size}). "
            f"Run 'bioimage-mcp prune' to free space."
        )

class SessionNotFound(StorageError):
    """Raised when referencing a non-existent session"""
    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}")

class PruneConflict(StorageError):
    """Raised when prune cannot acquire lock"""
    def __init__(self):
        super().__init__("Another prune operation is in progress")
```

## Implementation Plan

### Phase 1: Schema & Tracking (0.19.1)

1. Add database migration for new session columns
2. Add `RetentionConfig` and `QuotaConfig` to config schema
3. Hook artifact creation to update `total_size_bytes`
4. Hook session completion to set `completed_at`

### Phase 2: Prune Logic (0.19.2)

1. Implement `retention.py` with prune core logic
2. Implement `quota.py` with size parsing and threshold checks
3. Add quota check hook before run execution
4. Write unit tests for all prune scenarios

### Phase 3: CLI Commands (0.19.3)

1. Implement `bioimage-mcp prune` command
2. Implement `bioimage-mcp storage status` command
3. Implement `bioimage-mcp session list/pin/unpin` commands
4. Write CLI integration tests

### Phase 4: Testing & Documentation (0.19.4)

1. Add integration tests with real artifact store
2. Update AGENTS.md with new commands
3. Add user documentation for storage management

## File Changes

### New Files

```
src/bioimage_mcp/
├── storage/
│   ├── retention.py          # Prune logic, session cleanup
│   ├── quota.py              # Quota checking, size parsing
│   └── errors.py             # StorageQuotaExceeded, SessionNotFound
├── cli/
│   ├── prune.py              # bioimage-mcp prune command
│   ├── storage_cmd.py        # bioimage-mcp storage status command
│   └── session_cmd.py        # bioimage-mcp session list/pin/unpin
```

### Modified Files

```
src/bioimage_mcp/
├── config/schema.py          # Add RetentionConfig, QuotaConfig
├── storage/sqlite.py         # Add migration for new columns
├── artifacts/store.py        # Hook size tracking on artifact creation
├── api/runs.py               # Add quota check before run execution
├── runtimes/session.py       # Set completed_at on session end
└── cli/__init__.py           # Register new CLI commands
```

### Database Migration

```python
# storage/migrations/002_retention_fields.py
def upgrade(db):
    db.execute("ALTER TABLE sessions ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE")
    db.execute("ALTER TABLE sessions ADD COLUMN completed_at TIMESTAMP")
    db.execute("ALTER TABLE sessions ADD COLUMN total_size_bytes INTEGER DEFAULT 0")
    
    # Backfill existing sessions as completed
    db.execute("UPDATE sessions SET completed_at = created_at WHERE completed_at IS NULL")
```

## CLI Reference

### Commands

```bash
# Prune expired sessions and orphaned files
bioimage-mcp prune [--dry-run] [--force]

# Show storage usage breakdown
bioimage-mcp storage status

# List all sessions with status and size
bioimage-mcp session list

# Pin a session (exempt from auto-cleanup)
bioimage-mcp session pin <session_id>

# Unpin a session (subject to retention policy)
bioimage-mcp session unpin <session_id>
```

### Example Output

```bash
$ bioimage-mcp storage status

Artifact Store Status
=====================
Location: ~/.bioimage-mcp/artifacts
Usage:    45.2 GB / 50 GB (90%)

Breakdown by status:
  Active:    1.2 GB (1 session)
  Retained:  30.5 GB (12 sessions, <7 days old)
  Expired:   8.5 GB (5 sessions, >7 days old)  ← prunable
  Pinned:    5.0 GB (2 sessions)

Orphaned files: 3 files, 1.2 GB  ← prunable

Total reclaimable: 9.7 GB

Run 'bioimage-mcp prune --dry-run' to preview cleanup.
```

```bash
$ bioimage-mcp session list

Session ID                          Status              Age       Size
────────────────────────────────────────────────────────────────────────
ses_abc123def456                    active              -         1.2 GB
ses_789xyz012abc                    retained            2d        3.4 GB
ses_mno345pqr678                    retained            5d        0.8 GB
ses_stu901vwx234                    expired             12d       2.1 GB
ses_important_run                   pinned              30d       5.0 GB
                                                               ──────────
                                                    Total:     12.5 GB
```

## Success Criteria

- **SC-001**: `bioimage-mcp prune --dry-run` correctly identifies expired sessions and orphans
- **SC-002**: `bioimage-mcp prune` deletes expired sessions and reclaims disk space
- **SC-003**: Quota check blocks runs at 95% usage with actionable error message
- **SC-004**: Quota check logs warning at 80% usage
- **SC-005**: `session pin` prevents session from being pruned regardless of age
- **SC-006**: `storage status` returns accurate breakdown in <1 second
- **SC-007**: Active sessions are never deleted by prune
- **SC-008**: Orphaned files are detected and cleaned up
- **SC-009**: All operations are idempotent (safe to run multiple times)

## Migration Notes

- Existing sessions will be backfilled with `completed_at = created_at`
- Existing artifacts will need size recalculation on first status call (one-time migration)
- No breaking changes to existing APIs or artifact formats

## Out of Scope

1. **Per-artifact TTLs**: All retention is session-scoped for simplicity
2. **Automatic background cleanup**: Only on-demand prune command
3. **Remote storage backends**: Local filesystem only (S3/GCS left for future)
4. **Compression**: No automatic compression of old artifacts
5. **Tiered storage**: No hot/cold storage tiers

---

This proposal establishes a simple, user-controlled system for managing artifact store growth while respecting the constitution's requirement for a stable MCP surface.
