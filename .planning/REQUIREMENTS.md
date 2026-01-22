# Requirements: Bioimage-MCP

**Defined:** 2026-01-22
**Core Value:** Enables AI agents to safely and reproducibly execute bioimage analysis tools without dependency conflicts.

## v1 Requirements

### Core Runtime
- [ ] **CORE-01**: System executes tools in isolated Conda environments (Hub-and-Spoke architecture)
- [ ] **CORE-02**: System automatically passes through local GPU (CUDA/MPS) availability to environments
- [ ] **CORE-03**: Core server communicates with workers via robust NDJSON protocol over stdio
- [ ] **CORE-04**: System handles process lifecycle (start, keep-alive, graceful shutdown) to prevent zombies

### Tool Management
- [ ] **TOOL-01**: User can install tools from manifests via `bioimage-mcp install`
- [ ] **TOOL-02**: User can list installed tools and their status via `bioimage-mcp list`
- [ ] **TOOL-03**: User can remove tools and clean up environments via `bioimage-mcp remove`
- [ ] **TOOL-04**: User can verify environment health via `bioimage-mcp doctor`

### Data & Artifacts
- [ ] **DATA-01**: Tools can accept and return file paths as artifacts (avoiding heavy serialization)
- [ ] **DATA-02**: System supports `mem://` references for zero-copy data passing within the same worker context

### Interaction
- [ ] **INTR-01**: Tools can request user input (text/confirmation) during execution via MCP sampling/prompts
- [ ] **INTR-02**: Tools report execution progress to the MCP client (percentage/status text)

### Reproducibility
- [ ] **REPR-01**: System records all tool inputs, outputs, and versions during a session
- [ ] **REPR-02**: User can export a session to a reproducible workflow file

## v2 Requirements

### Advanced Features
- **FEAT-01**: Hot-reload of plugins without server restart
- **FEAT-02**: "Eject" to standalone script (independent of bioimage-mcp)

### Ecosystem
- **ECO-01**: Centralized online registry for tool discovery
- **ECO-02**: Third-party plugin support (pip installable packs)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user Server | v1 focuses on local single-user experience |
| Web Dashboard | CLI is sufficient and standard for this audience |
| Docker Support | Conda provides sufficient isolation and better native GPU support |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 1 | Pending |
| CORE-03 | Phase 1 | Pending |
| CORE-04 | Phase 1 | Pending |
| TOOL-01 | Phase 2 | Pending |
| TOOL-02 | Phase 2 | Pending |
| TOOL-03 | Phase 2 | Pending |
| TOOL-04 | Phase 2 | Pending |
| DATA-01 | Phase 3 | Pending |
| DATA-02 | Phase 3 | Pending |
| INTR-01 | Phase 4 | Pending |
| INTR-02 | Phase 4 | Pending |
| REPR-01 | Phase 5 | Pending |
| REPR-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-22*
