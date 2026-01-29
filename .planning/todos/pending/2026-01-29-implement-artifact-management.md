---
created: 2026-01-29T17:48
title: Implement artifact store retention and quota management
area: general
files:
  - specs/019-artifact-management/proposal.md
  - src/bioimage_mcp/artifacts/store.py
  - src/bioimage_mcp/config/schema.py
  - src/bioimage_mcp/storage/sqlite.py
---

## Problem

The artifact store in `~/.bioimage-mcp/artifacts` grows unbounded because artifacts are persisted after each run with no automatic cleanup. This causes disk space exhaustion on developer machines and in CI environments. A proposal was drafted but remains unimplemented.

## Solution

Implement the 4-phase plan detailed in `specs/019-artifact-management/proposal.md`:
1. Schema & Tracking: Add `completed_at`, `total_size_bytes` to sessions; add configuration for retention/quotas.
2. Prune Logic: Implement session-level TTL cleanup and orphan detection.
3. CLI Commands: Add `bioimage-mcp prune`, `storage status`, and session pin/unpin commands.
4. Testing: Verify with integration tests and update documentation.
