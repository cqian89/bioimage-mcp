# CLI Contract: Storage & Artifact Management (019)

This document specifies the command-line interface for managing storage, sessions, and artifacts in `bioimage-mcp`.

## 1. Overview

Storage management commands are grouped under the `storage` subparser.

```bash
bioimage-mcp storage [COMMAND]
```

| Command | Purpose |
| :--- | :--- |
| `status` | Display storage usage breakdown by session state. |
| `prune` | Remove expired sessions and orphaned files. |
| `pin` | Mark a session as protected from automated cleanup. |
| `list` | List sessions with storage details and filtering. |

---

## 2. Commands

### 2.1 `bioimage-mcp storage status`

Display storage usage relative to quotas and breakdown by session lifecycle state.

#### Arguments
- `--json`: Output machine-readable JSON (maps to `StorageStatus` model).
- `-v, --verbose`: Show detailed per-session statistics.

#### Human Output Example
```text
Storage Usage Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Quota:    50.0 GB
Used:           15.2 GB (30.4%)
Available:      34.8 GB (69.6%)

Breakdown by State:
  Active:       3 sessions,  5.1 GB
  Completed:    8 sessions,  7.3 GB  
  Expired:      5 sessions,  2.6 GB (reclaimable)
  Pinned:       2 sessions,  0.2 GB

Orphaned Files: 47 MB (23 files)
```

#### Exit Codes
- `0`: Normal usage (below warning threshold).
- `1`: Warning threshold exceeded (default >80%).
- `2`: Critical threshold exceeded (default >95%).

---

### 2.2 `bioimage-mcp storage prune`

Reclaim space by deleting expired sessions and files not indexed in the database.

#### Arguments
- `--dry-run, -n`: Preview changes without deleting.
- `--force, -f`: Skip confirmation prompt.
- `--include-orphans`: Also clean orphaned files (default: `True`).
- `--older-than DAYS`: Override the default `retention_days` for this run.

#### Human Output Example
```text
Pruning expired sessions...

Sessions to delete: 5
  - ses_abc123 (2.1 GB, completed 12 days ago)
  - ses_def456 (0.5 GB, completed 8 days ago)
  ...

Orphaned files to delete: 23 files (47 MB)

Total space to reclaim: 2.65 GB

Proceed? [y/N]: y

✓ Deleted 5 sessions (42 artifacts)
✓ Deleted 23 orphaned files
✓ Reclaimed 2.65 GB
```

#### JSON Output (`--json`)
Returns the `PruneResult` model as defined in `data-model.md`.

#### Exit Codes
- `0`: Success.
- `1`: Partial failure (some files/records could not be deleted).
- `2`: Complete failure (e.g., database unavailable).

---

### 2.3 `bioimage-mcp storage pin <session_id>`

Protect a specific session from automated or manual pruning.

#### Arguments
- `session_id` (Positional, Required): The ID of the session to pin/unpin.
- `--unpin`: Remove the protection pin instead of adding it.

#### Human Output Example
```text
✓ Session ses_abc123 is now pinned (protected from cleanup)
  - 42 artifacts, 2.1 GB total
```

#### Exit Codes
- `0`: Success.
- `1`: Session ID not found.

---

### 2.4 `bioimage-mcp storage list`

List sessions and their associated storage footprint.

#### Arguments
- `--state STATE`: Filter by session state (`active`, `completed`, `expired`, `pinned`).
- `--limit N`: Maximum sessions to show (default: `50`).
- `--sort KEY`: Sort by `size`, `age`, or `name` (default: `age`).
- `--json`: Output as a JSON array of session storage objects.

#### Human Output Example
```text
Sessions (showing 15 of 23)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION ID           STATE      SIZE     AGE        ARTIFACTS
ses_abc123          active     2.1 GB   2h 15m     42
ses_def456          completed  0.5 GB   3d 4h      12
ses_ghi789          expired    1.2 GB   12d        28
ses_jkl012 [📌]      pinned     0.8 GB   45d        15
```

#### Exit Codes
- `0`: Success.
- `1`: Invalid filter or sort parameters.

---

## 3. Data Model Mapping

The CLI output MUST align with the models defined in `data-model.md`:

- `status --json` -> `StorageStatus`
- `prune --json` -> `PruneResult`
- `list --json` -> `List[SessionStorageInfo]`
