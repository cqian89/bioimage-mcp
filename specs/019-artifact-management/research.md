# Research: Artifact Management & Lifecycle (019-artifact-management)

This document outlines the research findings and architectural decisions for implementing artifact lifecycle management, storage quotas, and cleanup strategies in `bioimage-mcp`.

## Context Summary
- **Storage Architecture**: `bioimage-mcp` uses a dual-storage approach: a SQLite database for indexing and metadata (`state/bioimage_mcp.sqlite3`) and the local filesystem for actual artifact data (images, logs, tables).
- **Current Schema**: The `sessions`, `artifacts`, and `session_steps` tables exist, but `artifacts` currently lacks a direct `session_id` foreign key. Linkage is buried in `session_steps.outputs_json`.
- **Cleanup State**: No automated deletion or cleanup logic exists. Sessions remain in the DB indefinitely, and files persist on disk regardless of age.
- **CLI/Config**: Uses `argparse` with subcommands and Pydantic models for configuration. `session_ttl_hours` is already defined in `Config` but not enforced.

---

## Key Decisions

### 1. Schema Migration: Artifact-Session Linking
**Decision**: Add an optional `session_id` column to the `artifacts` table as a Foreign Key.
**Rationale**: 
- **Performance**: Querying artifacts by session via JSON extraction in `session_steps` is extremely slow and complex at scale. A direct FK allows for efficient indexing and recursive deletion.
- **Traceability**: Makes it trivial to calculate total storage used by a specific session.
- **Flexibility**: Keeping it optional allows for "global" artifacts (like shared datasets or base models) that aren't tied to a specific session.

**Alternatives considered**: 
- *Query-time join*: Rejected due to complexity of parsing `outputs_json` for every cleanup check.
- *Materialized view*: SQLite support for materialized views is limited; a direct column with a standard index is more robust for our use case.

### 2. Session State Extension
**Decision**: Add `completed_at` (timestamp) and `is_pinned` (boolean) columns to the `sessions` table.
**Rationale**: 
- **Cleanup Logic**: `last_activity_at` tracks when a session was last touched, but `completed_at` is a better trigger for TTL-based cleanup of finished workflows.
- **User Control**: `is_pinned` allows users to protect specific sessions (and their associated artifacts) from automated cleanup/pruning.
- **Total Size**: Total size will be calculated via aggregation rather than a static column to avoid synchronization issues during concurrent writes.

**Alternatives considered**:
- *Separate Lifecycle Table*: Rejected as it adds unnecessary join complexity for core session queries.

### 3. Quota Configuration
**Decision**: Extend the `Config` Pydantic model with a nested `StorageSettings` model.
**Rationale**: 
- **Consistency**: Keeps all system limits in one place.
- **Validation**: Leverages Pydantic's validators to ensure `critical_threshold` > `warning_threshold`.
- **Default Values**: Provides a sane default (e.g., 50GB) that is easily overrideable via `config.yaml`.

**Alternatives considered**:
- *Separate StorageQuota model*: Rejected as storage is a core concern of the server's configuration, not a separate pluggable module.

### 4. Cleanup Strategy
**Decision**: Two-phase "File-First, DB-Second" approach with orphan handling.
**Rationale**: 
- **Safety**: Deleting the DB record first makes the file "orphaned" and potentially forgotten if the process crashes mid-cleanup. Deleting the file first ensures we reclaim space immediately.
- **Integrity**: A background "orphan sweep" will periodically reconcile the filesystem against the DB to catch any files missed during failed cleanup tasks.
- **Atomicity**: While SQLite provides transactions, the filesystem does not; this strategy minimizes the risk of leaked disk space.

**Alternatives considered**:
- *Transactional approach*: Impossible across DB/Filesystem boundaries without complex WAL-like logging.

### 5. CLI Command Structure
**Decision**: Implement nested subcommands under a `storage` namespace: `bioimage-mcp storage prune` and `bioimage-mcp storage status`.
**Rationale**: 
- **Scalability**: Allows adding more storage-related tools (like `reindex`, `verify`, or `import`) without cluttering the top-level CLI.
- **Clarity**: Groups lifecycle management commands together logically.

**Alternatives considered**:
- *Top-level commands*: Rejected as `prune` is too ambiguous; it should be clear what is being pruned.

### 6. Quota Enforcement Point
**Decision**: Enforce at the `ExecutionService` level before dispatching a run.
**Rationale**: 
- **User Experience**: Prevents starting a long-running, resource-intensive job that is guaranteed to fail due to disk space.
- **Centralization**: All tool runs pass through `ExecutionService`, making it the "choke point" for system health checks.

**Alternatives considered**:
- *In worker*: Rejected because by the time the worker starts, environment setup costs (Conda activation, model loading) have already been paid.

### 7. Orphan Detection Strategy
**Decision**: Periodic "Reference Reconciliation" scan.
**Rationale**: 
- **Accuracy**: Comparing the `artifacts` table against the `objects/` directory is the only way to catch files added manually or left behind by crashed processes.
- **Low Overhead**: This scan can be run infrequently (e.g., once a day or via CLI manual trigger) so it doesn't impact runtime performance.

**Alternatives considered**:
- *Separate tracking table*: Rejected as it can still get out of sync with the actual filesystem. The filesystem itself is the "ground truth" for orphans.
