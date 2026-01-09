# Storage Management Service Internal API Contract

This document specifies the internal Python API for the `StorageService` class. This service is responsible for managing the artifact store lifecycle, enforcing quotas, and performing cleanup operations. 

**Note**: This is an internal system API and is NOT exposed directly via the MCP protocol.

## Service Definition

### `StorageService`

```python
class StorageService:
    """Manages artifact store lifecycle, quotas, and cleanup."""
    
    def __init__(self, config: Config, conn: sqlite3.Connection) -> None:
        """
        Initialize the storage service.
        
        Args:
            config: Layered YAML configuration containing storage limits and paths.
            conn: SQLite database connection for artifact and session indexing.
        """
        ...
```

## Methods

### 1. `get_status() -> StorageStatus`
Returns current storage usage breakdown.
- Aggregates `size_bytes` from the `artifacts` table.
- Groups by session state (active, completed, expired, pinned).
- Scans the `objects/` directory for orphan detection.
- **Returns**: `StorageStatus` model.

### 2. `check_quota() -> QuotaCheckResult`
Pre-run quota validation used by `ExecutionService` before starting runs.
- **Returns**: `QuotaCheckResult` with `allowed: bool`, `usage_percent: float`, and `message: str`.

### 3. `prune(dry_run: bool = False, include_orphans: bool = True, older_than_days: int | None = None) -> PruneResult`
Delete expired sessions and orphaned files.
- Identifies expired, non-pinned sessions.
- Deletes files from storage first, then removes database records.
- Optionally cleans orphaned files (files on disk not tracked in DB).
- **Returns**: `PruneResult` model.

### 4. `pin_session(session_id: str) -> Session`
Mark a session as pinned to prevent it from being pruned.
- Sets `is_pinned = 1`.
- **Returns**: Updated `Session` model.
- **Raises**: `KeyError` if the `session_id` is not found.

### 5. `unpin_session(session_id: str) -> Session`
Remove the pin from a session, allowing it to be pruned if expired.
- Sets `is_pinned = 0`.
- **Returns**: Updated `Session` model.
- **Raises**: `KeyError` if the `session_id` is not found.

### 6. `list_sessions(state: str | None = None, limit: int = 50, sort_by: str = "age") -> list[SessionSummary]`
List sessions with associated storage information.
- Filter by state if provided.
- Includes artifact count and total size per session.
- **Returns**: A list of `SessionSummary` models.

### 7. `get_session_size(session_id: str) -> int`
Get total bytes used by a specific session.
- Aggregates `size_bytes` from `artifacts` where `session_id = ?`.
- **Returns**: Total size in bytes.

### 8. `find_orphans() -> list[OrphanFile]`
Identify files in the storage root that are not tracked in the database.
- Scans `artifact_store_root/objects/`.
- Compares findings against `artifacts.uri`.
- **Returns**: List of `OrphanFile` objects with path and `size_bytes`.

### 9. `delete_orphans(orphans: list[OrphanFile]) -> int`
Delete specified orphan files from the filesystem.
- **Returns**: Count of successfully deleted files.

### 10. `complete_session(session_id: str) -> Session`
Mark a session as completed.
- Sets `completed_at` to the current timestamp.
- Updates status to `'completed'`.
- **Returns**: Updated `Session` model.

---

## Data Models

All models use `pydantic.BaseModel`.

```python
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime

class QuotaCheckResult(BaseModel):
    allowed: bool
    usage_percent: float
    message: str

class StorageStatus(BaseModel):
    total_bytes: int
    by_state: dict[str, int]  # e.g., {"active": 1024, "pinned": 2048}
    orphan_count: int
    orphan_bytes: int
    quota_limit: int

class SessionSummary(BaseModel):
    session_id: str
    status: str  # active, completed, expired, pinned
    is_pinned: bool
    created_at: datetime
    completed_at: datetime | None
    artifact_count: int
    total_bytes: int
    age_seconds: int

class OrphanFile(BaseModel):
    path: Path
    size_bytes: int

class PruneResult(BaseModel):
    sessions_deleted: int
    files_deleted: int
    bytes_reclaimed: int
    dry_run: bool
```
