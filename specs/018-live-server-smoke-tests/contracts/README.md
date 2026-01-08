# Contracts: Live Server Smoke Tests

**Feature**: 018-live-server-smoke-tests  
**Date**: 2026-01-08

## No New API Contracts

This feature does not introduce any new MCP API contracts. It is purely test infrastructure that exercises the existing MCP API surface:

### Existing MCP Tools Exercised

| Tool | Purpose in Smoke Tests |
|------|------------------------|
| `list` | Verify server returns environment/function catalog |
| `describe` | Fetch full function schemas before execution |
| `search` | Find functions by query (optional in scenarios) |
| `run` | Execute functions with real inputs |
| `status` | Poll async execution status |
| `artifact_info` | Validate artifact metadata |
| `session_export` | Export workflow for reproducibility |
| `session_replay` | Replay exported workflows |

### Validation Approach

Instead of new contracts, smoke tests validate:

1. **Response Structure**: All responses match expected MCP schemas
2. **Artifact References**: Outputs contain valid `ref_id` and `uri` fields
3. **Error Handling**: Error responses include `code`, `message`, `details`
4. **Session Lifecycle**: Session IDs are preserved across calls

### Contract Tests Location

Existing contract tests in `tests/contract/` cover schema validation.
Smoke tests complement these by testing the full protocol path.
