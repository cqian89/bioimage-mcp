# Project Roadmap

**Project:** Bioimage-MCP
**Mission:** Enable AI agents to safely and reproducibly execute bioimage analysis tools.
**Status:** Active
**Current Phase:** Phase 2 (Tool Management)

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
**Status:** Complete (~95%)
**Goal:** System enables zero-copy data passing and artifact management.
**Focus:** File paths, `mem://` protocol, `bioio` integration.

| Requirement | Description | Status |
|-------------|-------------|--------|
| **DATA-01** | Tools accept/return file paths as artifacts | ✅ |
| **DATA-02** | System supports `mem://` references | ✅ |

**Notes:**
- DATA-02: Currently in file-simulated phase, ready for zero-copy upgrade.

### Phase 4: Reproducibility
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
| **2 - Tool Management** | Install/List Tools | **Complete** |
| **3 - Data & Artifacts** | Zero-copy I/O | **Complete** |
| **4 - Reproducibility** | Record/Export | **Mostly Complete** |
