# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** v0.3.0 Scipy Integration

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-01-25 — Milestone v0.3.0 started

Progress: [░░░░░░░░░░░░░░░░░░░░] 0% (v0.3.0)

## Accumulated Context

- **v0.2.0 Shipped (2026-01-25):** Core runtime, CLI, reproducibility, Trackpy integration.
- **Next Steps:** Define requirements for Scipy integration.

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-01-25)

## Accumulated Decisions (v0.2.0 Highlights)

(Full history in `PROJECT.md` and archived milestones)

- **Hub-and-Spoke Architecture**: Persistent workers for performance.
- **Artifact-based I/O**: File/mem paths instead of raw data.
- **Out-of-process Discovery**: Worker entrypoints provide tool metadata.
- **Strict Worker Termination**: Kill on error to prevent state desync.

## Roadmap

- ✅ v0.2.0 Foundation (Shipped)
- 📋 v0.3.0 Scipy Integration (Defining Requirements)
