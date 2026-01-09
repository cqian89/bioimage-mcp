# Feature Specification: Artifact Store Retention & Quota Management

**Feature Branch**: `019-artifact-management`  
**Created**: 2026-01-09  
**Status**: Draft  
**Input**: `specs/019-artifact-management/proposal.md`

## Executive Summary

The artifact store in the bioimage-mcp system currently grows unbounded because artifacts are persisted after each workflow run with no automatic cleanup mechanism. This leads to disk space exhaustion on developer machines and within CI/CD environments, eventually causing system failures when write operations cannot be completed.

This specification introduces a comprehensive management system to address these issues:
- **Session-Level Retention**: A policy-driven approach where all artifacts are managed at the session granularity with configurable Time-To-Live (TTL).
  - Session retention: 7 days default
  - Storage quota: 50GB default (configurable, can be unlimited)
  - Warning threshold: 80%
  - Critical threshold: 95%
- **Storage Quotas**: Configurable limits on total storage usage with threshold-based warnings and execution blocks.
- **CLI Management**: A set of administrative commands to audit usage, pin important sessions, and prune expired data.
- **Orphan Detection**: A safety mechanism to identify and remove files on disk that are no longer tracked by the system index.

## User Scenarios & Testing

### User Story 1: Developer Reclaims Disk Space (Priority: P1)
**Why this priority**: Unbounded growth is the primary pain point for users. Reclaiming space is the core value proposition of this feature.

**Description**:  
A developer has been using bioimage-mcp for several weeks and notices their disk is getting full. They need to understand what is using space and safely remove old data.

**Independent Test**:
1. Run a storage status command to see a breakdown of usage by session age and state.
2. Execute a "dry-run" prune to verify which sessions and orphaned files would be deleted.
3. Perform the actual prune operation and verify that disk space is successfully reclaimed while active and pinned sessions remain intact.

### User Story 2: CI Environment Protection (Priority: P1)
**Why this priority**: Prevents intermittent CI failures caused by storage exhaustion on shared runners.

**Description**:  
A CI pipeline runs bioimage-mcp integration tests frequently. To prevent the runner from running out of disk space, the system should enforce quotas and allow for easy cleanup of test artifacts.

**Independent Test**:
1. Configure a strict storage quota and verify that a new run is blocked with a clear error message when the quota is exceeded.
2. Set a short retention period (e.g., 1 day) and verify that a cleanup command removes the artifacts from the previous day's runs.

### User Story 3: Protecting Important Results (Priority: P2)
**Why this priority**: Prevents accidental data loss of valuable research results during automated or manual cleanup.

**Description**:  
A user has completed a session with validated results that they need to keep indefinitely for a publication. They need a way to exempt this specific session from any automatic or bulk pruning operations.

**Independent Test**:
1. Mark a specific session as "pinned."
2. Wait for the session's age to exceed the default retention period.
3. Run the prune command and verify that the pinned session and its associated artifacts are preserved while other expired sessions are deleted.

### User Story 4: Understanding Storage Usage (Priority: P2)
**Why this priority**: Provides transparency and allows users to make informed decisions about storage management.

**Description**:  
A user wants to see a detailed inventory of their artifact storage to identify which workflows are consuming the most space.

**Independent Test**:
1. List all sessions and verify that the output correctly displays status (active, retained, expired, pinned), age, and the total size of artifacts for each session.

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Prune during active session | System must never delete sessions that are currently in progress. |
| File already deleted | Cleanup operations must be idempotent; if a file is already missing, the system logs the event and continues without error. |
| Directory-based artifacts | System must correctly handle and recursively remove directory-structured artifacts (e.g., OME-Zarr). |
| Missing file with index entry | If the database tracks a file that is missing from disk, the system must clean up the stale index entry. |
| Concurrent management | The system must prevent race conditions if multiple cleanup commands are issued simultaneously. |
| Interrupted cleanup | If a cleanup operation is interrupted (e.g., process crash), the next run must be able to resume or identify remaining "orphaned" files. |
| Quota check on empty store | System must correctly report zero usage and allow runs to proceed. |

General invariant: Cleanup operations must be idempotent across process restarts; rerunning prune converges on the same final state.

## Requirements

### Constitution Constraints

#### 1. Stable MCP Surface (Anti-Context-Bloat)
Management operations (prune, pin, status) are restricted to the CLI and core server logic. No new tools are added to the MCP discovery surface, ensuring it remains focused on bioimage analysis tasks.

#### 2. Isolated Tool Execution
Storage quota enforcement occurs within the core server before dispatching tasks to tool environments. This maintains the existing isolation model where tools are consumers, not managers, of the artifact store.

#### 3. Artifact References Only
This feature manages the physical lifecycle and metadata of artifacts but does not change the underlying reference-based I/O model used by the tools.

#### 4. Reproducibility & Provenance
Retention policies respect "pinned" sessions to ensure important reproducible workflows remain available. While pruning old sessions limits replayability of those specific runs, it is a necessary trade-off for system stability.

#### 5. Safety & Observability
All destructive operations require user confirmation or explicit override flags. The system provides "dry-run" capabilities to preview changes and detailed logging for all deletion events.

#### 6. Test-Driven Development
Logic for session expiration, quota calculation, and cleanup must be verified with tests before implementation is considered complete.

### Functional Requirements

- **FR-001**: System must record the completion timestamp when a workflow session ends.
- **FR-002**: System must be able to compute accurate per-session storage usage by associating artifacts to their owning session and summing `size_bytes` (either computed on demand or maintained incrementally).
- **FR-003**: System must support a "pinned" state for sessions to exempt them from any automated or age-based cleanup.
- **FR-004**: Cleanup operations must remove all disk files and database records for sessions that have exceeded the retention period and are not pinned.
- **FR-005**: Cleanup operations must support a "preview" mode showing what would be deleted without performing the actual deletion.
- **FR-006**: Bulk deletion must support a "force" flag to bypass user confirmation prompts.
- **FR-007**: System must provide a status report showing storage usage broken down by session state (active, retained, expired, pinned).
- **FR-008**: System must be able to list all sessions with their associated storage footprint and age.
- **FR-009**: Users must be able to toggle the "pinned" status of any existing session.
- **FR-010**: The system must perform a storage quota check before starting any new workflow run.
- **FR-011**: New runs must be blocked if storage usage exceeds a "critical" threshold (default: 95%).
- **FR-012**: When storage usage exceeds the warning threshold, the system must emit a warning via structured logs (including current usage and threshold); runs proceed normally.
- **FR-013**: Session deletion must use a cascading approach, ensuring all associated files are removed from disk.
- **FR-014**: Cleanup operations must optionally detect and clean up orphaned files on disk that have no corresponding entry in the artifact index when invoked with an explicit flag (e.g., `--include-orphans`).

### Non-Functional Requirements

- **NFR-001**: Documentation must include storage management CLI usage in `AGENTS.md` and the project README, and the examples in `specs/019-artifact-management/quickstart.md` must be verified to work end-to-end.

### Key Entities

- **Session**: Represents a discrete workflow execution. It has a lifecycle that moves from "active" to "completed." Once completed, it is subject to a retention period unless it is "pinned" by the user.
- **Artifact**: A file-backed data object generated during a session. Its lifecycle is tied strictly to its parent session; it cannot exist independently.
- **Storage Quota**: A set of configurable limits defining the maximum allowed size of the artifact store, including warning and critical thresholds.

### Session Lifecycle & State Model

For storage management, session state is derived from `sessions` table fields:

- **active**: `completed_at` is NULL (session still in progress)
- **retained**: `completed_at` is set and the session is within the retention TTL
- **expired**: `completed_at` is set and `completed_at + retention_ttl < now`
- **pinned**: `is_pinned = true` (never pruned regardless of age)

`completed_at` is stamped once when a session first transitions from active to completed (idempotent), typically when it has been inactive longer than a configured idle timeout.

### Assumptions

- Database migrations to support new tracking fields will be backward-compatible with existing artifact stores.
- Retention period countdown begins when a session completes, not when it was created.
- Configuration can be overridden via environment variables for CI/CD use cases (e.g., shorter retention period, smaller quota).

## Success Criteria

- **Measurable Outcome 1**: The storage status command responds with accurate usage data in under 1 second.
- **Measurable Outcome 2**: Quota checks add ≤ 50ms (p95) overhead per `run_workflow` call on a typical local store (document fixture characteristics).
- **Measurable Outcome 3**: A cleanup operation involving 100 typical sessions completes in under 30 seconds.
- **Measurable Outcome 4**: Pinned sessions remain accessible and fully intact after multiple cleanup cycles that remove other sessions of the same age.
- **Measurable Outcome 5**: After prune, `bytes_reclaimed` reported by the command equals the delta in total tracked `size_bytes` shown by `storage status` (within filesystem rounding tolerance).
- **Measurable Outcome 6**: Active sessions (those currently running) are never identified as candidates for pruning, regardless of the retention policy.
- **Measurable Outcome 7**: The dry-run preview mode accurately identifies all expired sessions and orphaned files that would be deleted.
- **Measurable Outcome 8**: When storage exceeds the critical threshold, new runs are blocked with a clear, actionable error message directing users to run cleanup.
- **Measurable Outcome 9**: When storage exceeds the warning threshold, a warning is logged but runs proceed normally.
- **Measurable Outcome 10**: Orphaned files (those not tracked in the index) are identified and removed during cleanup operations.
- **Measurable Outcome 11**: All cleanup and status operations are idempotent — running them multiple times produces the same result without errors.
