# Project Roadmap

**Project:** Bioimage-MCP
**Mission:** Enable AI agents to safely and reproducibly execute bioimage analysis tools.
**Status:** Active
**Current Phase:** Phase 5

## Overview

This roadmap structures the development of `bioimage-mcp` into 4 coherent phases. Each phase delivers a standalone verifiable capability, moving from core infrastructure to advanced interaction and reproducibility. The strategy prioritizes the "Hub-and-Spoke" architecture immediately to resolve the primary technical risk (dependency isolation).

## Phase Structure

### Phase 1: Core Runtime
**Status:** Complete (100%)
**Goal:** System can reliably spawn and manage persistent worker processes in isolated environments.
**Focus:** Process lifecycle, IPC, GPU detection.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **CORE-01** | System executes tools in isolated Conda environments | ✅ |
| **CORE-02** | System passes through local GPU (CUDA/MPS) availability | ✅ |
| **CORE-03** | Core server communicates via NDJSON over stdio | ✅ |
| **CORE-04** | System handles process lifecycle (no zombies) | ✅ |

**Notes:**
- CORE-02: Unified GPU detection for NVIDIA (CUDA) and Apple Silicon (MPS) implemented.

**Plans:** 1 plan (Wave 1)
- [x] 01-01-PLAN.md — Add MPS (Apple Silicon) GPU detection to complete CORE-02

### Phase 2: Tool Management
**Status:** Complete (100%)
**Goal:** User can manage the lifecycle of tool environments via CLI.
**Focus:** Installation, verification, removal.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **TOOL-01** | User can install tools via `bioimage-mcp install` | ✅ |
| **TOOL-02** | User can list installed tools and status | ✅ |
| **TOOL-03** | User can remove tools via `bioimage-mcp remove` | ✅ |
| **TOOL-04** | User can verify environment health via `doctor` | ✅ |

**Notes:**
- TOOL-01: `install` refactored for dynamic tool discovery.
- TOOL-02: `list` command implemented with table and JSON output.
- TOOL-03: `remove` command implemented with safety checks.

**Plans:** 4 plans (Wave 1 - all parallel)
- [x] 02-01-PLAN.md — Implement `list` CLI command
- [x] 02-02-PLAN.md — Refactor `install` CLI command
- [x] 02-03-PLAN.md — Implement `remove` CLI command
- [x] 02-04-PLAN.md — Refactor `list` for filesystem discovery

### Phase 3: Data & Artifacts
**Status:** Complete (100%)
**Goal:** System enables zero-copy data passing and artifact management.
**Focus:** File paths, `mem://` protocol, `bioio` integration.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **DATA-01** | Tools accept/return file paths as artifacts | ✅ |
| **DATA-02** | System supports `mem://` references | ✅ |

**Notes:**
- DATA-02: Currently in file-simulated phase, ready for zero-copy upgrade.

### Phase 4: Reproducibility
**Status:** Complete (100%)
**Goal:** Users can record and reproduce analysis sessions with validation, error handling, and resume capability.
**Focus:** Session recording, workflow export, production-ready replay.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **REPR-01** | System records all tool inputs/outputs/versions | ✅ |
| **REPR-02** | User can export session to reproducible workflow | ✅ |

**Notes:**
- REPR-01: Implemented using `SessionStep` and provenance tracking with `lock_hash`.
- REPR-02: Export and replay complete with validation, error handling, progress, and resume.

**Plans:** 4 plans (Waves 1-4 sequential)
- [x] 04-01-PLAN.md — Add override validation using jsonschema
- [x] 04-02-PLAN.md — Add version mismatch warnings and environment checks
- [x] 04-03-PLAN.md — Add step progress reporting and tool message surfacing
- [x] 04-04-PLAN.md — Add missing input handling, resume capability, and error summaries

### Phase 5: Trackpy Integration
**Status:** Complete (100%)
**Goal:** Integrate trackpy particle tracking library as a tool pack with full API coverage and live smoke tests.
**Depends on:** Phase 4
**Focus:** Dynamic introspection, API coverage, test data, smoke testing.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **TRACK-01** | Trackpy functions discoverable via dynamic introspection | ✅ |
| **TRACK-02** | Determine correct environment (base vs. separate) | ✅ |
| **TRACK-03** | Full API coverage from trackpy v0.7 | ✅ |
| **TRACK-04** | Test data sourced from trackpy repo/docs | ✅ |
| **TRACK-05** | Live smoke test matching reference script output | ✅ |

**Notes:**
- Integration approach similar to skimage, xarray packages
- API reference: https://soft-matter.github.io/trackpy/v0.7/api.html
- Function signatures via dynamic introspection (not manual definitions)
- Exclusions from API should have documented justification
- TRACK-01 & TRACK-03: Implemented via out-of-process discovery (meta.list/meta.describe)
- TRACK-04: Vendored frame 0 from soft-matter/trackpy-examples.
- TRACK-05: Implemented numerical equivalence smoke tests using live_server fixture.

**Plans:** 8 plans (Waves 1-4 sequential, Wave 1 parallel gap closure)
- [x] 05-01-PLAN.md — Create trackpy tool pack skeleton (env, manifest, entrypoint)
- [x] 05-02-PLAN.md — Implement TrackpyAdapter for dynamic introspection
- [x] 05-03-PLAN.md — Add smoke tests with synthetic data fixtures
- [x] 05-04-PLAN.md — Fix core stability issues (install, worker runtime) (Gap Closure)
- [x] 05-05-PLAN.md — Fix tool entrypoints (Cellpose meta.list, Trackpy stdout) (Gap Closure)
- [x] 05-06-PLAN.md — End-to-end verification via smoke tests
- [x] 05-07-PLAN.md — Doctor: treat missing conda-lock as warning (Gap Closure)
- [x] 05-08-PLAN.md — Describe: fix Trackpy meta.describe schema enrichment (Gap Closure)

## Progress

| Phase | Goal | Status |
|-------|------|--------|
| **1 - Core Runtime** | Spawn/Manage Workers | **Complete** ✓ |
| **2 - Tool Management** | Install/List Tools | **Complete** ✓ |
| **3 - Data & Artifacts** | Zero-copy I/O | **Complete** ✓ |
| **4 - Reproducibility** | Record/Export | **Complete** ✓ |
| **5 - Trackpy Integration** | Particle Tracking | **Complete** ✓ |
