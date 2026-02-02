# Phase 18: Implement artifact store retention and quota management - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

## Phase Boundary

Add retention policies and storage limits for artifacts to prevent unbounded growth and manage storage costs. This phase covers:
- Time-based artifact retention with configurable periods
- Global storage quotas with soft enforcement
- Automatic background cleanup when limits are exceeded
- CLI visibility into storage status and cleanup events

Out of scope: User-level quotas, per-tool retention policies, backup/archive functionality.

## Implementation Decisions

### Retention Policies
- **Time-based deletion** drives cleanup (artifact age, not session lifecycle)
- **Default retention period: 14 days** (configurable via CLI/config file)
- **Global policy** applies to all artifacts uniformly (not per-session or per-tool)
- **Orphaned artifacts** (no session) get same 14-day retention
- **Pin/preserve override**: Users can mark artifacts to exempt from cleanup
- Pinned artifact handling: Claude's discretion (filter during cleanup or separate preservation pass)
- Backend coverage: Claude's discretion (may vary by storage backend capabilities)

### Quota Enforcement Strategy
- **Soft limits with aggressive cleanup** (not hard rejection)
- **Global total scope**: 100 GB limit across all sessions
- **Total storage only** (no time-based rate limits)
- No per-session or per-user quotas in this phase
- Configurable quota limit via CLI/config (default 100 GB)

### Cleanup Behavior
- **Oldest first (FIFO)** deletion priority
- **Skip in-use artifacts** (those with active references)
- **Keep the most recent session** protected from deletion
- **Asynchronous background cleanup** (non-blocking)
- Trigger at **100%** of quota, clean down to **80%** (aggressive headroom)
- **Global deletion** across all sessions (not session-proportional)
- **Dry-run mode** available for preview (`--dry-run` flag)
- **Rate limit**: Cooldown period between cleanup runs to prevent thrashing

### Timing and Operation
- **Periodic background checks** (not on every artifact creation)
- Cleanup triggers on **quota threshold hit** (100%)
- Where cleanup runs (in-server vs daemon): Claude's discretion

### Monitoring and Visibility
- **Both**: Explicit `bioimage-mcp status` command + storage summary in other CLI commands
- **Status detail level**: Claude's discretion (balanced detail without overwhelm)
- **Time-to-cleanup displayed**: Show hours/days until deletion for each artifact
- **Soft threshold warnings** at 80% of quota
- **Summary-only logging** (artifact counts cleaned, not individual deletions)
- **Post-cleanup summary** in both CLI output and log file
- **Manual cleanup trigger** via CLI (`bioimage-mcp cleanup` command)

### Claude's Discretion
- Pinned artifact check implementation (filter vs separate pass)
- Storage backend coverage details
- Cleanup process location (in-server vs daemon)
- Status command detail level (what specific metrics to show)
- Rate limit duration between cleanup runs

## Specific Ideas

No specific UI references or examples — open to standard CLI patterns and standard logging practices.

## Deferred Ideas

**Future phase candidates:**
- Per-session or per-user quota tiers
- Per-tool retention policies (different rules for bioimages vs tables)
- Archive/cold storage tier for preserved artifacts
- Pre-cleanup warnings with user confirmation
- Email/webhook notifications for quota events
- Retention policy analytics (access patterns, optimal retention periods)

---

*Phase: 18-implement-artifact-store-retention-and-quota-management*
*Context gathered: 2026-02-02*
