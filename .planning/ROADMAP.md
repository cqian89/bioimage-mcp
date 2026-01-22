# Project Roadmap

**Project:** Bioimage-MCP
**Mission:** Enable AI agents to safely and reproducibly execute bioimage analysis tools.
**Status:** Active
**Current Phase:** Phase 2 (Tool Management)

## Overview

This roadmap structures the development of `bioimage-mcp` into 5 coherent phases. Each phase delivers a standalone verifiable capability, moving from core infrastructure to advanced interaction and reproducibility. The strategy prioritizes the "Hub-and-Spoke" architecture immediately to resolve the primary technical risk (dependency isolation).

## Phase Structure

### Phase 1: Core Runtime
**Status:** Complete (with minor gaps) (~90%)
**Goal:** System can reliably spawn and manage persistent worker processes in isolated environments.
**Focus:** Process lifecycle, IPC, GPU detection.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **CORE-01** | System executes tools in isolated Conda environments | ✅ |
| **CORE-02** | System passes through local GPU (CUDA/MPS) availability | ⚠️ |
| **CORE-03** | Core server communicates via NDJSON over stdio | ✅ |
| **CORE-04** | System handles process lifecycle (no zombies) | ✅ |

**Notes:**
- CORE-02: NVIDIA GPU detection implemented; MPS (Apple Silicon) detection is a known gap.

### Phase 2: Tool Management
**Status:** In Progress (~60%)
**Goal:** User can manage the lifecycle of tool environments via CLI.
**Focus:** Installation, verification, removal.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **TOOL-01** | User can install tools via `bioimage-mcp install` | ⚠️ |
| **TOOL-02** | User can list installed tools and status | ❌ |
| **TOOL-03** | User can remove tools via `bioimage-mcp remove` | ❌ |
| **TOOL-04** | User can verify environment health via `doctor` | ✅ |

**Notes:**
- TOOL-01: `install` exists but is currently hardcoded to base/cellpose envs.
- TOOL-02: CLI not exposed; logic exists in `DiscoveryService`.
- TOOL-03: Not implemented.

**Plans:** 3 plans (Wave 1 - all parallel)
- [ ] 02-01-PLAN.md — Implement `list` CLI command
- [ ] 02-02-PLAN.md — Refactor `install` CLI command
- [ ] 02-03-PLAN.md — Implement `remove` CLI command

### Phase 3: Data & Artifacts
**Status:** Complete (~95%)
**Goal:** System enables zero-copy data passing and artifact management.
**Focus:** File paths, `mem://` protocol, `bioio` integration.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **DATA-01** | Tools accept/return file paths as artifacts | ✅ |
| **DATA-02** | System supports `mem://` references | ✅ |

**Notes:**
- DATA-02: Currently in file-simulated phase, ready for zero-copy upgrade.

### Phase 4: Interactive Execution
**Status:** Pending (partial foundation) (~40%)
**Goal:** Tools can execute interactively and report real-time status.
**Focus:** User input, progress bars, sampling.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **INTR-01** | Tools can request user input during execution | ❌ |
| **INTR-02** | Tools report execution progress to MCP client | ⚠️ |

**Notes:**
- INTR-02: Status polling exists, but real-time streaming is not implemented.

### Phase 5: Reproducibility
**Status:** Mostly Complete (~80%)
**Goal:** Users can record and reproduce analysis sessions.
**Focus:** Session recording, workflow export.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **REPR-01** | System records all tool inputs/outputs/versions | ✅ |
| **REPR-02** | User can export session to reproducible workflow | ⚠️ |

**Notes:**
- REPR-01: Implemented using `SessionStep` and provenance tracking with `lock_hash`.
- REPR-02: Export works; replay is implemented but lacks validation and is not yet production-ready.

## Progress

| Phase | Goal | Status |
|-------|------|--------|
| **1 - Core Runtime** | Spawn/Manage Workers | **Complete** |
| **2 - Tool Management** | Install/List Tools | **In Progress** |
| **3 - Data & Artifacts** | Zero-copy I/O | **Complete** |
| **4 - Interactive Execution** | Input/Progress | Pending |
| **5 - Reproducibility** | Record/Export | **Mostly Complete** |
