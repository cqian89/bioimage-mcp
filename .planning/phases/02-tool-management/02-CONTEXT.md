# Phase 2: Tool Management - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

CLI commands for managing tool environment lifecycle. Users can install, list, remove, and verify health of tool packs. This phase completes the tool management CLI — `install` needs refactoring (currently hardcoded), `list` needs CLI exposure, `remove` needs implementation, and `doctor` is already complete.

</domain>

<decisions>
## Implementation Decisions

### Output format & verbosity
- Default to human-friendly tables for all commands
- `--json` flag for machine-readable output (scripts, CI)
- Quiet by default: success shows one-liner, failure shows full details
- `-v` flag for verbose output when needed
- Long operations (install) show spinner with current stage (e.g., "Installing cellpose...")
- Colors enabled with auto-detection (disable in pipes/non-TTY)
- Green for success, red for errors

### Install command design
- Support both profile-based (`--profile cpu`) AND individual tool selection (`install cellpose tttrlib`)
- Base environment should always be installed — it's a foundational requirement
- On partial failure (multiple tools): continue installing all, summarize successes and failures at end
- If tool already installed: warn and skip, require `--force` to reinstall

### Remove command behavior
- Always prompt for confirmation: "Remove cellpose? (y/N)"
- Block removal if tool has an active worker — refuse with "tool is currently running"
- During confirmation prompt, ask whether to also remove config/manifest
- Stay silent on orphaned dependencies — user can run `doctor` to see unused envs

### Error messaging patterns
- Smart detail level: brief messages for known issues, full context for unexpected errors
- Include suggested fix commands, e.g., "Run: bioimage-mcp install base"
- Exit codes: 0 (success), 1 (general error), 2 (usage error)
- With `--json` flag, errors return JSON with error code and message

### OpenCode's Discretion
- Spinner implementation details
- Exact table formatting/column widths
- Color palette choices beyond red/green
- Specific error code values for JSON errors

</decisions>

<specifics>
## Specific Ideas

- CLI should feel consistent with existing `doctor` command behavior
- Profile system should be extensible (not hardcoded to cpu/gpu)
- Error suggestions should be copy-pasteable commands

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-tool-management*
*Context gathered: 2026-01-22*
