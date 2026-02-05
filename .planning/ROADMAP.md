# Roadmap: Bioimage-MCP

## Milestones

- ✅ **v0.3.0 Scipy Integration** — Phases 5.1–10 (shipped 2026-01-27). Archive: `.planning/milestones/v0.3.0-ROADMAP.md`
- ✅ **v0.4.0 Unified Introspection Engine** — Phases 11–20 (shipped 2026-02-04). Archive: `.planning/milestones/v0.4.0-ROADMAP.md`
- 🚧 **v0.5.0 Interactive Annotation** — Phases 21–24 (In Progress)
...
### Phase 21: µSAM Tool Pack Foundation
Establish the isolated environment and prerequisite models for µSAM.

- **Goal:** The µSAM tool pack is installed and ready for local inference.
- **Dependencies:** None
- **Requirements:** USAM-01, USAM-05, USAM-06, INFRA-05
- **Success Criteria:**
  1. `bioimage-mcp install microsam --profile gpu` completes successfully on Linux/macOS.
  2. Specialist SAM models (LM, EM, Generalist) are present in local cache after installation.
  3. Tool execution automatically selects the fastest available device (CUDA > MPS > CPU).
- **Plans:** 5 plans
  - [x] 21-01-PLAN.md — Microsam tool pack scaffold (manifest + entrypoint + model bootstrap script)
  - [x] 21-02-PLAN.md — Microsam conda environment + lockfile
  - [x] 21-03-PLAN.md — Microsam install integration (CLI wiring + GPU profiles + model bootstrap)
  - [x] 21-04-PLAN.md — Microsam doctor verification (validation of env + models)
  - [x] 21-05-PLAN.md — Microsam device selection wiring (CUDA > MPS > CPU)

| Phase | Description | Status | Progress |
|-------|-------------|--------|----------|
| 21 | µSAM Tool Pack Foundation | ✓ Complete | 100% |

| 22 | Headless Tools | Pending | 0% |
| 23 | Interactive Bridge | Pending | 0% |
| 24 | Session Management | Pending | 0% |

---

*Roadmap updated: 2026-02-05*
