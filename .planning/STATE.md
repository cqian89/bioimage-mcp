# Project State

**Project:** Bioimage-MCP
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.
**Current Focus:** Planning next milestone

## Current Position

Phase: Planning
Plan: Not started
Status: Ready to plan
Last activity: 2026-01-25 — v0.2.0 milestone complete

Progress: [====================] 100% (v0.2.0)

## Accumulated Context

- **v0.2.0 Shipped (2026-01-25):** Core runtime, CLI, reproducibility, Trackpy integration.
- **Next Steps:** Use `/gsd-new-milestone` to start v0.3.0.

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
- 📋 v0.3.0 Next Milestone (Planning)
